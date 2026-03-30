# Context Boundaries

- Source inventory: `docs/REPO_INVENTORY.json`
- Inventory schema: `repo_inventory_v1`
- Boundary schema: `context_boundary_v1`
- Generated on: `2026-03-30`

## Boundary Intent

- This artifact defines what should be included, excluded, or reviewed before future AI coding/planning context is assembled.
- It is documentation-only scaffolding for hygiene work and does not change runtime behavior, policy, capture flow, or execution behavior.

## Allowed By Default

### Always-Include Documents
- `AGENTS.md`
- `docs/spec.md`
- `docs/execplan.md`
- `docs/CONTEXT_BOUNDARIES.md`

### AI-Safe Code Context
- These are smaller contract/model/ontology files with `keep` inventory status and lower context noise than the main implementation hotspots.
- `src/universal_visual_os_agent/actions/models.py`
- `src/universal_visual_os_agent/ai_architecture/interfaces.py`
- `src/universal_visual_os_agent/ai_boundary/interfaces.py`
- `src/universal_visual_os_agent/app/interfaces.py`
- `src/universal_visual_os_agent/app/models.py`
- `src/universal_visual_os_agent/audit/interfaces.py`
- `src/universal_visual_os_agent/audit/models.py`
- `src/universal_visual_os_agent/config/models.py`
- `src/universal_visual_os_agent/core/interfaces.py`
- `src/universal_visual_os_agent/geometry/interfaces.py`
- `src/universal_visual_os_agent/geometry/models.py`
- `src/universal_visual_os_agent/perception/interfaces.py`
- `src/universal_visual_os_agent/perception/models.py`
- `src/universal_visual_os_agent/persistence/interfaces.py`
- `src/universal_visual_os_agent/persistence/models.py`
- `src/universal_visual_os_agent/planning/interfaces.py`
- `src/universal_visual_os_agent/planning/models.py`
- `src/universal_visual_os_agent/policy/interfaces.py`
- `src/universal_visual_os_agent/policy/models.py`
- `src/universal_visual_os_agent/recovery/interfaces.py`
- `src/universal_visual_os_agent/recovery/models.py`
- `src/universal_visual_os_agent/replay/models.py`
- `src/universal_visual_os_agent/scenarios/interfaces.py`
- `src/universal_visual_os_agent/semantics/layout.py`
- `src/universal_visual_os_agent/semantics/models.py`
- `src/universal_visual_os_agent/semantics/ontology.py`

## Core Runtime Context

- Treat these areas as production-flow context, but include them task-sliced rather than wholesale.
- `src/universal_visual_os_agent/config/`
- `src/universal_visual_os_agent/geometry/`
- `src/universal_visual_os_agent/perception/`
- `src/universal_visual_os_agent/semantics/`
- `src/universal_visual_os_agent/integrations/windows/`
- `src/universal_visual_os_agent/policy/`
- `src/universal_visual_os_agent/app/`
- `src/universal_visual_os_agent/verification/`
- `src/universal_visual_os_agent/actions/`
- `src/universal_visual_os_agent/scenarios/`

## Excluded By Default

### Diagnostic-Only Runtime Files
- `src/universal_visual_os_agent/integrations/windows/capture_gdi.py`
- `src/universal_visual_os_agent/integrations/windows/capture_printwindow.py`
- `src/universal_visual_os_agent/integrations/windows/dxcam_capture_diagnostic.py`
- `src/universal_visual_os_agent/integrations/windows/foreground_capture_diagnostic.py`

### Archive Candidates
- `.tmp_test_artifacts/**`
- `docs/NEXT_STEPS.md`
- `docs/PROJECT_STATUS.md`

### Test-Only Context
- `tests/**`
- Test-only file count: `40`

### Re-Export Surfaces To Avoid In Default AI Packs
- `src/universal_visual_os_agent/actions/__init__.py`
- `src/universal_visual_os_agent/ai_architecture/__init__.py`
- `src/universal_visual_os_agent/integrations/windows/__init__.py`
- `src/universal_visual_os_agent/persistence/__init__.py`
- `src/universal_visual_os_agent/scenarios/__init__.py`
- `src/universal_visual_os_agent/semantics/__init__.py`
- `src/universal_visual_os_agent/verification/__init__.py`

