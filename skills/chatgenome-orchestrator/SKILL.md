---
name: chatgenome-orchestrator
description: Use when ChatGenome should decide which genomics analysis tools to run, in which order, and how to explain the resulting Studio state.
---

# ChatGenome Orchestrator

This skill defines the intended orchestration layer for `ChatGenome`.

## Purpose

Use this skill when deciding which registered genomics tool should be used for a user request or an upload workflow.

## Workflow prompts

### Initial scope prompt

{file_name} 파일을 받았습니다. VCF analysis scope와 range(limit)를 입력해 주세요. 별도 지시가 없으면 representative로 시작합니다. 예: all로 200개, representative로 진행.

The architecture target is:

1. ChatGenome receives a VCF and user request.
2. The orchestrator chooses one or more tools from the registry.
3. The shared runner executes those tools.
4. Studio cards render the tool outputs.
5. Chat explains the grounded outputs, not raw VCF rows.

## Initial tool ordering

For the current migration stage, the preferred initial order is:

1. `vcf_qc_tool`
2. `annotation_tool`
3. `roh_analysis_tool`
4. `snpeff_execution_tool` when the user explicitly requests local SnpEff annotation
5. `cadd_lookup_tool`
6. `revel_lookup_tool`
7. `candidate_ranking_tool`
8. `grounded_summary_tool`
9. `clinvar_review_tool`
10. `vep_consequence_tool`
11. `clinical_coverage_tool`
12. `filtering_view_tool`
13. `symbolic_alt_tool`
14. `ldblockshow_execution_tool` when the user explicitly requests locus-level LD heatmap visualization for a VCF region

Later tools should include:

11. `igv_snapshot_tool`

## Rules

- Always prefer deterministic genomics tools over free-form model interpretation.
- Use `vcf_qc_tool` to establish base facts for any VCF workflow.
- Use `annotation_tool` to generate transcript-aware annotation state before downstream ranking.
- Use `snpeff_execution_tool` when the user explicitly asks to run SnpEff on a local VCF and the required local Java runtime, jar, and genome database are available.
- Use `ldblockshow_execution_tool` when the user explicitly asks for LD heatmap or block visualization over a region and provides or implies a concrete locus in `chr:start:end` format.
- Use `cadd_lookup_tool` to enrich shortlisted annotated variants with local CADD scores when a build-matched local table is available.
- Use `revel_lookup_tool` to enrich shortlisted missense variants with local REVEL scores when a matching local segment file is available.
- Use `roh_analysis_tool` when ROH/recessive review is shown or requested.
- Use `candidate_ranking_tool` to populate the ranked shortlist shown in Studio after optional score enrichment such as local CADD and REVEL lookup.
- Use `grounded_summary_tool` to compose the narrative answer from trusted tool-derived state.
- Use `clinvar_review_tool` to populate the clinical significance distribution.
- Use `vep_consequence_tool` to populate the consequence distribution shown in Studio.
- Use `clinical_coverage_tool` to summarize annotation completeness.
- Use `filtering_view_tool` to populate filtering/triage overview metrics for the variant table.
- Use `symbolic_alt_tool` to split symbolic ALT records into a dedicated review path.
- Chat should refer to tool outputs and Studio summaries as the trusted state.
- If a tool fails, preserve the prior direct implementation as fallback until migration is complete.

## Output expectations

The orchestrator should ensure that:

- used tool names are recorded
- registry tools are discoverable
- Studio cards can be traced to tool outputs
- grounded chat cites the current tool-derived state
