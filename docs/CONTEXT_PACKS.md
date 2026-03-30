# Context Packs

- Schema: `context_packs_v1`
- Generated on: `2026-03-31`
- Source artifacts: `docs/REPO_INVENTORY.json`, `docs/CONTEXT_BOUNDARIES.json`, `docs/SYMBOL_MAP.json`

## Shared Defaults

### Always-Include Documents
- `AGENTS.md`
- `docs/README.md`
- `docs/spec.md`
- `docs/execplan.md`
- `docs/CONTEXT_BOUNDARIES.md`
- `docs/SYMBOL_MAP.md`

### Shared Exclusions
- `.tmp_test_artifacts/**`
- `tests/**`
- `docs/archive/**`

## Packs

### `capture_runtime_pack`
- Purpose: Compact capture/runtime context anchored in normalized geometry, perception contracts, and safe capture configuration.
- Included modules (5): `src/universal_visual_os_agent/config/models.py`, `src/universal_visual_os_agent/geometry/interfaces.py`, `src/universal_visual_os_agent/geometry/models.py`, `src/universal_visual_os_agent/perception/interfaces.py`, `src/universal_visual_os_agent/perception/models.py`
- Review add-ons (6): `src/universal_visual_os_agent/integrations/windows/capture_desktop_duplication.py`, `src/universal_visual_os_agent/integrations/windows/capture.py`, `src/universal_visual_os_agent/integrations/windows/capture_backends.py`, `src/universal_visual_os_agent/integrations/windows/capture_dxcam.py`, `src/universal_visual_os_agent/integrations/windows/capture_models.py`, `src/universal_visual_os_agent/integrations/windows/screen_metrics.py`
- Excluded modules: `src/universal_visual_os_agent/integrations/windows/capture_gdi.py`, `src/universal_visual_os_agent/integrations/windows/capture_printwindow.py`, `src/universal_visual_os_agent/integrations/windows/dxcam_capture_diagnostic.py`, `src/universal_visual_os_agent/integrations/windows/foreground_capture_diagnostic.py`, `src/universal_visual_os_agent/integrations/windows/click.py`
- Core models/interfaces: `LoggingConfig`, `PersistenceConfig`, `ReplayConfig`, `RunConfig`, `ScreenMetricsProvider`, `NormalizedPoint`, `NormalizedBBox`, `ScreenMetrics`, `ScreenPoint`, `ScreenBBox`, `VirtualDesktopMetrics`, `ScreenMetricsQueryResult`, `CaptureProvider`, `FrameImagePayload`, `CapturedFrame`, `CaptureResult`, `FramePixelFormat`
- Safety rules / invariants:
  1. Capture context stays observe-only and never implies OS input or action execution.
  2. Normalized geometry and DPI-aware metrics remain the coordinate source of truth.
  3. Diagnostic/compatibility capture paths stay out of default production-oriented reasoning.
- Common failure modes:
  1. Primary DXcam/DXGI path unavailable in the current environment.
  2. DPI or virtual-desktop metrics drift causing coordinate mismatch.
  3. Diagnostic fallback files accidentally treated as production defaults.

### `semantics_pack`
- Purpose: Compact semantic-understanding context around layout, provenance ontology, and semantic compatibility surfaces.
- Included modules (4): `src/universal_visual_os_agent/geometry/models.py`, `src/universal_visual_os_agent/semantics/layout.py`, `src/universal_visual_os_agent/semantics/models.py`, `src/universal_visual_os_agent/semantics/ontology.py`
- Review add-ons (12): `src/universal_visual_os_agent/semantics/building.py`, `src/universal_visual_os_agent/semantics/candidate_generation.py`, `src/universal_visual_os_agent/semantics/candidate_scoring.py`, `src/universal_visual_os_agent/semantics/candidate_exposure.py`, `src/universal_visual_os_agent/semantics/layout_region_analysis.py`, `src/universal_visual_os_agent/semantics/ocr.py`, `src/universal_visual_os_agent/semantics/ocr_enrichment.py`, `src/universal_visual_os_agent/semantics/ocr_rapidocr.py`, `src/universal_visual_os_agent/semantics/preparation.py`, `src/universal_visual_os_agent/semantics/semantic_delta.py`, `src/universal_visual_os_agent/semantics/semantic_layout_enrichment.py`, `src/universal_visual_os_agent/semantics/state.py`
- Excluded modules: `src/universal_visual_os_agent/semantics/__init__.py`, `src/universal_visual_os_agent/integrations/windows/capture_gdi.py`, `src/universal_visual_os_agent/integrations/windows/capture_printwindow.py`
- Core models/interfaces: `NormalizedPoint`, `NormalizedBBox`, `ScreenMetrics`, `ScreenPoint`, `ScreenBBox`, `VirtualDesktopMetrics`, `ScreenMetricsQueryResult`, `SemanticNode`, `SemanticLayoutTree`, `CandidateProvenanceRecord`, `SemanticCandidateSourceType`, `CandidateSelectionRiskLevel`, `CandidateOntologyCarrier`, `normalize_source_of_truth_priority`, `normalize_provenance`, `candidate_ontology_completeness_status`, `provenance_source_types`
- Safety rules / invariants:
  1. Semantic candidates remain observe-only and non-actionable by default.
  2. Source/provenance metadata stays explicit for hybrid perception work.
  3. Normalized geometry remains the spatial boundary across OCR/layout/candidate layers.
