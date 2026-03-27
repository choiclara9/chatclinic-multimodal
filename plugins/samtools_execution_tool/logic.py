from __future__ import annotations

import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from app.models import SamtoolsIdxstatsRow, SamtoolsRequest, SamtoolsResponse, SamtoolsStatsItem


ROOT_DIR = Path(__file__).resolve().parents[2]
SAMTOOLS_BUNDLE_DIR = ROOT_DIR / "third_party" / "samtools"
SAMTOOLS_DEFAULT_EXECUTABLE = SAMTOOLS_BUNDLE_DIR / "bin" / "samtools"
SAMTOOLS_OUTPUT_DIR = ROOT_DIR / "outputs" / "samtools"


def _resolve_samtools_executable() -> Path:
    configured = Path(os.getenv("SAMTOOLS_EXECUTABLE", str(SAMTOOLS_DEFAULT_EXECUTABLE)))
    if configured.exists():
        return configured
    fallback = shutil.which("samtools")
    if fallback:
        return Path(fallback)
    raise FileNotFoundError(
        "samtools executable not found. Install it under third_party/samtools or set SAMTOOLS_EXECUTABLE."
    )


def _detect_alignment_kind(path: Path, original_name: str | None = None) -> str:
    lowered = (original_name or path.name).lower()
    if lowered.endswith(".bam"):
        return "BAM"
    if lowered.endswith(".sam"):
        return "SAM"
    if lowered.endswith(".cram"):
        return "CRAM"
    return "alignment"


