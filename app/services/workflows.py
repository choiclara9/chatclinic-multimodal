from __future__ import annotations

import json
import os
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.models import (
    AnalysisFacts,
    AnalysisResponse,
    CountSummaryItem,
    DetailedCountSummaryItem,
    PrsPrepResponse,
    RawQcResponse,
    RankedCandidate,
    RohSegment,
    SummaryStatsResponse,
    SymbolicAltSummary,
    ToolInfo,
    VariantAnnotation,
)
from app.services.annotation import build_draft_answer, build_ui_cards
from app.services.candidate_ranking import build_ranked_candidates
from app.services.fastqc import FASTQC_OUTPUT_DIR
from app.services.recommendation import build_recommendations
from app.services.references import build_reference_bundle
from app.services.roh_analysis import run_roh_analysis
from app.services.prs_prep import analyze_prs_prep
from app.services.summary_stats import analyze_summary_stats
from app.services.tool_runner import discover_tools, run_tool
from app.services.variant_annotation import annotate_variants
from app.services.vcf_summary import summarize_vcf


ROOT_DIR = Path(__file__).resolve().parents[2]
PLUGINS_DIR = ROOT_DIR / "plugins"
WORKFLOWS_DIR = ROOT_DIR / "skills" / "chatgenome-orchestrator" / "workflows"


@lru_cache(maxsize=1)
def load_workflow_manifests() -> list[dict[str, object]]:
    manifests: list[dict[str, object]] = []
    for manifest in sorted(WORKFLOWS_DIR.glob("*.json")):
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict):
            manifests.append(payload)
    return manifests


def list_workflow_manifests(source_type: str | None = None) -> list[dict[str, object]]:
    manifests = load_workflow_manifests()
    if source_type is None:
        return manifests
    normalized = source_type.strip().lower()
    return [
        item
        for item in manifests
        if str(item.get("source_type") or "").strip().lower() == normalized
    ]


def load_workflow_manifest(name: str | None) -> dict[str, object] | None:
    if not name:
        return None
    normalized = str(name).strip().lower()
    for manifest in load_workflow_manifests():
        if str(manifest.get("name") or "").strip().lower() == normalized:
            return manifest
    return None


def snpeff_genome_from_build(genome_build_guess: str | None) -> str:
    value = (genome_build_guess or "").lower()
    if any(token in value for token in ("38", "hg38", "grch38")):
        return "GRCh38.99"
    return "GRCh37.75"


def annotation_key(item: VariantAnnotation) -> tuple[str, int, str, tuple[str, ...]]:
    return (item.contig, item.pos_1based, item.ref, tuple(item.alts))


