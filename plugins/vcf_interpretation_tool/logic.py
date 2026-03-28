from __future__ import annotations

from app.models import AnalysisFacts, RohSegment, VariantAnnotation
from plugins.annotation_tool.logic import annotate_variants
from plugins.cadd_lookup_tool.logic import enrich_annotations_with_cadd
from plugins.candidate_ranking_tool.logic import build_ranked_candidates
from plugins.revel_lookup_tool.logic import enrich_annotations_with_revel
from plugins.roh_analysis_tool.logic import run_roh_analysis
from plugins.vcf_qc_tool.logic import summarize_vcf


def execute(payload: dict[str, object]) -> dict[str, object]:
    vcf_path = str(payload["vcf_path"])
    if "facts" in payload and payload.get("facts") is not None:
        facts = AnalysisFacts(**payload["facts"])
    else:
        facts = summarize_vcf(vcf_path, max_examples=int(payload.get("max_examples", 8)))
    scope = str(payload.get("scope", "representative"))
    annotation_limit = payload.get("annotation_limit")
    ranking_limit = int(payload.get("ranking_limit", 8))

    annotations = annotate_variants(
        vcf_path,
        facts,
        scope=scope,
        limit=annotation_limit,
    )
    roh_segments = run_roh_analysis(vcf_path)

    annotations_after_cadd, cadd_lookup_performed, cadd_matched_count = enrich_annotations_with_cadd(
        annotations,
        facts.genome_build_guess,
    )
    annotations_after_revel, revel_lookup_performed, revel_matched_count = enrich_annotations_with_revel(
        annotations_after_cadd,
        facts.genome_build_guess,
    )
    candidate_variants = build_ranked_candidates(
        annotations_after_revel,
        roh_segments,
        limit=ranking_limit,
    )

    return {
        "tool": "vcf_interpretation_tool",
        "annotations": [item.model_dump() for item in annotations_after_revel],
        "roh_segments": [item.model_dump() for item in roh_segments],
        "candidate_variants": [item.model_dump() for item in candidate_variants],
        "annotation_count": len(annotations_after_revel),
        "roh_segment_count": len(roh_segments),
        "candidate_count": len(candidate_variants),
        "cadd_lookup_performed": cadd_lookup_performed,
        "cadd_matched_count": cadd_matched_count,
        "revel_lookup_performed": revel_lookup_performed,
        "revel_matched_count": revel_matched_count,
        "summary": (
            f"Interpreted {facts.file_name}: "
            f"{len(annotations_after_revel)} annotation(s), "
            f"{len(roh_segments)} ROH segment(s), "
            f"{len(candidate_variants)} ranked candidate(s)."
        ),
    }