def _run_command(command: list[str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.setdefault("LANG", "C")
    env.setdefault("LC_ALL", "C")
    return subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def _require_success(name: str, completed: subprocess.CompletedProcess[str]) -> str:
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or f"{name} failed."
        raise RuntimeError(message)
    return completed.stdout


def _header_has_sq_lines(executable: Path, input_path: Path) -> bool:
    header_command = [str(executable), "view", "-H", str(input_path)]
    completed = _run_command(header_command, cwd=ROOT_DIR, timeout=30)
    if completed.returncode != 0:
        return True
    return any(line.startswith("@SQ") for line in completed.stdout.splitlines())


def _validate_alignment_header(executable: Path, input_path: Path, file_kind: str) -> None:
    if file_kind not in {"SAM", "BAM", "CRAM"}:
        return
    if _header_has_sq_lines(executable, input_path):
        return
    raise RuntimeError(
        "The alignment header does not contain any @SQ sequence dictionary lines, so samtools QC cannot run. "
        "Re-export the file with a complete reference header or convert it to a BAM/CRAM with proper @SQ entries first."
    )


def _parse_flagstat(text: str) -> dict[str, float | int]:
    metrics: dict[str, float | int] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        total_match = re.match(r"(\d+) \+ \d+ in total", line)
        if total_match:
            metrics["total_reads"] = int(total_match.group(1))
            continue
        mapped_match = re.match(r"(\d+) \+ \d+ mapped \(([\d.]+)%", line)
        if mapped_match:
            metrics["mapped_reads"] = int(mapped_match.group(1))
            metrics["mapped_rate"] = float(mapped_match.group(2))
            continue
        paired_match = re.match(r"(\d+) \+ \d+ paired in sequencing", line)
        if paired_match:
            metrics["paired_reads"] = int(paired_match.group(1))
            continue
        proper_match = re.match(r"(\d+) \+ \d+ properly paired \(([\d.]+)%", line)
        if proper_match:
            metrics["properly_paired_reads"] = int(proper_match.group(1))
            metrics["properly_paired_rate"] = float(proper_match.group(2))
            continue
        singleton_match = re.match(r"(\d+) \+ \d+ singletons \(([\d.]+)%", line)
        if singleton_match:
            metrics["singleton_reads"] = int(singleton_match.group(1))
            continue
    return metrics


def _parse_stats_highlights(text: str, limit: int) -> list[SamtoolsStatsItem]:
    items: list[SamtoolsStatsItem] = []
    for raw_line in text.splitlines():
        if not raw_line.startswith("SN\t"):
            continue
        parts = raw_line.split("\t")
        if len(parts) < 3:
            continue
        label = parts[1].rstrip(":")
        value = parts[2].strip()
        items.append(SamtoolsStatsItem(label=label, value=value))
        if len(items) >= limit:
            break
    return items


def _parse_idxstats(text: str, limit: int) -> list[SamtoolsIdxstatsRow]:
    rows: list[SamtoolsIdxstatsRow] = []
    for raw_line in text.splitlines():
        parts = raw_line.strip().split("\t")
        if len(parts) != 4:
            continue
        try:
            rows.append(
                SamtoolsIdxstatsRow(
                    contig=parts[0],
                    length_bp=int(parts[1]),
                    mapped=int(parts[2]),
                    unmapped=int(parts[3]),
                )
            )
        except ValueError:
            continue
        if len(rows) >= limit:
            break
    return rows


def _existing_index_path(input_path: Path) -> Path | None:
    candidates = [
        Path(f"{input_path}.bai"),
        input_path.with_suffix(input_path.suffix + ".bai"),
        Path(f"{input_path}.crai"),
        input_path.with_suffix(input_path.suffix + ".crai"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def run_samtools(request: SamtoolsRequest) -> SamtoolsResponse:
    executable = _resolve_samtools_executable()
    input_path = Path(request.raw_path).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Alignment file not found: {request.raw_path}")

    display_name = request.original_name or input_path.name
    file_kind = _detect_alignment_kind(input_path, display_name)
    _validate_alignment_header(executable, input_path, file_kind)
    output_dir = SAMTOOLS_OUTPUT_DIR / uuid.uuid4().hex
    output_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    quickcheck_ok: bool | None = None
    index_path: Path | None = None

    quickcheck_command = [str(executable), "quickcheck", str(input_path)]
    quickcheck_result = _run_command(quickcheck_command, cwd=ROOT_DIR, timeout=30)
    if quickcheck_result.returncode == 0:
        quickcheck_ok = True
    else:
        quickcheck_ok = False
        warnings.append(quickcheck_result.stderr.strip() or quickcheck_result.stdout.strip() or "samtools quickcheck reported an issue.")

    if file_kind in {"BAM", "CRAM"}:
        index_path = _existing_index_path(input_path)
        if index_path is None and request.create_index_if_possible:
            index_suffix = ".bai" if file_kind == "BAM" else ".crai"
            index_path = output_dir / f"{input_path.name}{index_suffix}"
            index_command = [str(executable), "index", "-o", str(index_path), str(input_path)]
            index_result = _run_command(index_command, cwd=ROOT_DIR, timeout=60)
            if index_result.returncode != 0:
                warnings.append(index_result.stderr.strip() or index_result.stdout.strip() or "samtools index failed.")
                index_path = None

    flagstat_command = [str(executable), "flagstat", str(input_path)]
    flagstat_text = _require_success("samtools flagstat", _run_command(flagstat_command, cwd=ROOT_DIR, timeout=60))
    flagstat_metrics = _parse_flagstat(flagstat_text)

    stats_command = [str(executable), "stats", str(input_path)]
    stats_text = _require_success("samtools stats", _run_command(stats_command, cwd=ROOT_DIR, timeout=60))
    stats_highlights = _parse_stats_highlights(stats_text, request.stats_limit)

    idxstats_rows: list[SamtoolsIdxstatsRow] = []
    idxstats_command_preview = ""
    if file_kind in {"BAM", "CRAM"}:
        idxstats_command = [str(executable), "idxstats"]
        if index_path is not None:
            idxstats_command.extend(["-X", str(input_path), str(index_path)])
        else:
            idxstats_command.append(str(input_path))
        idxstats_command_preview = " ".join(idxstats_command)
        idxstats_result = _run_command(idxstats_command, cwd=ROOT_DIR, timeout=30)
        if idxstats_result.returncode == 0:
            idxstats_rows = _parse_idxstats(idxstats_result.stdout, request.idxstats_limit)
        else:
            warnings.append(idxstats_result.stderr.strip() or idxstats_result.stdout.strip() or "samtools idxstats failed.")
    else:
        warnings.append("samtools idxstats was skipped because SAM input is not index-addressable.")

    command_preview_parts = [
        " ".join(quickcheck_command),
        " ".join(flagstat_command),
        " ".join(stats_command),
    ]
    if idxstats_command_preview:
        command_preview_parts.append(idxstats_command_preview)

    return SamtoolsResponse(
        tool="samtools",
        input_path=str(input_path),
        display_name=display_name,
        file_kind=file_kind,
        command_preview=" && ".join(command_preview_parts),
        quickcheck_ok=quickcheck_ok,
        total_reads=int(flagstat_metrics["total_reads"]) if "total_reads" in flagstat_metrics else None,
        mapped_reads=int(flagstat_metrics["mapped_reads"]) if "mapped_reads" in flagstat_metrics else None,
        mapped_rate=float(flagstat_metrics["mapped_rate"]) if "mapped_rate" in flagstat_metrics else None,
        paired_reads=int(flagstat_metrics["paired_reads"]) if "paired_reads" in flagstat_metrics else None,
        properly_paired_reads=(
            int(flagstat_metrics["properly_paired_reads"]) if "properly_paired_reads" in flagstat_metrics else None
        ),
        properly_paired_rate=(
            float(flagstat_metrics["properly_paired_rate"]) if "properly_paired_rate" in flagstat_metrics else None
        ),
        singleton_reads=int(flagstat_metrics["singleton_reads"]) if "singleton_reads" in flagstat_metrics else None,
        index_path=str(index_path) if index_path else None,
        stats_highlights=stats_highlights,
        idxstats_rows=idxstats_rows,
        warnings=warnings,
    )


def execute(payload: dict[str, object]) -> SamtoolsResponse:
    request = SamtoolsRequest(**payload)
    return run_samtools(request)
