# Production Prune Plan

- Schema: `production_prune_plan_v1`
- Generated on: `2026-03-31`
- Source artifacts:
  - `docs/REPO_INVENTORY.json`
  - `docs/CONTEXT_BOUNDARIES.json`
  - `docs/SYMBOL_MAP.json`
  - `docs/CONTEXT_PACKS.json`

## Purpose

- This artifact plans what should and should not ship in a future production package.
- It is planning-only scaffolding. It does not delete files, change runtime behavior, or broaden execution.
- The intent is to make later release pruning allowlist-driven, safety-first, and reviewable.

## Planning Summary

- Inventory total files: `306`
- Production-critical files: `35`
- Supporting files: `71`
- Non-production files: `200`
- Diagnostic runtime files: `4`
- Test-only files: `44`
- Archive-candidate files: `132`
- Cycle-risk files: `8`
- Split-candidate files: `34`

## Recommended Release Profiles

### `production_base_observe_runtime`

- Default shipping profile.
- Includes the current Windows-first, observe-only, dry-run-first runtime.
- Excludes diagnostics, tests, archive/docs payloads, and optional live-input scaffolding.

### `production_runtime_support`

- Optional ship-adjacent profile for feature-gated support modules that are not required for the minimal observe-only runtime.
- Intended for controlled environments, internal builds, and staged rollout bundles.
- Includes safety boundary, replay, planner/resolver scaffolding, and narrow safe-click support only when explicitly justified.

### `diagnostic_bundle`

- Non-default profile for support/debug usage.
- Contains compatibility and diagnostic capture paths plus their helpers.
- Must not be the default production package.

### `dev_full_repo`

- Full repository checkout for development, CI, tests, and hygiene work.
- Not a production packaging target.

## Grouping Recommendations

### Production Include Set

- Keep these in the future default shipping package:
  - `src/universal_visual_os_agent/__init__.py`
  - `src/universal_visual_os_agent/config/**`
  - `src/universal_visual_os_agent/geometry/**`
  - `src/universal_visual_os_agent/perception/**`
  - `src/universal_visual_os_agent/persistence/**`
  - `src/universal_visual_os_agent/policy/**`
  - `src/universal_visual_os_agent/recovery/**`
  - `src/universal_visual_os_agent/semantics/**`
  - `src/universal_visual_os_agent/verification/**`
  - `src/universal_visual_os_agent/app/**`
  - `src/universal_visual_os_agent/scenarios/**`
  - `src/universal_visual_os_agent/actions/models.py`
  - `src/universal_visual_os_agent/actions/interfaces.py`
  - `src/universal_visual_os_agent/actions/scaffolding.py`
  - `src/universal_visual_os_agent/actions/scaffolding_models.py`
  - `src/universal_visual_os_agent/actions/dry_run.py`
  - `src/universal_visual_os_agent/actions/dry_run_models.py`
  - `src/universal_visual_os_agent/actions/tool_boundary.py`
  - `src/universal_visual_os_agent/actions/tool_boundary_models.py`
  - `src/universal_visual_os_agent/integrations/windows/capture.py`
  - `src/universal_visual_os_agent/integrations/windows/capture_backends.py`
  - `src/universal_visual_os_agent/integrations/windows/capture_models.py`
  - `src/universal_visual_os_agent/integrations/windows/capture_dxcam.py`
  - `src/universal_visual_os_agent/integrations/windows/capture_desktop_duplication.py`
  - `src/universal_visual_os_agent/integrations/windows/screen_metrics.py`
- Rationale:
  - These files represent the current production-oriented observe-only runtime, semantic pipeline, verification/recovery path, and dry-run boundary layers.
  - They align with the current spec: event-driven, modular, observe-only by default, safety-first, and testable without real OS action.

### Runtime Support Set

- Keep these available for controlled/internal builds, but do not require them in the minimal default production package:
  - `src/universal_visual_os_agent/actions/safe_click.py`
  - `src/universal_visual_os_agent/integrations/windows/click.py`
  - `src/universal_visual_os_agent/ai_boundary/**`
  - `src/universal_visual_os_agent/ai_architecture/**`
  - `src/universal_visual_os_agent/planning/**`
  - `src/universal_visual_os_agent/replay/**`
- Rationale:
  - These areas are important for staged productization, structured AI boundary hardening, replay validation, and the existing narrow safe-click prototype.
  - They are not required for the smallest observe-only production runtime and should remain feature-gated or optional until backend integrations are real.

### Diagnostic-Only Set

- Keep these in the repo and optionally in a separate diagnostic bundle, but exclude them from the default production package:
  - `src/universal_visual_os_agent/integrations/windows/capture_gdi.py`
  - `src/universal_visual_os_agent/integrations/windows/capture_printwindow.py`
  - `src/universal_visual_os_agent/integrations/windows/dxcam_capture_diagnostic.py`
  - `src/universal_visual_os_agent/integrations/windows/foreground_capture_diagnostic.py`
- Rationale:
  - Revision 1 made DXcam/DXGI-oriented capture the production full-desktop path.
  - GDI/BitBlt and PrintWindow are explicitly diagnostic/compatibility-oriented and should not silently ship as production defaults.

### Dev/Test-Only Set

- Exclude these from any production package:
  - `tests/**`
  - `.tmp_test_artifacts/**`
  - `src/universal_visual_os_agent/testing/**`
  - `.github/**`
  - `requirements.in`
  - `requirements.txt`
