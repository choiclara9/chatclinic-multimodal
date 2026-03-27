from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pysam import bcftools

from app.models import RohSegment


def _parse_roh_regions(text: str) -> list[RohSegment]:
    segments: list[RohSegment] = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) < 8 or fields[0] != "RG":
            continue
        try:
            segments.append(
                RohSegment(
                    sample=fields[1],
                    contig=fields[2],
                    start_1based=int(fields[3]),
                    end_1based=int(fields[4]),
                    length_bp=int(fields[5]),
                    marker_count=int(fields[6]),
                    quality=float(fields[7]),
                )
            )
        except ValueError:
            continue
    return segments


def run_roh_analysis(path: str) -> list[RohSegment]:
    vcf_path = Path(path)
    if not vcf_path.exists():
        raise FileNotFoundError(f"VCF not found: {path}")

    output_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="chatgenome_roh_", suffix=".txt", delete=False) as tmp:
            output_path = tmp.name

        bcftools.roh(
            "-G",
            os.getenv("BCFTOOLS_ROH_GT_PHRED", "30"),
            "--AF-dflt",
            os.getenv("BCFTOOLS_ROH_AF_DEFAULT", "0.4"),
            "-O",
            "r",
            "-o",
            output_path,
            str(vcf_path),
        )
        text = Path(output_path).read_text(encoding="utf-8")
        return _parse_roh_regions(text)
    except Exception:
        return []
    finally:
        if output_path:
            try:
                Path(output_path).unlink(missing_ok=True)
            except OSError:
                pass


def execute(payload: dict[str, object]) -> dict[str, object]:
    vcf_path = str(payload["vcf_path"])
    segments = run_roh_analysis(vcf_path)
    return {
        "tool": "roh_analysis_tool",
        "roh_segments": [segment.model_dump() for segment in segments],
        "summary": f"Detected {len(segments)} ROH segment(s).",
    }
