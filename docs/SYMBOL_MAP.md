# Symbol Map

- Source boundary: `docs/CONTEXT_BOUNDARIES.json`
- Schema: `symbol_map_v1`
- Scope: `ai_safe_context.code_file_paths`
- Generated on: `2026-03-30`
- Module count: `26`

## Summary

### Packages
- `actions`: 1
- `ai_architecture`: 1
- `ai_boundary`: 1
- `app`: 2
- `audit`: 2
- `config`: 1
- `core`: 1
- `geometry`: 2
- `perception`: 2
- `persistence`: 2
- `planning`: 2
- `policy`: 2
- `recovery`: 2
- `replay`: 1
- `scenarios`: 1
- `semantics`: 3

### Public Class Kinds
- `dataclass`: 44
- `enum`: 12
- `protocol`: 36

### Largest AI-Safe Modules
- `src/universal_visual_os_agent/geometry/models.py`: 229 lines
- `src/universal_visual_os_agent/semantics/models.py`: 148 lines
- `src/universal_visual_os_agent/config/models.py`: 141 lines
- `src/universal_visual_os_agent/actions/models.py`: 133 lines
- `src/universal_visual_os_agent/perception/models.py`: 133 lines
- `src/universal_visual_os_agent/policy/models.py`: 130 lines
- `src/universal_visual_os_agent/ai_architecture/interfaces.py`: 129 lines
- `src/universal_visual_os_agent/semantics/ontology.py`: 118 lines

## Module Skeletons

### `src/universal_visual_os_agent/actions/models.py`
- Purpose: Action intent and result models.
- Public classes: `ActionIntentStatus` (enum), `ActionIntentReasonCode` (enum), `ActionRequirementStatus` (enum), `ActionPrecondition` (dataclass), `ActionTargetValidation` (dataclass), `ActionSafetyGate` (dataclass), `ActionIntent` (dataclass), `ActionResult` (dataclass)
- Public functions: None
- Important data models: `ActionPrecondition`, `ActionTargetValidation`, `ActionSafetyGate`, `ActionIntent`, `ActionResult`
- Important enums: `ActionIntentStatus`, `ActionIntentReasonCode`, `ActionRequirementStatus`
- Important protocols: None
- Internal dependencies: `universal_visual_os_agent.geometry.models`
- Line count: `133`; public symbol count: `8`

### `src/universal_visual_os_agent/ai_architecture/interfaces.py`
- Purpose: Interfaces for shared AI ontology, contracts, and arbitration scaffolding.
- Public classes: `SharedOntologyBinder` (protocol), `PlannerContractBuilder` (protocol), `ResolverContractBuilder` (protocol), `EscalationPolicyDecider` (protocol), `AiArbitrator` (protocol)
- Public functions: None
- Important data models: None
- Important enums: None
- Important protocols: `SharedOntologyBinder`, `PlannerContractBuilder`, `ResolverContractBuilder`, `EscalationPolicyDecider`, `AiArbitrator`
- Internal dependencies: `universal_visual_os_agent.ai_architecture.arbitration`, `universal_visual_os_agent.ai_architecture.contracts`, `universal_visual_os_agent.ai_architecture.ontology`, `universal_visual_os_agent.ai_boundary.models`, `universal_visual_os_agent.semantics.candidate_exposure`, `universal_visual_os_agent.semantics.state`, `universal_visual_os_agent.verification.models`
- Line count: `129`; public symbol count: `5`

### `src/universal_visual_os_agent/ai_boundary/interfaces.py`
- Purpose: Interfaces for structured AI-boundary validation.
- Public classes: `PlannerBoundaryValidator` (protocol), `ResolverBoundaryValidator` (protocol)
- Public functions: None
- Important data models: None
- Important enums: None
- Important protocols: `PlannerBoundaryValidator`, `ResolverBoundaryValidator`
- Internal dependencies: `universal_visual_os_agent.ai_boundary.models`
- Line count: `37`; public symbol count: `2`