- Common failure modes:
  1. Compatibility-export modules add noise without defining primary symbols.
  2. Semantic implementation modules are oversized and need task-scoped inclusion.
  3. Cycle-risk around semantics interfaces and OCR can blur boundaries.

### `verification_pack`
- Purpose: Compact verification/recovery context centered on loop contracts, replay/recovery models, and delta-driven verification add-ons.
- Included modules (5): `src/universal_visual_os_agent/app/interfaces.py`, `src/universal_visual_os_agent/app/models.py`, `src/universal_visual_os_agent/recovery/interfaces.py`, `src/universal_visual_os_agent/recovery/models.py`, `src/universal_visual_os_agent/replay/models.py`
- Review add-ons (5): `src/universal_visual_os_agent/verification/interfaces.py`, `src/universal_visual_os_agent/verification/models.py`, `src/universal_visual_os_agent/verification/goal_oriented.py`, `src/universal_visual_os_agent/verification/explanations.py`, `src/universal_visual_os_agent/semantics/semantic_delta.py`
- Excluded modules: `src/universal_visual_os_agent/verification/__init__.py`, `src/universal_visual_os_agent/actions/safe_click.py`, `src/universal_visual_os_agent/integrations/windows/click.py`
- Core models/interfaces: `ObservationProvider`, `FrameDiffer`, `SemanticRebuilder`, `LoopPlanner`, `TransitionVerifier`, `RecoveryLoader`, `RecoveryReconciler`, `LoopActionExecutor`, `FrameDiff`, `LoopPlan`, `RetryPolicy`, `LoopRequest`, `LoopResult`, `LoopStage`, `LoopStatus`, `RecoverySnapshotLoader`, `StateReconciler`, `RecoverySnapshot`, `ReconciliationResult`, `DeterministicReplaySettings`, `ReplayEntry`, `ReplaySession`, `ReplayHarnessResult`
- Safety rules / invariants:
  1. Verification remains read-only and should never imply action success without observed evidence.
  2. Unknown and partial-input outcomes must stay explicit rather than guessed.
  3. Replay and dry-run validation are preferred over live behavior checks.
- Common failure modes:
  1. Missing before/after state leaves verification in unknown or partial status.
  2. Verification cluster has cycle-risk and should be included deliberately.
  3. Explanation taxonomy can drift if verification and delta layers are edited separately.

### `action_pack`
- Purpose: Compact action/safety context around intent models, policy gates, and boundary validation contracts.
- Included modules (4): `src/universal_visual_os_agent/actions/models.py`, `src/universal_visual_os_agent/ai_boundary/interfaces.py`, `src/universal_visual_os_agent/policy/interfaces.py`, `src/universal_visual_os_agent/policy/models.py`
- Review add-ons (6): `src/universal_visual_os_agent/actions/interfaces.py`, `src/universal_visual_os_agent/actions/scaffolding.py`, `src/universal_visual_os_agent/actions/dry_run.py`, `src/universal_visual_os_agent/actions/safe_click.py`, `src/universal_visual_os_agent/ai_boundary/models.py`, `src/universal_visual_os_agent/ai_boundary/validation.py`
- Excluded modules: `src/universal_visual_os_agent/actions/__init__.py`, `src/universal_visual_os_agent/integrations/windows/click.py`, `src/universal_visual_os_agent/integrations/windows/capture_gdi.py`, `src/universal_visual_os_agent/integrations/windows/capture_printwindow.py`
- Core models/interfaces: `ActionPrecondition`, `ActionTargetValidation`, `ActionSafetyGate`, `ActionIntent`, `ActionResult`, `ActionIntentStatus`, `ActionIntentReasonCode`, `ActionRequirementStatus`, `PlannerBoundaryValidator`, `ResolverBoundaryValidator`, `ProtectedContextDetector`, `KillSwitch`, `PauseController`, `PolicyEngine`, `PolicyRule`, `PolicyRuleSet`, `ProtectedContextAssessment`, `KillSwitchState`, `PauseState`, `PolicyEvaluationContext`, `PolicyDecision`, `PolicyVerdict`, `ProtectedContextStatus`, `PolicyContextCompleteness`, `PauseStatus`
- Safety rules / invariants:
  1. Action context is non-executing by default and real actions stay behind explicit config flags.
  2. Protected-context detection, kill switch, and pause/resume hooks remain mandatory.
  3. Structured boundary validation must reject malformed AI outputs before any OS-facing path.