def analyze_vcf_workflow(
    path: str,
    annotation_scope: str = "representative",
    annotation_limit: int | None = None,
) -> AnalysisResponse:
    max_examples = int(os.getenv("MAX_EXAMPLE_VARIANTS", "8"))
    used_tools: list[str] = []
    tool_registry = discover_tools()

    try:
        qc_result = run_tool(
            "vcf_qc_tool",
            {
                "vcf_path": path,
                "max_examples": max_examples,
            },
        )
        facts = AnalysisFacts(**qc_result["facts"])
        used_tools.append("vcf_qc_tool")
    except Exception:
        facts = summarize_vcf(path, max_examples=max_examples)

    try:
        annotation_result = run_tool(
            "annotation_tool",
            {
                "vcf_path": path,
                "facts": facts.model_dump(),
                "scope": annotation_scope,
                "limit": annotation_limit,
            },
        )
        annotations = [VariantAnnotation(**item) for item in annotation_result["annotations"]]
        used_tools.append("annotation_tool")
    except Exception:
        annotations = annotate_variants(
            path,
            facts,
            scope=annotation_scope,
            limit=annotation_limit,
        )

    snpeff_result = None
    try:
        snpeff_payload = run_tool(
            "snpeff_execution_tool",
            {
                "vcf_path": path,
                "genome": snpeff_genome_from_build(facts.genome_build_guess),
                "output_prefix": f"{Path(path).stem}.aux",
                "parse_limit": 10,
            },
        )
        from app.models import SnpEffResponse

        snpeff_result = SnpEffResponse(**snpeff_payload)
        used_tools.append("snpeff_execution_tool")
    except Exception:
        snpeff_result = None

    try:
        roh_result = run_tool("roh_analysis_tool", {"vcf_path": path})
        roh_segments = [RohSegment(**item) for item in roh_result["roh_segments"]]
        used_tools.append("roh_analysis_tool")
    except Exception:
        roh_segments = run_roh_analysis(path)

    preliminary_candidates = build_ranked_candidates(annotations, roh_segments, limit=24)
    shortlisted_annotations = [entry.item for entry in preliminary_candidates]
    try:
        cadd_result = run_tool(
            "cadd_lookup_tool",
            {
                "annotations": [item.model_dump() for item in shortlisted_annotations],
                "genome_build_guess": facts.genome_build_guess,
            },
        )
        enriched_shortlisted_annotations = [VariantAnnotation(**item) for item in cadd_result["annotations"]]
        if bool(cadd_result.get("lookup_performed")):
            used_tools.append("cadd_lookup_tool")
        enriched_by_key = {annotation_key(item): item for item in enriched_shortlisted_annotations}
        annotations = [enriched_by_key.get(annotation_key(item), item) for item in annotations]
    except Exception:
        enriched_shortlisted_annotations = shortlisted_annotations

    try:
        revel_result = run_tool(
            "revel_lookup_tool",
            {
                "annotations": [item.model_dump() for item in enriched_shortlisted_annotations],
                "genome_build_guess": facts.genome_build_guess,
            },
        )
        revel_enriched_annotations = [VariantAnnotation(**item) for item in revel_result["annotations"]]
        if bool(revel_result.get("lookup_performed")):
            used_tools.append("revel_lookup_tool")
        revel_by_key = {annotation_key(item): item for item in revel_enriched_annotations}
        annotations = [revel_by_key.get(annotation_key(item), item) for item in annotations]
        enriched_shortlisted_annotations = [
            revel_by_key.get(annotation_key(item), item) for item in enriched_shortlisted_annotations
        ]
    except Exception:
        pass

    try:
        candidate_result = run_tool(
            "candidate_ranking_tool",
            {
                "annotations": [item.model_dump() for item in enriched_shortlisted_annotations],
                "roh_segments": [item.model_dump() for item in roh_segments],
                "limit": 8,
            },
        )
        candidate_variants = [RankedCandidate(**item) for item in candidate_result["candidate_variants"]]
        used_tools.append("candidate_ranking_tool")
    except Exception:
        candidate_variants = build_ranked_candidates(enriched_shortlisted_annotations, roh_segments, limit=8)

    try:
        clinvar_result = run_tool(
            "clinvar_review_tool",
            {"annotations": [item.model_dump() for item in annotations]},
        )
        clinvar_summary = [CountSummaryItem(**item) for item in clinvar_result["clinvar_summary"]]
        used_tools.append("clinvar_review_tool")
    except Exception:
        counts: dict[str, int] = {}
        for item in annotations:
            key = (
                item.clinical_significance.strip()
                if item.clinical_significance and item.clinical_significance != "."
                else "Unreviewed"
            )
            counts[key] = counts.get(key, 0) + 1
        clinvar_summary = [
            CountSummaryItem(label=label, count=count)
            for label, count in sorted(counts.items(), key=lambda part: part[1], reverse=True)
        ]

    try:
        consequence_result = run_tool(
            "vep_consequence_tool",
            {
                "annotations": [item.model_dump() for item in annotations],
                "limit": 10,
            },
        )
        consequence_summary = [CountSummaryItem(**item) for item in consequence_result["consequence_summary"]]
        used_tools.append("vep_consequence_tool")
    except Exception:
        counts = {}
        for item in annotations:
            key = item.consequence.strip() if item.consequence and item.consequence != "." else "Unclassified"
            counts[key] = counts.get(key, 0) + 1
        consequence_summary = [
            CountSummaryItem(label=label, count=count)
            for label, count in sorted(counts.items(), key=lambda part: part[1], reverse=True)[:10]
        ]

    try:
        coverage_result = run_tool(
            "clinical_coverage_tool",
            {"annotations": [item.model_dump() for item in annotations]},
        )
        clinical_coverage_summary = [
            DetailedCountSummaryItem(**item) for item in coverage_result["clinical_coverage_summary"]
        ]
        used_tools.append("clinical_coverage_tool")
    except Exception:
        total = len(annotations)

        def detail(label: str, count: int) -> DetailedCountSummaryItem:
            percent = round((count / total) * 100) if total else 0
            return DetailedCountSummaryItem(label=label, count=count, detail=f"{count}/{total} annotated ({percent}%)")

        clinical_coverage_summary = [
            detail(
                "ClinVar coverage",
                sum(
                    1
                    for item in annotations
                    if (item.clinical_significance and item.clinical_significance != ".")
                    or (item.clinvar_conditions and item.clinvar_conditions != ".")
                ),
            ),
            detail("gnomAD coverage", sum(1 for item in annotations if item.gnomad_af and item.gnomad_af != ".")),
            detail("Gene mapping", sum(1 for item in annotations if item.gene and item.gene != ".")),
            detail(
                "HGVS coverage",
                sum(1 for item in annotations if (item.hgvsc and item.hgvsc != ".") or (item.hgvsp and item.hgvsp != ".")),
            ),
            detail("Protein change", sum(1 for item in annotations if item.hgvsp and item.hgvsp != ".")),
        ]

    try:
        filtering_result = run_tool(
            "filtering_view_tool",
            {"annotations": [item.model_dump() for item in annotations]},
        )
        filtering_summary = [DetailedCountSummaryItem(**item) for item in filtering_result["filtering_summary"]]
        used_tools.append("filtering_view_tool")
    except Exception:
        unique_genes = {item.gene.strip() for item in annotations if item.gene and item.gene.strip() not in {"", "."}}
        clinvar_labeled = sum(1 for item in annotations if item.clinical_significance and item.clinical_significance != ".")
        symbolic = sum(1 for item in annotations if any(alt.startswith("<") and alt.endswith(">") for alt in item.alts))
        filtering_summary = [
            DetailedCountSummaryItem(
                label="Annotated rows", count=len(annotations), detail=f"{len(annotations)} rows currently available in the triage table"
            ),
            DetailedCountSummaryItem(
                label="Distinct genes", count=len(unique_genes), detail=f"{len(unique_genes)} genes represented in the annotated subset"
            ),
            DetailedCountSummaryItem(
                label="ClinVar-labeled rows",
                count=clinvar_labeled,
                detail=f"{clinvar_labeled} rows contain a ClinVar-style significance label",
            ),
            DetailedCountSummaryItem(
                label="Symbolic ALT rows",
                count=symbolic,
                detail=f"{symbolic} rows are symbolic ALT records that may need separate handling",
            ),
        ]

    try:
        symbolic_result = run_tool(
            "symbolic_alt_tool",
            {"annotations": [item.model_dump() for item in annotations]},
        )
        symbolic_alt_summary = SymbolicAltSummary(**symbolic_result["symbolic_alt_summary"])
        used_tools.append("symbolic_alt_tool")
    except Exception:
        symbolic_items = [item for item in annotations if any(alt.startswith("<") and alt.endswith(">") for alt in item.alts)]
        symbolic_alt_summary = SymbolicAltSummary(
            count=len(symbolic_items),
            examples=[
                {
                    "locus": f"{item.contig}:{item.pos_1based}",
                    "gene": item.gene or "",
                    "alts": item.alts,
                    "consequence": item.consequence or "",
                    "genotype": item.genotype or "",
                }
                for item in symbolic_items[:5]
            ],
        )

    reference_annotations = annotations[: min(len(annotations), 20)]
    references = build_reference_bundle(facts, reference_annotations)
    recommendations = build_recommendations(facts)
    ui_cards = build_ui_cards(facts, annotations)
    try:
        summary_result = run_tool(
            "grounded_summary_tool",
            {
                "facts": facts.model_dump(),
                "annotations": [item.model_dump() for item in annotations],
                "references": [item.model_dump() for item in references],
                "recommendations": [item.model_dump() for item in recommendations],
            },
        )
        draft_answer = str(summary_result["draft_answer"])
        used_tools.append("grounded_summary_tool")
    except Exception:
        draft_answer = build_draft_answer(
            facts,
            annotations,
            [item.id for item in references],
            [item.id for item in recommendations],
        )

    return AnalysisResponse(
        analysis_id=str(uuid.uuid4()),
        facts=facts,
        annotations=annotations,
        roh_segments=roh_segments,
        source_vcf_path=path,
        snpeff_result=snpeff_result,
        candidate_variants=candidate_variants,
        clinvar_summary=clinvar_summary,
        consequence_summary=consequence_summary,
        clinical_coverage_summary=clinical_coverage_summary,
        filtering_summary=filtering_summary,
        symbolic_alt_summary=symbolic_alt_summary,
        references=references,
        recommendations=recommendations,
        ui_cards=ui_cards,
        draft_answer=draft_answer,
        used_tools=used_tools,
        tool_registry=tool_registry,
    )