### `src/universal_visual_os_agent/app/interfaces.py`
- Purpose: Async-friendly orchestration protocols.
- Public classes: `ObservationProvider` (protocol), `FrameDiffer` (protocol), `SemanticRebuilder` (protocol), `LoopPlanner` (protocol), `TransitionVerifier` (protocol), `RecoveryLoader` (protocol), `RecoveryReconciler` (protocol), `LoopActionExecutor` (protocol)
- Public functions: None
- Important data models: None
- Important enums: None
- Important protocols: `ObservationProvider`, `FrameDiffer`, `SemanticRebuilder`, `LoopPlanner`, `TransitionVerifier`, `RecoveryLoader`, `RecoveryReconciler`, `LoopActionExecutor`
- Internal dependencies: `universal_visual_os_agent.actions.models`, `universal_visual_os_agent.app.models`, `universal_visual_os_agent.config.models`, `universal_visual_os_agent.config.modes`, `universal_visual_os_agent.perception.models`, `universal_visual_os_agent.recovery.models`, `universal_visual_os_agent.semantics.state`, `universal_visual_os_agent.verification.models`
- Line count: `103`; public symbol count: `8`

### `src/universal_visual_os_agent/app/models.py`
- Purpose: Async orchestration models for the main loop skeleton.
- Public classes: `LoopStage` (enum), `LoopStatus` (enum), `FrameDiff` (dataclass), `LoopPlan` (dataclass), `RetryPolicy` (dataclass), `LoopRequest` (dataclass), `LoopResult` (dataclass)
- Public functions: None
- Important data models: `FrameDiff`, `LoopPlan`, `RetryPolicy`, `LoopRequest`, `LoopResult`
- Important enums: `LoopStage`, `LoopStatus`
- Important protocols: None
- Internal dependencies: `universal_visual_os_agent.actions.models`, `universal_visual_os_agent.perception.models`, `universal_visual_os_agent.planning.models`, `universal_visual_os_agent.policy.models`, `universal_visual_os_agent.recovery.models`, `universal_visual_os_agent.semantics.state`, `universal_visual_os_agent.verification.models`
- Line count: `105`; public symbol count: `7`

### `src/universal_visual_os_agent/audit/interfaces.py`
- Purpose: Audit sink interfaces.
- Public classes: `AuditSink` (protocol)
- Public functions: None
- Important data models: None
- Important enums: None
- Important protocols: `AuditSink`
- Internal dependencies: `universal_visual_os_agent.audit.models`
- Line count: `15`; public symbol count: `1`

### `src/universal_visual_os_agent/audit/models.py`
- Purpose: Audit models for observable system behavior.
- Public classes: `AuditEvent` (dataclass)
- Public functions: None
- Important data models: `AuditEvent`
- Important enums: None
- Important protocols: None
- Internal dependencies: None
- Line count: `19`; public symbol count: `1`

### `src/universal_visual_os_agent/config/models.py`
- Purpose: Dataclass-based configuration with safe defaults.
- Public classes: `LoggingConfig` (dataclass), `PersistenceConfig` (dataclass), `ReplayConfig` (dataclass), `RunConfig` (dataclass)
- Public functions: None
- Important data models: `LoggingConfig`, `PersistenceConfig`, `ReplayConfig`, `RunConfig`
- Important enums: None
- Important protocols: None
- Internal dependencies: `universal_visual_os_agent.config.modes`
- Line count: `141`; public symbol count: `4`

### `src/universal_visual_os_agent/core/interfaces.py`
- Purpose: Shared low-level interfaces.
- Public classes: `Clock` (protocol), `EventSink` (protocol)
- Public functions: None
- Important data models: None
- Important enums: None
- Important protocols: `Clock`, `EventSink`
- Internal dependencies: `universal_visual_os_agent.core.events`
- Line count: `23`; public symbol count: `2`

### `src/universal_visual_os_agent/geometry/interfaces.py`
- Purpose: Protocols for future OS-backed screen metrics providers.
- Public classes: `ScreenMetricsProvider` (protocol)
- Public functions: None
- Important data models: None
- Important enums: None
- Important protocols: `ScreenMetricsProvider`
- Internal dependencies: `universal_visual_os_agent.geometry.models`
- Line count: `14`; public symbol count: `1`

### `src/universal_visual_os_agent/geometry/models.py`
- Purpose: Normalized geometry primitives.
- Public classes: `NormalizedPoint` (dataclass), `NormalizedBBox` (dataclass), `ScreenMetrics` (dataclass), `ScreenPoint` (dataclass), `ScreenBBox` (dataclass), `VirtualDesktopMetrics` (dataclass), `ScreenMetricsQueryResult` (dataclass)
- Public functions: None
- Important data models: `NormalizedPoint`, `NormalizedBBox`, `ScreenMetrics`, `ScreenPoint`, `ScreenBBox`, `VirtualDesktopMetrics`, `ScreenMetricsQueryResult`
- Important enums: None
- Important protocols: None
- Internal dependencies: None
- Line count: `229`; public symbol count: `7`

