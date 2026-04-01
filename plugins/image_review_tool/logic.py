from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from app.models import ImageSourceResponse
from app.services.tool_runner import discover_tools


_MODE_BIT_DEPTH: dict[str, int] = {
    "1": 1, "L": 8, "P": 8, "RGB": 24, "RGBA": 32,
    "CMYK": 32, "YCbCr": 24, "LAB": 24, "HSV": 24,
    "I": 32, "F": 32, "I;16": 16, "I;16L": 16, "I;16B": 16,
    "LA": 16, "PA": 16, "RGBa": 32,
}

THUMBNAIL_MAX_PX = 512


def _gps_to_decimal(gps_info: dict) -> dict[str, float | str | None]:
    """Convert EXIF GPS IFDRational tuples to decimal degrees."""
    result: dict[str, float | str | None] = {}
    try:
        lat = gps_info.get(2)
        lat_ref = gps_info.get(1, "N")
        lon = gps_info.get(4)
        lon_ref = gps_info.get(3, "E")
        if lat and lon:
            lat_dec = float(lat[0]) + float(lat[1]) / 60 + float(lat[2]) / 3600
            lon_dec = float(lon[0]) + float(lon[1]) / 60 + float(lon[2]) / 3600
            if lat_ref == "S":
                lat_dec = -lat_dec
            if lon_ref == "W":
                lon_dec = -lon_dec
            result["latitude"] = round(lat_dec, 6)
            result["longitude"] = round(lon_dec, 6)
    except Exception:
        pass
    return result


def _extract_exif(img: Image.Image) -> dict[str, Any]:
    """Extract human-readable EXIF data from a PIL Image."""
    exif_data: dict[str, Any] = {}
    try:
        raw_exif = img.getexif()
        if not raw_exif:
            return exif_data
        for tag_id, value in raw_exif.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            if tag_name == "GPSInfo":
                gps_ifd = raw_exif.get_ifd(0x8825)
                gps_parsed: dict[str, Any] = {}
                for gps_tag_id, gps_val in gps_ifd.items():
                    gps_tag_name = GPSTAGS.get(gps_tag_id, str(gps_tag_id))
                    gps_parsed[gps_tag_name] = str(gps_val)
                decimal = _gps_to_decimal(gps_ifd)
                if decimal:
                    gps_parsed.update(decimal)
                exif_data["GPS"] = gps_parsed
            elif isinstance(value, bytes):
                exif_data[tag_name] = f"<{len(value)} bytes>"
            else:
                exif_data[tag_name] = str(value)
    except Exception:
        pass
    return exif_data


def _build_thumbnail(img: Image.Image) -> str | None:
    """Generate a base64 PNG data URL thumbnail (max 512px)."""
    try:
        thumb = img.copy()
        thumb.thumbnail((THUMBNAIL_MAX_PX, THUMBNAIL_MAX_PX), Image.LANCZOS)
        if thumb.mode in ("RGBA", "LA", "PA"):
            pass
        elif thumb.mode not in ("RGB", "L"):
            thumb = thumb.convert("RGB")
        buf = io.BytesIO()
        thumb.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return None


def analyze_image_source(image_path: str, file_name: str | None = None) -> ImageSourceResponse:
    path = Path(image_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Image source not found: {path}")

    warnings: list[str] = []
    img = Image.open(path)
    width, height = img.size
    format_name = img.format or path.suffix.lstrip(".").upper()
    color_mode = img.mode
    bit_depth = _MODE_BIT_DEPTH.get(color_mode)
    exif_data = _extract_exif(img)
    preview_data_url = _build_thumbnail(img)
    if not preview_data_url:
        warnings.append("Thumbnail generation failed.")

    name = file_name or path.name
    metadata_item: dict[str, Any] = {
        "file_name": name,
        "width": width,
        "height": height,
        "format": format_name,
        "color_mode": color_mode,
        "bit_depth": bit_depth,
        "file_size_bytes": path.stat().st_size,
    }
    if exif_data:
        metadata_item["exif"] = exif_data

    artifacts = {
        "metadata": metadata_item,
        "image_review": {
            "metadata": metadata_item,
            "preview_data_url": preview_data_url,
            "exif": exif_data,
        },
    }

    exif_summary = ""
    if exif_data.get("Make") or exif_data.get("Model"):
        exif_summary = f"- Camera: {exif_data.get('Make', '')} {exif_data.get('Model', '')}\n"
    if exif_data.get("DateTime"):
        exif_summary += f"- DateTime: {exif_data['DateTime']}\n"
    if exif_data.get("GPS"):
        gps = exif_data["GPS"]
        if "latitude" in gps and "longitude" in gps:
            exif_summary += f"- GPS: {gps['latitude']}, {gps['longitude']}\n"

    draft_answer = (
        f"Image review is ready for `{name}`.\n\n"
        f"- Dimensions: {width} x {height} px\n"
        f"- Format: {format_name}\n"
        f"- Color mode: {color_mode} ({bit_depth or '?'}-bit)\n"
        f"- File size: {path.stat().st_size:,} bytes\n"
        f"{exif_summary}\n"
        "The Studio card shows image metadata and a thumbnail preview. "
        "Use `$studio ...` for grounded follow-up questions."
    )

    return ImageSourceResponse(
        analysis_id="",
        source_image_path=str(path),
        file_name=name,
        file_kind=format_name,
        width=width,
        height=height,
        format_name=format_name,
        color_mode=color_mode,
        bit_depth=bit_depth,
        exif_data=exif_data,
        metadata_items=[metadata_item],
        studio_cards=[{"id": "image_review", "title": "Image Review", "subtitle": "Metadata, EXIF, and image preview"}],
        artifacts=artifacts,
        warnings=warnings,
        preview_data_url=preview_data_url,
        draft_answer=draft_answer,
        used_tools=["image_review_tool"],
        tool_registry=discover_tools(),
    )


def execute(payload: dict[str, object]) -> dict[str, object]:
    image_path = str(payload.get("image_path") or "").strip()
    if not image_path:
        raise ValueError("`image_path` is required.")
    file_name = str(payload.get("file_name") or Path(image_path).name).strip()
    analysis = analyze_image_source(image_path, file_name=file_name)
    return {"analysis": analysis.model_dump()}
