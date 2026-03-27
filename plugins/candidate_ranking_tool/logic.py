from __future__ import annotations

from app.models import RankedCandidate, RohSegment, VariantAnnotation


def is_variant_in_roh(item: VariantAnnotation, roh_segments: list[RohSegment] | None) -> bool:
    if not roh_segments:
        return False
    return any(
        segment.contig == item.contig
        and item.pos_1based >= segment.start_1based
        and item.pos_1based <= segment.end_1based
        for segment in roh_segments
    )


def rank_candidate_score(item: VariantAnnotation) -> int:
    score = 0
    significance = (item.clinical_significance or "").lower()
    consequence = (item.consequence or "").lower()
    af = _parse_af(item.gnomad_af)

    if "pathogenic" in significance:
        score += 5
    elif "vus" in significance:
        score += 2
    elif "benign" in significance:
        score -= 2

    if "splice" in consequence:
        score += 4
    elif "missense" in consequence:
        score += 3
    elif "stop" in consequence or "frameshift" in consequence:
        score += 5
    elif "synonymous" in consequence:
        score -= 1

    if af is not None:
        if af < 0.001:
            score += 3
        elif af < 0.01:
            score += 2
        elif af > 0.05:
            score -= 2

    if item.genotype == "1/1":
        score += 1

    score += _cadd_bonus(item.cadd_phred)
    score += _revel_bonus(item.revel_score)

    return score


def rank_recessive_score(item: VariantAnnotation, roh_segments: list[RohSegment] | None) -> int:
    score = 0
    consequence = (item.consequence or "").lower()
    significance = (item.clinical_significance or "").lower()
    af = _parse_af(item.gnomad_af)

    if item.genotype == "1/1":
        score += 4
    if is_variant_in_roh(item, roh_segments):
        score += 5
    if "splice" in consequence:
        score += 4
    elif "missense" in consequence:
        score += 3
    elif "stop" in consequence or "frameshift" in consequence:
        score += 5
    elif "synonymous" in consequence:
        score -= 2

    if af is not None:
        if af < 0.001:
            score += 4
        elif af < 0.01:
            score += 2
        elif af > 0.05:
            score -= 3

    if "pathogenic" in significance:
        score += 3
    elif "benign" in significance:
        score -= 3

    score += _cadd_bonus(item.cadd_phred)
    score += _revel_bonus(item.revel_score)

    return score


def build_ranked_candidates(
    annotations: list[VariantAnnotation],
    roh_segments: list[RohSegment] | None,
    limit: int = 8,
) -> list[RankedCandidate]:
    ranked = [
        RankedCandidate(
            item=item,
            score=rank_candidate_score(item) + (3 if is_variant_in_roh(item, roh_segments) else 0) + (1 if item.genotype == "1/1" else 0),
            in_roh=is_variant_in_roh(item, roh_segments),
        )
        for item in annotations
    ]
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[:limit]


def _parse_af(raw_value: str) -> float | None:
    if not raw_value:
        return None
    token = raw_value.strip().split(" ", 1)[0]
    try:
        return float(token)
    except ValueError:
        return None


def _cadd_bonus(phred: float | None) -> int:
    if phred is None:
        return 0
    if phred >= 30:
        return 4
    if phred >= 20:
        return 3
    if phred >= 15:
        return 2
    if phred >= 10:
        return 1
    return 0


def _revel_bonus(score: float | None) -> int:
    if score is None:
        return 0
    if score >= 0.9:
        return 4
    if score >= 0.75:
        return 3
    if score >= 0.5:
        return 2
    if score >= 0.25:
        return 1
    return 0


def execute(payload: dict[str, object]) -> dict[str, object]:
    annotations = [VariantAnnotation(**item) for item in payload.get("annotations", [])]
    roh_segments = [RohSegment(**item) for item in payload.get("roh_segments", [])]
    limit = int(payload.get("limit", 8))
    ranked = build_ranked_candidates(annotations, roh_segments, limit=limit)
    return {"candidate_variants": [item.model_dump() for item in ranked]}