### `src/universal_visual_os_agent/perception/interfaces.py`
- Purpose: Perception provider interfaces.
- Public classes: `CaptureProvider` (protocol)
- Public functions: None
- Important data models: None
- Important enums: None
- Important protocols: `CaptureProvider`
- Internal dependencies: `universal_visual_os_agent.perception.models`
- Line count: `14`; public symbol count: `1`

### `src/universal_visual_os_agent/perception/models.py`
- Purpose: Perception model types.
- Public classes: `FramePixelFormat` (enum), `FrameImagePayload` (dataclass), `CapturedFrame` (dataclass), `CaptureResult` (dataclass)
- Public functions: None
- Important data models: `FrameImagePayload`, `CapturedFrame`, `CaptureResult`
- Important enums: `FramePixelFormat`
- Important protocols: None
- Internal dependencies: None
- Line count: `133`; public symbol count: `4`

### `src/universal_visual_os_agent/persistence/interfaces.py`
- Purpose: Repository interfaces for SQLite-backed persistence.
- Public classes: `TaskRepository` (protocol), `CheckpointRepository` (protocol), `AuditEventRepository` (protocol)
- Public functions: None
- Important data models: None
- Important enums: None
- Important protocols: `TaskRepository`, `CheckpointRepository`, `AuditEventRepository`
- Internal dependencies: `universal_visual_os_agent.audit.models`, `universal_visual_os_agent.persistence.models`
- Line count: `39`; public symbol count: `3`

### `src/universal_visual_os_agent/persistence/models.py`
- Purpose: SQLite-oriented persistence models.
- Public classes: `TaskRecord` (dataclass), `CheckpointRecord` (dataclass)
- Public functions: None
- Important data models: `TaskRecord`, `CheckpointRecord`
- Important enums: None
- Important protocols: None
- Internal dependencies: None
- Line count: `29`; public symbol count: `2`

### `src/universal_visual_os_agent/planning/interfaces.py`
- Purpose: Planner interfaces.
- Public classes: `Planner` (protocol), `RecoveryPlanner` (protocol)
- Public functions: None
- Important data models: None
- Important enums: None
- Important protocols: `Planner`, `RecoveryPlanner`
- Internal dependencies: `universal_visual_os_agent.planning.models`, `universal_visual_os_agent.recovery.models`
- Line count: `23`; public symbol count: `2`

### `src/universal_visual_os_agent/planning/models.py`
- Purpose: Planner model types.
- Public classes: `PlannerDecision` (dataclass)
- Public functions: None
- Important data models: `PlannerDecision`
- Important enums: None
- Important protocols: None
- Internal dependencies: None
- Line count: `16`; public symbol count: `1`

### `src/universal_visual_os_agent/policy/interfaces.py`
- Purpose: Policy engine and safety hook interfaces.
- Public classes: `ProtectedContextDetector` (protocol), `KillSwitch` (protocol), `PauseController` (protocol), `PolicyEngine` (protocol)
- Public functions: None
- Important data models: None
- Important enums: None
- Important protocols: `ProtectedContextDetector`, `KillSwitch`, `PauseController`, `PolicyEngine`
- Internal dependencies: `universal_visual_os_agent.actions.models`, `universal_visual_os_agent.policy.models`
- Line count: `52`; public symbol count: `4`

### `src/universal_visual_os_agent/policy/models.py`
- Purpose: Policy and safety models for action gating.
- Public classes: `PolicyVerdict` (enum), `ProtectedContextStatus` (enum), `PolicyContextCompleteness` (enum), `PauseStatus` (enum), `PolicyRule` (dataclass), `PolicyRuleSet` (dataclass), `ProtectedContextAssessment` (dataclass), `KillSwitchState` (dataclass), `PauseState` (dataclass), `PolicyEvaluationContext` (dataclass), `PolicyDecision` (dataclass)
- Public functions: None
- Important data models: `PolicyRule`, `PolicyRuleSet`, `ProtectedContextAssessment`, `KillSwitchState`, `PauseState`, `PolicyEvaluationContext`, `PolicyDecision`
- Important enums: `PolicyVerdict`, `ProtectedContextStatus`, `PolicyContextCompleteness`, `PauseStatus`
- Important protocols: None
- Internal dependencies: None
- Line count: `130`; public symbol count: `11`