- Rationale:
  - These are for CI, replay validation, local scaffolding, or temporary artifacts.
  - They add size and noise without being part of the runtime product.

### Archive / Docs-Only Set

- Keep these in the repository, but do not ship them inside the runtime package:
  - `docs/**`
  - `docs/archive/**`
  - `AGENTS.md`
  - `README.md`
- Rationale:
  - These are source-of-truth, operator, and hygiene documents.
  - They matter for engineering workflow, but not for the runtime artifact itself.

### Exclude-From-Production Set

- Explicitly exclude these from the default production package:
  - All diagnostic-only files
  - All dev/test-only files
  - All archive/docs-only files
  - `src/universal_visual_os_agent/memory/**`
- Rationale:
  - `memory/` is still placeholder-level and not part of the active production runtime path.
  - Diagnostics, tests, and docs should remain in source control but not in the release payload.

## Production-Only Candidate Set

- Recommended allowlist basis for a minimal shipping package:
  - `src/universal_visual_os_agent/__init__.py`
  - `src/universal_visual_os_agent/config/`
  - `src/universal_visual_os_agent/geometry/`
  - `src/universal_visual_os_agent/perception/`
  - `src/universal_visual_os_agent/persistence/`
  - `src/universal_visual_os_agent/policy/`
  - `src/universal_visual_os_agent/recovery/`
  - `src/universal_visual_os_agent/semantics/`
  - `src/universal_visual_os_agent/verification/`
  - `src/universal_visual_os_agent/app/`
  - `src/universal_visual_os_agent/scenarios/`
  - `src/universal_visual_os_agent/actions/models.py`
  - `src/universal_visual_os_agent/actions/interfaces.py`
  - `src/universal_visual_os_agent/actions/scaffolding.py`
  - `src/universal_visual_os_agent/actions/scaffolding_models.py`
  - `src/universal_visual_os_agent/actions/dry_run.py`
  - `src/universal_visual_os_agent/actions/dry_run_models.py`
  - `src/universal_visual_os_agent/actions/tool_boundary.py`
  - `src/universal_visual_os_agent/actions/tool_boundary_models.py`
  - `src/universal_visual_os_agent/integrations/windows/capture.py`
  - `src/universal_visual_os_agent/integrations/windows/capture_backends.py`
  - `src/universal_visual_os_agent/integrations/windows/capture_models.py`
  - `src/universal_visual_os_agent/integrations/windows/capture_dxcam.py`
  - `src/universal_visual_os_agent/integrations/windows/capture_desktop_duplication.py`
  - `src/universal_visual_os_agent/integrations/windows/screen_metrics.py`
- Planning note:
  - Package `__init__.py` files should remain where required for import stability even when they are excluded from default AI context packs.
  - Context-hygiene exclusions are not the same as packaging exclusions.

## Include / Exclude Rationale Notes

### Keep Thin Compatibility Surfaces When They Preserve Public Imports

- `__init__.py` facades and compatibility modules can remain in a production package if they are needed for stable imports.
- They should still stay thin and lazy where possible.

### Prefer Allowlist Packaging Over Denylist Packaging

- Build the future production package from an explicit allowlist.
- Do not rely on "ship everything except tests" logic.
- This reduces the chance of accidentally shipping diagnostics, temporary artifacts, or future experimental modules.

### Separate Shipping Runtime from Repo Retention

- Some files should remain in the repository for debugging, CI, or staged rollout even if they are excluded from the default package.
- The prune plan is about packaging shape, not about deleting repo history or engineering assets.

## Release Smoke Checklist Draft

1. Confirm the package contents are allowlist-based and exclude `tests/**`, `docs/**`, `.tmp_test_artifacts/**`, and diagnostic capture files.
2. Run `python -m compileall src tests`.
3. Run the default suite: `python -m pytest -q tests -p no:cacheprovider`.
4. Run an import smoke for the intended production profile.
5. Confirm production capture policy still rejects diagnostic-only GDI/PrintWindow fallback in production mode.
6. Confirm the semantic pipeline still produces non-actionable candidates by default.
7. Confirm dry-run and tool-boundary paths remain non-executing by default.
8. If the optional safe-action extension is present, confirm it remains explicitly gated and disabled by default.
9. Confirm no archive/docs payload is present in the built runtime artifact.
10. Confirm no temporary SQLite artifacts or local scratch files are present in the release payload.

## Packaging / Profile Considerations

- Recommended future packaging profiles:
  - `base_observe_runtime`
  - `runtime_support`
  - `diagnostic_bundle`
  - `dev_full_repo`
- Recommended defaults:
  - Ship `base_observe_runtime` by default.
  - Keep `runtime_support` explicit and review-gated.
  - Keep `diagnostic_bundle` separate from the default install path.
- Recommended release bias:
  - Prefer smaller, safety-first artifacts over "ship the whole repo."
  - Only promote support/diagnostic modules into the default runtime package when there is a concrete operational need.

## Follow-Up Order

1. Define a concrete packaging manifest for `base_observe_runtime`.
2. Define an optional manifest for `runtime_support`.
3. Keep diagnostic capture files in a separate non-default bundle.
4. Remove `.tmp_test_artifacts/**` from any future build context.
5. Revisit `memory/**` only after it becomes part of a real runtime path.
