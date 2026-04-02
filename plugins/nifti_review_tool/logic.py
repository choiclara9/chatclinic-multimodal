from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
from PIL import Image

from app.models import NiftiSourceResponse
from app.services.tool_runner import discover_tools


THUMBNAIL_MAX_PX = 512


def _normalize_slice(arr: np.ndarray) -> np.ndarray:
    """Normalize a 2D array to 0-255 uint8."""
    arr = arr.astype(np.float64)
    lo, hi = np.nanmin(arr), np.nanmax(arr)
    if hi - lo > 0:
        arr = (arr - lo) / (hi - lo) * 255.0
    else:
        arr = np.zeros_like(arr)
    return np.nan_to_num(arr, nan=0).astype(np.uint8)


def _slice_to_data_url(arr: np.ndarray) -> str | None:
    """Convert a 2D numpy array into a base64 PNG data URL."""
    try:
        normed = _normalize_slice(arr)
        img = Image.fromarray(normed, mode="L")
        img.thumbnail((THUMBNAIL_MAX_PX, THUMBNAIL_MAX_PX), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return None


def _build_montage(data: np.ndarray) -> str | None:
    """Build a 3-panel montage (axial, coronal, sagittal) as a data URL."""
    try:
        if data.ndim < 3:
            return None
        # Take center slices along each axis
        ax_slice = _normalize_slice(np.rot90(data[:, :, data.shape[2] // 2]))
        cor_slice = _normalize_slice(np.rot90(data[:, data.shape[1] // 2, :]))
        sag_slice = _normalize_slice(np.rot90(data[data.shape[0] // 2, :, :]))

        # Make all same height by padding
        max_h = max(ax_slice.shape[0], cor_slice.shape[0], sag_slice.shape[0])
        panels = []
        for sl in [ax_slice, cor_slice, sag_slice]:
            if sl.shape[0] < max_h:
                pad = np.zeros((max_h - sl.shape[0], sl.shape[1]), dtype=np.uint8)
                sl = np.vstack([sl, pad])
            panels.append(sl)

        # Add 4px black separator
        sep = np.zeros((max_h, 4), dtype=np.uint8)
        montage = np.hstack([panels[0], sep, panels[1], sep, panels[2]])

        img = Image.fromarray(montage, mode="L")
        img.thumbnail((THUMBNAIL_MAX_PX * 3, THUMBNAIL_MAX_PX), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return None


def _orientation_string(img: nib.Nifti1Image) -> str:
    """Return orientation codes like 'RAS' or 'LPI'."""
    try:
        codes = nib.aff2axcodes(img.affine)
        return "".join(codes)
    except Exception:
        return "unknown"


def analyze_nifti_source(nifti_path: str, file_name: str | None = None) -> NiftiSourceResponse:
    path = Path(nifti_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"NIfTI source not found: {path}")

    warnings: list[str] = []
    name = file_name or path.name

    img = nib.load(str(path))
    header = img.header
    shape = list(int(d) for d in img.shape)
    voxel_dims = [round(float(v), 4) for v in header.get_zooms()]
    affine = [[round(float(v), 6) for v in row] for row in img.affine.tolist()]
    datatype = str(header.get_data_dtype())
    orientation = _orientation_string(img)

    # Spatial dimensions
    ndim = len(shape)
    is_4d = ndim >= 4
    spatial_shape = shape[:3] if ndim >= 3 else shape

    # Generate montage preview from 3D data
    preview_data_url: str | None = None
    try:
        data = np.asanyarray(img.dataobj)
        if data.ndim >= 4:
            data = data[..., 0]  # first volume
        if data.ndim >= 3:
            preview_data_url = _build_montage(data)
    except Exception:
        warnings.append("Slice preview generation failed.")

    if not preview_data_url:
        warnings.append("Could not generate slice montage.")

    metadata_item: dict[str, Any] = {
        "file_name": name,
        "shape": shape,
        "voxel_dims": voxel_dims,
        "datatype": datatype,
        "orientation": orientation,
        "is_4d": is_4d,
        "file_size_bytes": path.stat().st_size,
    }

    # Compute volume dimensions in mm
    spatial_mm = [
        round(spatial_shape[i] * voxel_dims[i], 2) if i < len(voxel_dims) else 0
        for i in range(min(3, len(spatial_shape)))
    ]
    metadata_item["fov_mm"] = spatial_mm

    artifacts = {
        "metadata": metadata_item,
        "nifti_review": {
            "metadata": metadata_item,
            "preview_data_url": preview_data_url,
            "affine": affine,
        },
    }

    shape_str = " × ".join(str(d) for d in shape)
    voxel_str = " × ".join(str(v) for v in voxel_dims[:3])
    fov_str = " × ".join(f"{v:.1f}" for v in spatial_mm)

    draft_answer = (
        f"NIfTI review is ready for `{name}`.\n\n"
        f"- Shape: {shape_str}\n"
        f"- Voxel size: {voxel_str} mm\n"
        f"- FOV: {fov_str} mm\n"
        f"- Orientation: {orientation}\n"
        f"- Data type: {datatype}\n"
        f"{'- 4D volume (e.g. fMRI time series)' if is_4d else '- 3D volume'}\n\n"
        "The Studio card shows volume metadata and a 3-plane slice preview (axial / coronal / sagittal). "
        "Use `$studio ...` for grounded follow-up questions."
    )

    return NiftiSourceResponse(
        analysis_id="",
        source_nifti_path=str(path),
        file_name=name,
        file_kind="NIFTI",
        shape=shape,
        voxel_dims=voxel_dims,
        affine_matrix=affine,
        datatype=datatype,
        orientation=orientation,
        is_4d=is_4d,
        fov_mm=spatial_mm,
        metadata_items=[metadata_item],
        studio_cards=[{"id": "nifti_review", "title": "NIfTI Review", "subtitle": "Volume metadata, orientation, and slice preview"}],
        artifacts=artifacts,
        warnings=warnings,
        preview_data_url=preview_data_url,
        draft_answer=draft_answer,
        used_tools=["nifti_review_tool"],
        tool_registry=discover_tools(),
    )


def execute(payload: dict[str, object]) -> dict[str, object]:
    nifti_path = str(payload.get("nifti_path") or "").strip()
    if not nifti_path:
        raise ValueError("`nifti_path` is required.")
    file_name = str(payload.get("file_name") or Path(nifti_path).name).strip()
    analysis = analyze_nifti_source(nifti_path, file_name=file_name)
    return {"analysis": analysis.model_dump()}