### `src/universal_visual_os_agent/recovery/interfaces.py`
- Purpose: Recovery loading and reconciliation contracts.
- Public classes: `RecoverySnapshotLoader` (protocol), `StateReconciler` (protocol)
- Public functions: None
- Important data models: None
- Important enums: None
- Important protocols: `RecoverySnapshotLoader`, `StateReconciler`
- Internal dependencies: `universal_visual_os_agent.recovery.models`
- Line count: `26`; public symbol count: `2`

### `src/universal_visual_os_agent/recovery/models.py`
- Purpose: Recovery model types.
- Public classes: `RecoverySnapshot` (dataclass), `ReconciliationResult` (dataclass)
- Public functions: None
- Important data models: `RecoverySnapshot`, `ReconciliationResult`
- Important enums: None
- Important protocols: None
- Internal dependencies: `universal_visual_os_agent.persistence.models`
- Line count: `45`; public symbol count: `2`

### `src/universal_visual_os_agent/replay/models.py`
- Purpose: Replay session and deterministic-mode models.
- Public classes: `DeterministicReplaySettings` (dataclass), `ReplayEntry` (dataclass), `ReplaySession` (dataclass), `ReplayHarnessResult` (dataclass)
- Public functions: None
- Important data models: `DeterministicReplaySettings`, `ReplayEntry`, `ReplaySession`, `ReplayHarnessResult`
- Important enums: None
- Important protocols: None
- Internal dependencies: `universal_visual_os_agent.app.models`, `universal_visual_os_agent.perception.models`, `universal_visual_os_agent.semantics.state`
- Line count: `64`; public symbol count: `4`

### `src/universal_visual_os_agent/scenarios/interfaces.py`
- Purpose: Scenario-definition and scenario-flow interfaces.
- Public classes: `ScenarioDefinitionBuilder` (protocol), `ScenarioRunner` (protocol), `ScenarioActionRunner` (protocol), `ScenarioStateMachine` (protocol)
- Public functions: None
- Important data models: None
- Important enums: None
- Important protocols: `ScenarioDefinitionBuilder`, `ScenarioRunner`, `ScenarioActionRunner`, `ScenarioStateMachine`
- Internal dependencies: `universal_visual_os_agent.config.models`, `universal_visual_os_agent.geometry.models`, `universal_visual_os_agent.policy.models`, `universal_visual_os_agent.scenarios.models`, `universal_visual_os_agent.scenarios.state_machine`, `universal_visual_os_agent.semantics.state`
- Line count: `90`; public symbol count: `4`

### `src/universal_visual_os_agent/semantics/layout.py`
- Purpose: Semantic layout tree models.
- Public classes: `SemanticNode` (dataclass), `SemanticLayoutTree` (dataclass)
- Public functions: None
- Important data models: `SemanticNode`, `SemanticLayoutTree`
- Important enums: None
- Important protocols: None
- Internal dependencies: `universal_visual_os_agent.geometry.models`
- Line count: `61`; public symbol count: `2`

### `src/universal_visual_os_agent/semantics/models.py`
- Purpose: Compatibility exports for semantic models.
- Public classes: None
- Public functions: None
- Important data models: None
- Important enums: None
- Important protocols: None
- Internal dependencies: `universal_visual_os_agent.semantics.building`, `universal_visual_os_agent.semantics.candidate_exposure`, `universal_visual_os_agent.semantics.candidate_generation`, `universal_visual_os_agent.semantics.candidate_scoring`, `universal_visual_os_agent.semantics.interfaces`, `universal_visual_os_agent.semantics.layout`, `universal_visual_os_agent.semantics.layout_region_analysis`, `universal_visual_os_agent.semantics.ocr` + 6 more
- Line count: `148`; public symbol count: `0`

### `src/universal_visual_os_agent/semantics/ontology.py`
- Purpose: Stable candidate-source ontology models for hybrid semantic perception.
- Public classes: `SemanticCandidateSourceType` (enum), `CandidateSelectionRiskLevel` (enum), `CandidateProvenanceRecord` (dataclass), `CandidateOntologyCarrier` (protocol)
- Public functions: `normalize_source_of_truth_priority`, `normalize_provenance`, `candidate_ontology_completeness_status`, `provenance_source_types`
- Important data models: `CandidateProvenanceRecord`
- Important enums: `SemanticCandidateSourceType`, `CandidateSelectionRiskLevel`
- Important protocols: `CandidateOntologyCarrier`
- Internal dependencies: None
- Line count: `118`; public symbol count: `8`
