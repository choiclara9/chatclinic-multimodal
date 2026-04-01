# ChatClinic Developer Manual

This manual is for collaborators who want to add tools, source types, or Studio renderers to ChatClinic.

## 1. Core Concepts

ChatClinic separates four concepts:

### Source types

Source types are auto-detected on upload. Each source type has a bootstrap workflow, chat endpoint, and Studio renderer.

Current source types:
- `vcf` — variant interpretation
- `raw_qc` — FASTQ/BAM/SAM sequencing QC
- `summary_stats` — GWAS summary statistics
- `text` — plain text / markdown notes
- `spreadsheet` — Excel workbooks
- `dicom` — DICOM medical images
- `image` — PNG/JPG/TIFF images
- `fhir` — FHIR clinical bundles

### `@toolname`

`@toolname` runs one deterministic tool.

Examples:
- `@liftover`
- `@samtools`
- `@plink`
- `@qqman`
- `@snpeff`
- `@ldblockshow`
- `@prs_prep`

### `$studio`

`$studio` tells chat to explain the current Studio state rather than answer as a general assistant.

Other grounding prefixes: `$current analysis`, `$current card`, `$grounded`.

### `@help`

`@help` shows the full tool guide, loaded from `SKILL.md`.

## 2. Repository Areas You Will Touch

### Skill policy

- `skills/chatgenome-orchestrator/SKILL.md`

Defines: trigger policy, tool recommendation, interpretation rules, grounded-chat behavior, welcome message, help message.

### Source registry

- `app/services/source_registry.py`

Defines: source type detection (suffixes, file kinds), bootstrap mapping, upload labels, initial tools, chat response kinds, Studio renderers.

### Bootstrap manifests

- `skills/chatgenome-orchestrator/bootstrap/<source_type>_bootstrap.json`

Defines: ordered tool steps that run on source upload.

### Tool plugins

- `plugins/<tool_folder>/`

Each plugin typically contains:

```text
plugins/<tool_folder>/
  tool.json       — metadata, aliases, help, workflow_binding
  logic.py        — Python implementation (entrypoint preferred)
  run.py          — optional CLI wrapper (--input/--output)
```

### Backend runtime

Main files:
- `app/main.py` — API endpoints
- `app/models.py` — request/response schemas
- `app/services/chat.py` — chat dispatch
- `app/services/workflows.py` — workflow execution
- `app/services/source_bootstrap.py` — bootstrap launcher

### Frontend

Main files:
- `webapp/app/page.tsx` — state, handlers, chat, Studio
- `webapp/app/components/studioRenderers.tsx` — renderer registry
- `webapp/app/components/customStudioRenderers.tsx` — custom card components
- `webapp/app/components/genericStudioRenderers.tsx` — generic card components

## 3. How To Add A New Tool

### Step 1. Decide the user-facing alias

Pick the command users should type (e.g. `@clinvar`, `@vep`).

### Step 2. Create the plugin folder

```text
plugins/<tool_folder>/
  tool.json
  logic.py
```

### Step 3. Write `tool.json`

Minimal:

```json
{
  "name": "example_execution_tool",
  "description": "What the tool does.",
  "task": "example-task",
  "modality": "genomics",
  "approval_required": false,
  "source": "plugin",
  "aliases": ["example"]
}
```

For `@tool help` support, add a `help` section:

```json
{
  "help": {
    "summary": "Short user-facing summary.",
    "options": [
      { "name": "mode", "type": "string", "default": "run", "description": "Execution mode." }
    ],
    "examples": ["@example help", "@example", "@example mode=run"]
  }
}
```

For workflow integration, add a `workflow_binding` section:

```json
{
  "workflow_binding": {
    "source_type": "vcf",
    "input_map": { "vcf_path": "$source_vcf_path", "facts": "$facts" },
    "result_path": "annotations",
    "transform": "variant_annotation_list",
    "used_tools_label": "annotation_tool"
  }
}
```

### Step 4. Write `logic.py`

Preferred pattern — export a callable entrypoint:

```python
def run(payload: dict) -> dict:
    # deterministic work
    return {"tool": "example_tool", "summary": "Done.", "artifacts": {}}
```

### Step 5. Wire the backend

Typical places:
- `app/main.py` — add endpoint if needed
- `app/models.py` — add request/response models
- `app/services/chat.py` — tool routing (often automatic via registry)

### Step 6. Add Studio rendering

Update renderer registry in `webapp/app/components/studioRenderers.tsx` and add card component in `customStudioRenderers.tsx` or `genericStudioRenderers.tsx`.

### Step 7. Update SKILL.md

Add tool to the help message and orchestrator rules.

## 4. How To Add A New Source Type

### Step 1. Register in source registry

Add entry to `app/services/source_registry.py` with suffixes, labels, bootstrap type, initial tools, and Studio renderer.

### Step 2. Create bootstrap manifest

Add `skills/chatgenome-orchestrator/bootstrap/<source_type>_bootstrap.json`.

### Step 3. Add backend endpoint

Add upload endpoint in `app/main.py` and chat endpoint for the source type.

### Step 4. Add response models

Add source response and chat response models in `app/models.py`.

### Step 5. Add frontend support

In `webapp/app/page.tsx`:
- Add file detection function
- Add state and handlers
- Wire into multimodal payload

### Step 6. Add Studio renderer

Add renderer component and register it.

## 5. Contributor Checklist

Before opening a PR:

1. Validate Python syntax:
```bash
python3 -m py_compile app/main.py app/models.py app/services/*.py
```

2. Build the frontend:
```bash
cd webapp && npm run build
```

3. Test `@tool help` if you added a direct tool.
4. Confirm Studio card appears if the tool produces a review artifact.
5. Update `SKILL.md` help message if adding user-facing tools.
