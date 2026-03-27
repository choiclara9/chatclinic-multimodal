from __future__ import annotations

import csv
import gzip
import os
from pathlib import Path
from typing import Iterable

from app.models import VariantAnnotation


def enrich_annotations_with_cadd(
    annotations: list[VariantAnnotation],
    genome_build_guess: str | None = None,
) -> tuple[list[VariantAnnotation], bool, int]:
    db_path = _resolve_cadd_db_path(genome_build_guess)
    if db_path is None:
        return [_with_lookup_status(item, "not-configured") for item in annotations], False, 0
    if not db_path.exists():
        return [_with_lookup_status(item, "db-missing") for item in annotations], False, 0

    enriched: list[VariantAnnotation] = []
    matched_count = 0
    for item in annotations:
        best_match = _lookup_best_match(db_path, item)
        if best_match is None:
            enriched.append(_with_lookup_status(item, "not-found"))
            continue
        raw_score, phred_score = best_match
        enriched.append(
            item.model_copy(
                update={
                    "cadd_raw_score": raw_score,
                    "cadd_phred": phred_score,
                    "cadd_lookup_status": "matched",
                }
            )
        )
        matched_count += 1

    return enriched, True, matched_count


def _resolve_cadd_db_path(genome_build_guess: str | None) -> Path | None:
    build = (genome_build_guess or "").lower()
    env_key = "CADD_LOOKUP_FILE"
    if any(token in build for token in ("38", "hg38", "grch38")):
        env_key = "CADD_LOOKUP_FILE_GRCH38"
    elif any(token in build for token in ("37", "hg19", "grch37")):
        env_key = "CADD_LOOKUP_FILE_GRCH37"

    explicit = os.getenv(env_key) or os.getenv("CADD_LOOKUP_FILE")
    if explicit:
        return Path(explicit).expanduser().resolve()

    root = Path(__file__).resolve().parents[2]
    candidate_paths = []
    if env_key == "CADD_LOOKUP_FILE_GRCH38":
        candidate_paths.extend([root / "data/cadd/GRCh38.tsv.gz", root / "data/cadd/GRCh38.tsv"])
    elif env_key == "CADD_LOOKUP_FILE_GRCH37":
        candidate_paths.extend([root / "data/cadd/GRCh37.tsv.gz", root / "data/cadd/GRCh37.tsv"])
    candidate_paths.extend([root / "data/cadd/cadd_lookup.tsv.gz", root / "data/cadd/cadd_lookup.tsv"])
    for path in candidate_paths:
        if path.exists():
            return path.resolve()
    return None


def _lookup_best_match(db_path: Path, item: VariantAnnotation) -> tuple[float | None, float | None] | None:
    best: tuple[float | None, float | None] | None = None
    normalized_item_contig = _normalize_contig(item.contig)
    for row in _iter_cadd_rows(db_path):
        if _normalize_contig(str(row.get("chrom", ""))) != normalized_item_contig:
            continue
        if _to_int(row.get("pos")) != item.pos_1based:
            continue
        if str(row.get("ref", "")).upper() != item.ref.upper():
            continue
        row_alt = str(row.get("alt", "")).upper()
        if not any(row_alt == alt.upper() for alt in item.alts):
            continue

        candidate = (_to_float(row.get("raw")), _to_float(row.get("phred")))
        if best is None:
            best = candidate
            continue
        current_phred = candidate[1] if candidate[1] is not None else float("-inf")
        best_phred = best[1] if best[1] is not None else float("-inf")
        if current_phred > best_phred:
            best = candidate
    return best


def _iter_cadd_rows(db_path: Path) -> Iterable[dict[str, str]]:
    opener = gzip.open if db_path.suffix == ".gz" else open
    with opener(db_path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header_map: dict[int, str] | None = None
        for raw_row in reader:
            if not raw_row or raw_row[0].startswith("#"):
                continue
            if header_map is None:
                lowered = [cell.strip().lower() for cell in raw_row]
                if {"chrom", "pos", "ref", "alt"} <= set(lowered):
                    header_map = {index: name for index, name in enumerate(lowered)}
                    continue
                header_map = {0: "chrom", 1: "pos", 2: "ref", 3: "alt", 4: "raw", 5: "phred"}
            row = {header_map[index]: value for index, value in enumerate(raw_row) if index in header_map}
            yield {
                "chrom": row.get("chrom", row.get("#chrom", "")),
                "pos": row.get("pos", ""),
                "ref": row.get("ref", ""),
                "alt": row.get("alt", ""),
                "raw": row.get("raw", row.get("rawscore", "")),
                "phred": row.get("phred", row.get("phredscore", "")),
            }


def _normalize_contig(contig: str) -> str:
    value = contig.strip().lower()
    if value.startswith("chr"):
        return value[3:]
    return value


def _to_float(raw_value: str | None) -> float | None:
    if raw_value in (None, ""):
        return None
    try:
        return float(raw_value)
    except ValueError:
        return None


def _to_int(raw_value: str | None) -> int | None:
    if raw_value in (None, ""):
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None


def _with_lookup_status(item: VariantAnnotation, status: str) -> VariantAnnotation:
    return item.model_copy(update={"cadd_lookup_status": status})


def execute(payload: dict[str, object]) -> dict[str, object]:
    annotations = [VariantAnnotation(**item) for item in payload.get("annotations", [])]
    genome_build_guess = payload.get("genome_build_guess")
    enriched, lookup_performed, matched_count = enrich_annotations_with_cadd(annotations, genome_build_guess)  # type: ignore[arg-type]
    return {
        "annotations": [item.model_dump() for item in enriched],
        "lookup_performed": lookup_performed,
        "matched_count": matched_count,
    }
