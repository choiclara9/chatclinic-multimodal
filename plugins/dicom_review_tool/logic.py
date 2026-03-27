from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

from app.models import DicomSourceResponse
from app.services.tool_runner import discover_tools


def _read_dicom_metadata(raw: bytes) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "patient_id": "not available",
        "study_instance_uid": "not available",
        "series_instance_uid": "not available",
        "study_description": "not available",
        "series_description": "not available",
        "modality": "not available",
        "rows": "not available",
        "columns": "not available",
        "instance_number": "not available",
        "preview": {"available": False, "image_data_url": None, "message": "Preview not available"},
    }
    try:
        import pydicom  # type: ignore
    except Exception:
        return meta

    try:
        dataset = pydicom.dcmread(io.BytesIO(raw), stop_before_pixels=True, force=True)
        meta.update(
            {
                "patient_id": str(getattr(dataset, "PatientID", "not available")),
                "study_instance_uid": str(getattr(dataset, "StudyInstanceUID", "not available")),
                "series_instance_uid": str(getattr(dataset, "SeriesInstanceUID", "not available")),
                "study_description": str(getattr(dataset, "StudyDescription", "not available")),
                "series_description": str(getattr(dataset, "SeriesDescription", "not available")),
                "modality": str(getattr(dataset, "Modality", "not available")),
                "rows": str(getattr(dataset, "Rows", "not available")),
                "columns": str(getattr(dataset, "Columns", "not available")),
                "instance_number": str(getattr(dataset, "InstanceNumber", "not available")),
            }
        )
        meta["preview"] = _build_dicom_preview(raw)
    except Exception:
        pass
    return meta


def _build_dicom_preview(raw: bytes) -> dict[str, Any]:
    try:
        import numpy as np  # type: ignore
        import pydicom  # type: ignore
        from PIL import Image  # type: ignore
    except Exception:
        return {"available": False, "image_data_url": None, "message": "Preview dependencies are not installed."}

    try:
        dataset = pydicom.dcmread(io.BytesIO(raw), force=True)
        pixel_array = dataset.pixel_array
        array = np.asarray(pixel_array)
        if array.ndim == 4:
            array = array[0, 0]
        elif array.ndim == 3 and array.shape[-1] not in (3, 4):
            array = array[0]

        if array.ndim == 2:
            array = array.astype(np.float32)
            slope = float(getattr(dataset, "RescaleSlope", 1) or 1)
            intercept = float(getattr(dataset, "RescaleIntercept", 0) or 0)
            array = array * slope + intercept
            min_value = float(array.min())
            max_value = float(array.max())
            if max_value == min_value:
                normalized = np.zeros_like(array, dtype=np.uint8)
            else:
                normalized = ((array - min_value) / (max_value - min_value) * 255.0).clip(0, 255).astype(np.uint8)
            if str(getattr(dataset, "PhotometricInterpretation", "")).upper() == "MONOCHROME1":
                normalized = 255 - normalized
            image = Image.fromarray(normalized, mode="L")
        elif array.ndim == 3 and array.shape[-1] in (3, 4):
            normalized = array.astype(np.float32)
            min_value = float(normalized.min())
            max_value = float(normalized.max())
            if max_value != min_value:
                normalized = ((normalized - min_value) / (max_value - min_value) * 255.0).clip(0, 255)
            image = Image.fromarray(normalized.astype(np.uint8), mode="RGB" if normalized.shape[-1] == 3 else "RGBA")
        else:
            return {"available": False, "image_data_url": None, "message": f"Unsupported DICOM pixel shape: {tuple(array.shape)}"}

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return {"available": True, "image_data_url": f"data:image/png;base64,{encoded}", "message": "Preview generated"}
    except Exception as exc:
        return {"available": False, "image_data_url": None, "message": f"Preview generation failed: {exc}"}


def analyze_dicom_source(dicom_path: str, file_name: str | None = None) -> DicomSourceResponse:
    path = Path(dicom_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"DICOM source not found: {path}")
    raw = path.read_bytes()
    metadata = _read_dicom_metadata(raw)
    metadata["file_name"] = file_name or path.name
    metadata["source_file_path"] = str(path)
    warnings: list[str] = []
    preview = metadata.get("preview") or {}
    if not bool(preview.get("available")):
        warnings.append(str(preview.get("message") or "Preview is not available for this DICOM file."))

    series = [
        {
            "series_instance_uid": metadata.get("series_instance_uid", "not available"),
            "study_instance_uid": metadata.get("study_instance_uid", "not available"),
            "modality": metadata.get("modality", "not available"),
            "study_description": metadata.get("study_description", "not available"),
            "series_description": metadata.get("series_description", "not available"),
            "instance_count": 1,
            "example_files": [file_name or path.name],
            "preview": metadata.get("preview"),
        }
    ]

    artifacts = {
        "metadata": metadata,
        "series": {"series": series},
        "dicom_review": {
            "metadata": metadata,
            "series": series,
            "preview": metadata.get("preview"),
        },
    }
    draft_answer = (
        f"DICOM review is ready for `{file_name or path.name}`.\n\n"
        f"- Modality: {metadata.get('modality', 'not available')}\n"
        f"- Study: {metadata.get('study_description', 'not available')}\n"
        f"- Series: {metadata.get('series_description', 'not available')}\n"
        f"- Matrix: {metadata.get('rows', 'not available')} x {metadata.get('columns', 'not available')}\n\n"
        "The Studio card now shows DICOM metadata, preview state, and series summary. Use `$studio ...` for grounded imaging follow-up."
    )
    return DicomSourceResponse(
        analysis_id="",
        source_dicom_path=str(path),
        file_name=file_name or path.name,
        file_kind="DICOM",
        metadata_items=[metadata],
        series=series,
        studio_cards=[{"id": "dicom_review", "title": "DICOM Review", "subtitle": "Metadata, preview, and series summary"}],
        artifacts=artifacts,
        warnings=warnings,
        draft_answer=draft_answer,
        used_tools=["dicom_review_tool"],
        tool_registry=discover_tools(),
    )


def execute(payload: dict[str, object]) -> dict[str, object]:
    dicom_path = str(payload.get("dicom_path") or "").strip()
    if not dicom_path:
        raise ValueError("`dicom_path` is required.")
    file_name = str(payload.get("file_name") or Path(dicom_path).name).strip()
    analysis = analyze_dicom_source(dicom_path, file_name=file_name)
    return {"analysis": analysis.model_dump()}