def analyze_raw_qc_workflow(path: str, original_name: str) -> RawQcResponse:
    try:
        result = run_tool(
            "fastqc_execution_tool",
            {
                "raw_path": path,
                "original_name": original_name,
            },
        )
        return RawQcResponse(**result)
    except Exception as exc:
        raise RuntimeError(f"Raw QC failed: {exc}") from exc


def analyze_summary_stats_workflow(
    path: str,
    original_name: str,
    genome_build: str = "unknown",
    trait_type: str = "unknown",
) -> SummaryStatsResponse:
    result = analyze_summary_stats(path, original_name, genome_build=genome_build, trait_type=trait_type)
    result.analysis_id = str(uuid.uuid4())
    result.tool_registry = discover_tools()
    return result


def analyze_prs_prep_workflow(
    path: str,
    original_name: str,
    genome_build: str = "unknown",
) -> PrsPrepResponse:
    result = analyze_prs_prep(path, original_name, genome_build=genome_build)
    result.analysis_id = str(uuid.uuid4())
    return result


def run_registered_summary_stats_workflow(
    workflow_name: str,
    analysis: SummaryStatsResponse,
) -> dict[str, object]:
    manifest = load_workflow_manifest(workflow_name)
    if manifest is None:
        raise ValueError(f"Unknown summary-statistics workflow: {workflow_name}")
    source_type = str(manifest.get("source_type") or "").strip().lower()
    if source_type != "summary_stats":
        raise ValueError(f"Workflow {workflow_name} is not registered for summary-statistics sources.")

    requires = [str(item).strip() for item in manifest.get("requires", []) if str(item).strip()]
    if "source_stats_path" in requires and not analysis.source_stats_path:
        raise RuntimeError(
            "The active summary-statistics session does not expose a durable source file path, so this workflow cannot be rerun from chat."
        )

    if workflow_name == "prs_prep":
        prs_prep_result = analyze_prs_prep_workflow(
            analysis.source_stats_path or "",
            analysis.file_name,
            genome_build=analysis.genome_build,
        )
        refreshed = analysis.model_copy(update={"prs_prep_result": prs_prep_result})
        requested_view = str(manifest.get("requested_view") or "prs_prep")
        answer = (
            "The prs_prep workflow was run on the active summary-statistics source.\n\n"
            f"- Workflow: `{workflow_name}`\n"
            f"- Active file: `{prs_prep_result.file_name}`\n"
            f"- Build check: {prs_prep_result.build_check.inferred_build} ({prs_prep_result.build_check.build_confidence})\n"
            f"- Score-file rows kept: {prs_prep_result.kept_rows}\n"
            f"- Score-file rows dropped: {prs_prep_result.dropped_rows}\n"
            f"- Score file ready: {'yes' if prs_prep_result.score_file_ready else 'no'}\n\n"
            "The PRS Prep Review state has been added to Studio. Use `$studio ...` to ask grounded questions about build check, harmonization, or score-file readiness."
        )
        return {
            "answer": answer,
            "analysis": refreshed,
            "requested_view": requested_view,
            "prs_prep_result": prs_prep_result,
        }

    raise NotImplementedError(f"Workflow {workflow_name} is registered but not yet executable in the generic summary-statistics runner.")
