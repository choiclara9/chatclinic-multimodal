# Frontend Renderer Inventory

## Goal

Inventory the current Studio rendering in `webapp/app/page.tsx` to determine:

- Which parts can be absorbed into a generic renderer
- Which parts must remain as custom cards
- What extraction order is safest

## Current Studio Surface

Studio views are dispatched through the `StudioView` union and a renderer registry (`studioRenderers.tsx`).

Current renderer categories:

- **Generic renderers** (`genericStudioRenderers.tsx`): reusable metric/list/artifact/table cards
- **Custom renderers** (`customStudioRenderers.tsx`): domain-specific cards with interactive state

Current StudioView values include: `qc`, `candidates`, `annotations`, `clinvar`, `vep`, `roh`, `symbolic`, `rawqc`, `sumstats`, `prs_prep`, `qqman`, `samtools`, `snpeff`, `plink`, `liftover`, `ldblockshow`, `dicom_review`, `image_review`, `fhir_browser`, `text_review`, `cohort_browser`, and others.

## Source Shell

The three-column layout is shared across all source types:

- Left: Sources panel
- Center: Chat panel
- Right: Studio card grid + canvas

The renderer registry determines what renders inside the Studio canvas based on `activeStudioView`.

## Renderer Families

### Family A. Generic summary cards

Views that use metric grid + list + artifact link patterns:

- `samtools`
- `snpeff`
- `liftover`
- `ldblockshow`
- `qqman`
- `qc`
- `vep`
- `coverage`

These are handled by `genericStudioRenderers.tsx` components such as `DirectToolResultCard` and `MetadataTableCard`.

### Family B. Generic preview/table cards

Views that present tabular data with optional search/filter:

- `sumstats`
- `table`

### Family C. Domain custom cards (genomics)

Views with strong interaction, navigation, or domain-specific rendering:

- `candidates` — variant ranking with scoring/triage
- `annotations` — annotation dropdown, search, detail card
- `roh` — ROH segment review
- `symbolic` — symbolic ALT review
- `clinvar` — clinical significance distribution
- `igv` — browser embed (future)

### Family D. Domain custom cards (clinical/imaging)

- `dicom_review` — DICOM metadata, series summary, viewer
- `image_review` — image metadata, EXIF, thumbnail preview
- `fhir_browser` — patient hero, allergies, vitals, medications, labs, care team
- `text_review` — markdown preview with full text
- `cohort_browser` — spreadsheet sheets, schema, missingness

### Family E. Workflow-specific cards

- `plink` — execution form with qc/score modes
- `prs_prep` — build check, harmonization, score-file preview
- `rawqc` — FastQC module review with report actions

## Existing Reusable Primitives

Components extracted into shared modules:

- `MetadataTableCard` — key-value metadata display
- `DirectToolResultCard` — generic metric + warning + artifact card
- `TextMarkdownCard` — rendered markdown with full-text fetch
- `RawQcReviewCard` — FastQC module summaries
- `FhirBrowserCard` — FHIR patient/medication/lab/care team
- `DicomReviewCard` — DICOM metadata and series summary

## Renderer Registry Architecture

The current dispatch flow:

1. `studioRenderers.tsx` — `STUDIO_RENDERER_METADATA` maps renderer keys to requested views
2. `resolveStudioRendererKey()` — resolves payload to a renderer key
3. `buildStudioRendererRegistry()` — builds a component registry
4. `customStudioRenderers.tsx` — domain-specific card implementations
5. `genericStudioRenderers.tsx` — reusable card implementations

Adding a new renderer requires:
1. Add entry to `STUDIO_RENDERER_METADATA`
2. Add component to custom or generic renderers
3. Register in `buildStudioRendererRegistry()`

## Migration Status

### Completed

- Generic renderer registry extracted from `page.tsx`
- Direct tool results use `DirectToolResultCard`
- Text, DICOM, image, FHIR, spreadsheet renderers use dedicated components
- Renderer dispatch is registry-based, not conditional branches

### Remaining

- Some VCF-specific views still rendered inline in `page.tsx`
- Further extraction of shared primitives (metric grid, distribution panel) possible
- IGV viewer card not yet implemented