## Review Required Before Inclusion

### Cycle-Risk Review Areas
- `src/universal_visual_os_agent/actions/interfaces.py`
- `src/universal_visual_os_agent/actions/safe_click.py`
- `src/universal_visual_os_agent/semantics/interfaces.py`
- `src/universal_visual_os_agent/semantics/ocr.py`
- `src/universal_visual_os_agent/verification/explanations.py`
- `src/universal_visual_os_agent/verification/goal_oriented.py`
- `src/universal_visual_os_agent/verification/interfaces.py`
- `src/universal_visual_os_agent/verification/models.py`

### Split Candidates
- `src/universal_visual_os_agent/actions/dry_run.py`
- `src/universal_visual_os_agent/actions/scaffolding.py`
- `src/universal_visual_os_agent/ai_architecture/arbitration.py`
- `src/universal_visual_os_agent/ai_architecture/contracts.py`
- `src/universal_visual_os_agent/ai_architecture/ontology.py`
- `src/universal_visual_os_agent/ai_boundary/models.py`
- `src/universal_visual_os_agent/ai_boundary/validation.py`
- `src/universal_visual_os_agent/app/orchestration.py`
- `src/universal_visual_os_agent/integrations/windows/capture.py`
- `src/universal_visual_os_agent/integrations/windows/capture_backends.py`
- `src/universal_visual_os_agent/integrations/windows/capture_dxcam.py`
- `src/universal_visual_os_agent/integrations/windows/capture_models.py`
- `src/universal_visual_os_agent/integrations/windows/screen_metrics.py`
- `src/universal_visual_os_agent/scenarios/action_flow.py`
- `src/universal_visual_os_agent/scenarios/definition.py`
- `src/universal_visual_os_agent/scenarios/loop.py`
- `src/universal_visual_os_agent/scenarios/models.py`
- `src/universal_visual_os_agent/scenarios/state_machine.py`
- `src/universal_visual_os_agent/semantics/building.py`
- `src/universal_visual_os_agent/semantics/candidate_exposure.py`
- `src/universal_visual_os_agent/semantics/candidate_generation.py`
- `src/universal_visual_os_agent/semantics/candidate_scoring.py`
- `src/universal_visual_os_agent/semantics/layout_region_analysis.py`
- `src/universal_visual_os_agent/semantics/ocr_enrichment.py`
- `src/universal_visual_os_agent/semantics/ocr_rapidocr.py`
- `src/universal_visual_os_agent/semantics/preparation.py`
- `src/universal_visual_os_agent/semantics/semantic_delta.py`
- `src/universal_visual_os_agent/semantics/semantic_layout_enrichment.py`
- `src/universal_visual_os_agent/semantics/state.py`
- `src/universal_visual_os_agent/testing/repo_inventory.py`

### Hygiene-Specific Review Artifacts
- `docs/REPO_INVENTORY.md`
- `docs/REPO_INVENTORY.json`

## Legacy Review Context

- No explicit legacy-review files are currently flagged by inventory heuristics.

## High-Noise Summary

### Cycle Risk By Domain
- `actions`: 2
- `semantics`: 2
- `verification`: 4

### Split Candidates By Domain
- `actions`: 2
- `ai_architecture`: 3
- `ai_boundary`: 2
- `app`: 1
- `integrations`: 5
- `scenarios`: 5
- `semantics`: 11
- `testing`: 1

### Archive Candidates By Domain
- `.tmp_test_artifacts`: 115
- `docs`: 2

## Recommended Follow-Up Order

1. Archive or purge temporary .tmp_test_artifacts noise from the repository surface.
2. Isolate the actions/semantics/verification cycle-risk cluster before larger feature work.
3. Split oversized semantics, scenarios, runtime capture, and AI-contract modules into narrower files.
4. Trim package __init__ re-export surfaces from default AI context packs and open concrete submodules instead.
