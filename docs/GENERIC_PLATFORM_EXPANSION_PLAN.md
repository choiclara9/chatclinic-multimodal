# Generic Platform Expansion Plan

## Goal

This project moved from a genomics-specific application to a generic multimodal clinical platform.

The target architecture:

- Adding a new tool requires only `plugins/<tool>/tool.json` and `plugins/<tool>/logic.py`
- Adding a new source type requires a source registry entry, bootstrap manifest, and renderer
- Core files (`main.py`, `chat.py`, `workflows.py`, `page.tsx`) should not need routine changes

## Supported Input Formats

| Category | Formats | Status |
|----------|---------|--------|
| Genomics | VCF, FASTQ/BAM/SAM, summary statistics | Complete |
| Imaging | DICOM, PNG/JPG/TIFF | Complete |
| Clinical structured | FHIR bundles (.fhir.json, .fhir.xml, .ndjson) | Complete |
| Tabular | Excel workbooks | Complete |
| Text | Plain text, markdown notes | Complete |

## Completed Stages

### Stage 1. Direct `@tool` genericization — Complete

Direct tool execution is metadata-driven via `tool.json` manifests. Tools: liftover, samtools, qqman, snpeff, ldblockshow, plink.

### Stage 2. Workflow dispatch — Complete

Workflow dispatch uses structured manifests. `chat.py` is a parser/router, not a dispatch table.

### Stage 3. Workflow manifests as structured batch definitions — Complete

Workflow manifests carry `source_type`, `requested_view`, `response_kind`, `answer_template`, and structured steps.

### Stage 4. Metadata-first workflow step execution — Complete

`tool.json.workflow_binding` drives step execution with `input_map`, `result_path`, `transform`, and `fallback_transform`.

### Stage 5. Transform, fallback, and hook registries — Complete

Domain-specific execution details moved to:
- `app/services/workflow_transforms.py`
- `app/services/workflow_fallbacks.py`
- `app/services/workflow_hooks.py`
- `app/services/workflow_internal_steps.py`
- `app/services/workflow_responses.py`

### Stage 6. Bootstrap-driven source initialization — Complete

Upload endpoints use `source_bootstrap.py` with bootstrap manifests under `skills/chatgenome-orchestrator/bootstrap/`.

### Stage 7. Generic source registry — Complete

`app/services/source_registry.py` defines all source types with detection rules, bootstrap mapping, initial tools, and Studio renderers.

### Stage 8. Generic Studio renderer layer — Complete

Renderer registry in `studioRenderers.tsx` with generic and custom renderer components. Fallback rendering available for unrecognized result types.

### Stage 9. Spreadsheet and text inputs — Complete

Excel workbooks and text/markdown notes are first-class source types with bootstrap, chat, and Studio cards.

### Stage 10. DICOM and raster image inputs — Complete

DICOM and PNG/JPG/TIFF images supported with metadata extraction, preview, and Studio cards.

### Stage 11. FHIR clinical bundles — Complete

FHIR JSON/XML/NDJSON bundles parsed into patient, observation, medication, allergy, vital, timeline, lab, and care team artifacts with a dedicated browser card.

## Architecture Summary

### Multi-source auto-detect

The `@mode`/`@skill` command system was replaced with automatic source type detection on upload. Multiple sources can coexist in a single session with cross-source grounded chat.

### Source lifecycle

1. User uploads a file
2. Frontend detects source type by filename
3. Dedicated upload endpoint calls source registry + bootstrap
4. Bootstrap manifest runs initial tools
5. Studio cards render tool outputs
6. Chat endpoints provide source-type-specific conversation

### Key files

| File | Role |
|------|------|
| `app/services/source_registry.py` | Source type definitions and detection |
| `app/services/source_bootstrap.py` | Bootstrap launcher |
| `app/services/tool_runner.py` | Plugin execution (entrypoint-first) |
| `app/services/workflows.py` | Workflow orchestration |
| `app/services/chat.py` | Chat dispatch and response assembly |
| `skills/chatgenome-orchestrator/SKILL.md` | Policy, welcome/help messages, rules |
| `webapp/app/components/studioRenderers.tsx` | Renderer registry and dispatch |

## Remaining Work

- HL7 message support (not yet started)
- IGV genome browser viewer card
- Further reduction of VCF-specific inline rendering in `page.tsx`
- Continue shrinking `chat.py` into a pure parser/router
