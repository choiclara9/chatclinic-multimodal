from __future__ import annotations

import csv
import os
from pathlib import Path

from app.models import VariantAnnotation


def enrich_annotations_with_revel(
    annotations: list[VariantAnnotation],
    genome_build_guess: str | None = None,
) -> tuple[list[VariantAnnotation], bool, int]:
    revel_root = _resolve_revel_root()
    if revel_root is None or not revel_root.exists():
        return [_with_revel_status(item, "not-configured") for item in annotations], False, 0

    position_field = "grch38_pos" if _is_grch38(genome_build_guess) else "hg19_pos"
    enriched: list[VariantAnnotation] = []
    matched = 0
    performed = False
    for item in annotations:
        if "missense" not in (item.consequence or "").lower():
            enriched.append(_with_revel_status(item, "not-applicable"))
            continue
        performed = True
        score = _lookup_revel_score(revel_root, item, position_field)
        if score is None:
            enriched.append(_with_revel_status(item, "not-found"))
            continue
        enriched.append(item.model_copy(update={"revel_score": score, "revel_lookup_status": "matched"}))
        matched += 1
    return enriched, performed, matched


def _resolve_revel_root() -> Path | None:
    explicit = os.getenv("REVEL_LOOKUP_DIR")
    if explicit:
        return Path(explicit).expanduser().resolve()
    root = Path(__file__).resolve().parents[2]
    candidate = root / "data/revel/source/chrom01/revel-v1.3_segments_chrom_01"
    if candidate.exists():
        return candidate.resolve()
    return None


def _lookup_revel_score(revel_root: Path, item: VariantAnnotation, position_field: str) -> float | None:
    contig = _normalize_contig(item.contig)
    if contig != "1":
        return None
    target_pos = item.pos_1based
    target_ref = item.ref.upper()
    target_alts = {alt.upper() for alt in item.alts}

    segment_path = _segment_for_position(revel_root, target_pos, position_field)
    if segment_path is None:
        return None

    with segment_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if _normalize_contig(row.get("chr", "")) != contig:
                continue
            try:
                row_pos = int(row.get(position_field, "") or 0)
            except ValueError:
                continue
            if row_pos != target_pos:
                continue
            if (row.get("ref") or "").upper() != target_ref:
                continue
            if (row.get("alt") or "").upper() not in target_alts:
                continue
            try:
                return float(row.get("REVEL", ""))
            except ValueError:
                return None
    return None


def _segment_for_position(revel_root: Path, pos: int, position_field: str) -> Path | None:
    for path in revel_root.glob("*.csv"):
        stem = path.stem
        try:
            parts = stem.rsplit("_", 2)
            if len(parts) != 3:
                continue
            start = int(parts[1])
            end = int(parts[2])
        except ValueError:
            continue
        if start <= pos <= end:
            return path
    return None


def _normalize_contig(contig: str) -> str:
    value = (contig or "").strip().lower()
    return value[3:] if value.startswith("chr") else value


def _is_grch38(genome_build_guess: str | None) -> bool:
    value = (genome_build_guess or "").lower()
    return any(token in value for token in ("38", "hg38", "grch38"))


def _with_revel_status(item: VariantAnnotation, status: str) -> VariantAnnotation:
    return item.model_copy(update={"revel_lookup_status": status})


def execute(payload: dict[str, object]) -> dict[str, object]:
    annotations = [VariantAnnotation(**item) for item in payload.get("annotations", [])]
    genome_build_guess = payload.get("genome_build_guess")
    enriched, lookup_performed, matched_count = enrich_annotations_with_revel(annotations, genome_build_guess)  # type: ignore[arg-type]
    return {
        "annotations": [item.model_dump() for item in enriched],
        "lookup_performed": lookup_performed,
        "matched_count": matched_count,
    }