- Common failure modes:
  1. Low-confidence or incomplete candidates remain blocked or dry-run-only.
  2. Policy context can be incomplete even when action models look valid.
  3. Actions interfaces and safe-click implementation sit in a cycle-risk cluster.

### `scenario_fsm_pack`
- Purpose: Compact scenario/FSM context around loop models, scenario interfaces, and explicit state-machine boundaries.
- Included modules (4): `src/universal_visual_os_agent/app/interfaces.py`, `src/universal_visual_os_agent/app/models.py`, `src/universal_visual_os_agent/recovery/models.py`, `src/universal_visual_os_agent/scenarios/interfaces.py`
- Review add-ons (5): `src/universal_visual_os_agent/scenarios/definition.py`, `src/universal_visual_os_agent/scenarios/models.py`, `src/universal_visual_os_agent/scenarios/state_machine.py`, `src/universal_visual_os_agent/scenarios/loop.py`, `src/universal_visual_os_agent/scenarios/action_flow.py`
- Excluded modules: `src/universal_visual_os_agent/scenarios/__init__.py`, `src/universal_visual_os_agent/actions/safe_click.py`, `src/universal_visual_os_agent/integrations/windows/click.py`
- Core models/interfaces: `ObservationProvider`, `FrameDiffer`, `SemanticRebuilder`, `LoopPlanner`, `TransitionVerifier`, `RecoveryLoader`, `RecoveryReconciler`, `LoopActionExecutor`, `FrameDiff`, `LoopPlan`, `RetryPolicy`, `LoopRequest`, `LoopResult`, `LoopStage`, `LoopStatus`, `RecoverySnapshot`, `ReconciliationResult`, `ScenarioDefinitionBuilder`, `ScenarioRunner`, `ScenarioActionRunner`, `ScenarioStateMachine`
- Safety rules / invariants:
  1. Scenario flow remains non-executing by default and must keep dry-run and real-click states separate.
  2. State transitions should stay explicit, instrumented, and recoverable.
  3. Verification still governs terminal success rather than implicit execution assumptions.
- Common failure modes:
  1. Oversized scenario modules make it easy to over-pull unrelated flow logic.
  2. Before/after snapshot handling can leave terminal state ambiguous.
  3. Scenario flow can accidentally absorb action-execution concerns if packs are not kept narrow.

### `ai_architecture_pack`
- Purpose: Compact AI-architecture context around typed planner/resolver contracts, ontology binding, and boundary-validation interfaces.
- Included modules (4): `src/universal_visual_os_agent/actions/models.py`, `src/universal_visual_os_agent/ai_architecture/interfaces.py`, `src/universal_visual_os_agent/ai_boundary/interfaces.py`, `src/universal_visual_os_agent/semantics/ontology.py`
- Review add-ons (5): `src/universal_visual_os_agent/ai_architecture/contracts.py`, `src/universal_visual_os_agent/ai_architecture/arbitration.py`, `src/universal_visual_os_agent/ai_architecture/ontology.py`, `src/universal_visual_os_agent/ai_boundary/models.py`, `src/universal_visual_os_agent/ai_boundary/validation.py`
- Excluded modules: `src/universal_visual_os_agent/ai_architecture/__init__.py`, `src/universal_visual_os_agent/integrations/windows/click.py`, `src/universal_visual_os_agent/integrations/windows/capture_gdi.py`, `src/universal_visual_os_agent/integrations/windows/capture_printwindow.py`
- Core models/interfaces: `ActionPrecondition`, `ActionTargetValidation`, `ActionSafetyGate`, `ActionIntent`, `ActionResult`, `ActionIntentStatus`, `ActionIntentReasonCode`, `ActionRequirementStatus`, `SharedOntologyBinder`, `PlannerContractBuilder`, `ResolverContractBuilder`, `EscalationPolicyDecider`, `AiArbitrator`, `PlannerBoundaryValidator`, `ResolverBoundaryValidator`, `CandidateProvenanceRecord`, `SemanticCandidateSourceType`, `CandidateSelectionRiskLevel`, `CandidateOntologyCarrier`, `normalize_source_of_truth_priority`, `normalize_provenance`, `candidate_ontology_completeness_status`, `provenance_source_types`
- Safety rules / invariants:
  1. Planner/resolver work stays typed and structured; no free-text AI output path is assumed.
  2. Candidate references, coordinates, labels, and confidence must be validated before downstream use.
  3. This pack is architecture-only and must remain non-executing until future phases explicitly broaden it.
- Common failure modes:
  1. Ontology drift between deterministic pipeline and AI-facing contracts.
  2. Boundary validation modules are large enough to over-expand context if opened wholesale.
  3. Invalid candidate IDs, malformed confidence, or unsupported targets should be rejected at the boundary.
