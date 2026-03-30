"""Structured AI-boundary contracts for future planner and resolver integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Protocol, Self

from universal_visual_os_agent.config.models import RunConfig
from universal_visual_os_agent.geometry.models import NormalizedPoint
from universal_visual_os_agent.semantics.candidate_exposure import CandidateExposureView
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot
from universal_visual_os_agent.verification.models import SemanticTransitionExpectation


STRUCTURED_AI_BOUNDARY_SCHEMA_VERSION = "structured_ai_boundary_v1"


class AiContractSource(StrEnum):
    """Supported structured AI contract sources."""

    cloud_planner = "cloud_planner"
    local_visual_resolver = "local_visual_resolver"


class AiBoundaryStatus(StrEnum):
    """Validation status for structured AI contracts."""

    accepted = "accepted"
    rejected = "rejected"


class AiBoundaryRejectionCode(StrEnum):
    """Stable rejection codes for invalid AI-boundary payloads."""

    missing_input = "missing_input"
    partial_input = "partial_input"
    invalid_candidate_reference = "invalid_candidate_reference"
    unsupported_target_label = "unsupported_target_label"
    malformed_confidence = "malformed_confidence"
    malformed_coordinate = "malformed_coordinate"
    out_of_bounds_coordinate = "out_of_bounds_coordinate"
    candidate_target_mismatch = "candidate_target_mismatch"
    invalid_action_eligibility = "invalid_action_eligibility"
    impossible_state_transition = "impossible_state_transition"


class AiSuggestedActionType(StrEnum):
    """Supported structured action suggestions at the AI boundary."""

    observe_only = "observe_only"
    candidate_select = "candidate_select"


class AiTargetLabel(StrEnum):
    """Supported target labels that downstream resolver output may reference."""

    candidate_center = "candidate_center"
    candidate_point = "candidate_point"


class AiActionEligibility(StrEnum):
    """Validated execution eligibility derived from current safety state."""

    observe_only = "observe_only"
    dry_run_only = "dry_run_only"
    live_execution_eligible = "live_execution_eligible"


class ProtectedContextAssessmentLike(Protocol):
    """Structural contract for protected-context snapshots."""

    status: object
    reason: str


class KillSwitchStateLike(Protocol):
    """Structural contract for kill-switch snapshots."""

    engaged: bool
    reason: str | None


class PauseStateLike(Protocol):
    """Structural contract for pause-state snapshots."""

    status: object
    reason: str | None

    @property
    def paused(self) -> bool:
        """Whether action processing is paused."""


class PolicyEvaluationContextLike(Protocol):
    """Structural contract for policy-evaluation context snapshots."""

    live_execution_requested: bool
    live_execution_enabled: bool


@dataclass(slots=True, frozen=True, kw_only=True)
class _DefaultProtectedContextAssessment:
    status: str = "unknown"
    reason: str = "No protected-context signal provided."


@dataclass(slots=True, frozen=True, kw_only=True)
class _DefaultKillSwitchState:
    engaged: bool = False
    reason: str | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class _DefaultPauseState:
    status: str = "running"
    reason: str | None = None

    @property
    def paused(self) -> bool:
        return self.status == "paused"


@dataclass(slots=True, frozen=True, kw_only=True)
class _DefaultPolicyEvaluationContext:
    live_execution_requested: bool = False
    live_execution_enabled: bool = False


def _default_protected_context_assessment() -> ProtectedContextAssessmentLike:
    return _DefaultProtectedContextAssessment()


def _default_kill_switch_state() -> KillSwitchStateLike:
    return _DefaultKillSwitchState()


def _default_pause_state() -> PauseStateLike:
    return _DefaultPauseState()


def _default_policy_context() -> PolicyEvaluationContextLike:
    return _DefaultPolicyEvaluationContext()


@dataclass(slots=True, frozen=True, kw_only=True)
class AiBoundaryValidationContext:
    """Inputs used to validate structured planner and resolver outputs."""

    run_config: RunConfig = field(default_factory=RunConfig)
    snapshot: SemanticStateSnapshot | None = None
    exposure_view: CandidateExposureView | None = None
    protected_context_assessment: ProtectedContextAssessmentLike = field(
        default_factory=_default_protected_context_assessment
    )
    kill_switch_state: KillSwitchStateLike = field(default_factory=_default_kill_switch_state)
    pause_state: PauseStateLike = field(default_factory=_default_pause_state)
    policy_context: PolicyEvaluationContextLike = field(default_factory=_default_policy_context)
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(slots=True, frozen=True, kw_only=True)
class PlannerActionSuggestionContract:
    """Strict structured planner action suggestion before boundary validation."""

    action_type: str
    confidence: object
    candidate_id: str | None = None
    candidate_label: str | None = None
    target_label: str | None = None
    dry_run_only: bool = True
    live_execution_requested: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.action_type:
            raise ValueError("action_type must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerContract:
    """Strict structured cloud-planner output before boundary validation."""

    decision_id: str
    summary: str
    action_suggestion: PlannerActionSuggestionContract | None = None
    expected_transition: SemanticTransitionExpectation | None = None
    schema_version: str = STRUCTURED_AI_BOUNDARY_SCHEMA_VERSION
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.decision_id:
            raise ValueError("decision_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.schema_version:
            raise ValueError("schema_version must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ResolverPointContract:
    """Structured resolver-point payload before normalized coordinate validation."""

    x: object
    y: object


@dataclass(slots=True, frozen=True, kw_only=True)
class LocalVisualResolverContract:
    """Strict structured local-visual-resolver output before boundary validation."""

    resolution_id: str
    summary: str
    action_type: str
    candidate_id: str
    target_label: str
    point: ResolverPointContract
    confidence: object
    candidate_label: str | None = None
    schema_version: str = STRUCTURED_AI_BOUNDARY_SCHEMA_VERSION
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.resolution_id:
            raise ValueError("resolution_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.action_type:
            raise ValueError("action_type must not be empty.")
        if not self.candidate_id:
            raise ValueError("candidate_id must not be empty.")
        if not self.target_label:
            raise ValueError("target_label must not be empty.")
        if not self.schema_version:
            raise ValueError("schema_version must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ValidatedPlannerActionSuggestion:
    """Validated planner action suggestion safe for downstream orchestration use."""

    action_type: AiSuggestedActionType
    confidence: float
    action_eligibility: AiActionEligibility
    candidate_id: str | None = None
    candidate_label: str | None = None
    target_label: AiTargetLabel | None = None
    dry_run_only: bool = True
    live_execution_requested: bool = False
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive.")
        if not self.dry_run_only:
            raise ValueError("Validated planner action suggestions must remain dry-run only.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Validated planner action suggestions must remain safety-first and non-executing.")
        if (
            self.action_eligibility is AiActionEligibility.observe_only
            and self.action_type is not AiSuggestedActionType.observe_only
        ):
            raise ValueError("observe_only eligibility requires an observe_only action type.")
        if (
            self.action_eligibility is AiActionEligibility.live_execution_eligible
            and not self.live_execution_requested
        ):
            raise ValueError("live_execution_eligible suggestions must request live execution.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ValidatedCloudPlannerOutput:
    """Validated planner output accepted at the AI boundary."""

    decision_id: str
    summary: str
    action_suggestion: ValidatedPlannerActionSuggestion | None = None
    expected_transition: SemanticTransitionExpectation | None = None
    schema_version: str = STRUCTURED_AI_BOUNDARY_SCHEMA_VERSION
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.decision_id:
            raise ValueError("decision_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.schema_version:
            raise ValueError("schema_version must not be empty.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Validated planner outputs must remain safety-first and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ValidatedLocalVisualResolverOutput:
    """Validated local visual resolver output accepted at the AI boundary."""

    resolution_id: str
    summary: str
    action_type: AiSuggestedActionType
    candidate_id: str
    target_label: AiTargetLabel
    point: NormalizedPoint
    confidence: float
    candidate_label: str | None = None
    schema_version: str = STRUCTURED_AI_BOUNDARY_SCHEMA_VERSION
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.resolution_id:
            raise ValueError("resolution_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.candidate_id:
            raise ValueError("candidate_id must not be empty.")
        if not self.schema_version:
            raise ValueError("schema_version must not be empty.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Validated resolver outputs must remain safety-first and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class AiBoundaryRejection:
    """Structured boundary rejection for invalid planner or resolver output."""

    source: AiContractSource
    code: AiBoundaryRejectionCode
    summary: str
    field_path: str | None = None
    related_candidate_id: str | None = None
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Boundary rejections must remain safety-first and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class PlannerContractValidationResult:
    """Validation result for a structured planner contract."""

    validator_name: str
    status: AiBoundaryStatus
    source_contract: CloudPlannerContract
    validated_output: ValidatedCloudPlannerOutput | None = None
    rejections: tuple[AiBoundaryRejection, ...] = ()
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.validator_name:
            raise ValueError("validator_name must not be empty.")
        if self.status is AiBoundaryStatus.accepted:
            if self.validated_output is None:
                raise ValueError("Accepted planner validation must include validated_output.")
            if self.rejections or self.error_code is not None or self.error_message is not None:
                raise ValueError("Accepted planner validation must not include rejection or error details.")
            return
        if self.validated_output is not None:
            raise ValueError("Rejected planner validation must not include validated_output.")
        if not self.rejections and self.error_code is None:
            raise ValueError("Rejected planner validation must include rejections or error details.")
        if self.error_code is None and self.error_message is not None:
            raise ValueError("error_message requires error_code.")

    @property
    def success(self) -> bool:
        return self.status is AiBoundaryStatus.accepted

    @classmethod
    def accepted(
        cls,
        *,
        validator_name: str,
        source_contract: CloudPlannerContract,
        validated_output: ValidatedCloudPlannerOutput,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            validator_name=validator_name,
            status=AiBoundaryStatus.accepted,
            source_contract=source_contract,
            validated_output=validated_output,
            details={} if details is None else details,
        )

    @classmethod
    def rejected(
        cls,
        *,
        validator_name: str,
        source_contract: CloudPlannerContract,
        rejections: tuple[AiBoundaryRejection, ...],
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            validator_name=validator_name,
            status=AiBoundaryStatus.rejected,
            source_contract=source_contract,
            rejections=rejections,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        validator_name: str,
        source_contract: CloudPlannerContract,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            validator_name=validator_name,
            status=AiBoundaryStatus.rejected,
            source_contract=source_contract,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class ResolverContractValidationResult:
    """Validation result for a structured resolver contract."""

    validator_name: str
    status: AiBoundaryStatus
    source_contract: LocalVisualResolverContract
    validated_output: ValidatedLocalVisualResolverOutput | None = None
    rejections: tuple[AiBoundaryRejection, ...] = ()
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.validator_name:
            raise ValueError("validator_name must not be empty.")
        if self.status is AiBoundaryStatus.accepted:
            if self.validated_output is None:
                raise ValueError("Accepted resolver validation must include validated_output.")
            if self.rejections or self.error_code is not None or self.error_message is not None:
                raise ValueError("Accepted resolver validation must not include rejection or error details.")
            return
        if self.validated_output is not None:
            raise ValueError("Rejected resolver validation must not include validated_output.")
        if not self.rejections and self.error_code is None:
            raise ValueError("Rejected resolver validation must include rejections or error details.")
        if self.error_code is None and self.error_message is not None:
            raise ValueError("error_message requires error_code.")

    @property
    def success(self) -> bool:
        return self.status is AiBoundaryStatus.accepted

    @classmethod
    def accepted(
        cls,
        *,
        validator_name: str,
        source_contract: LocalVisualResolverContract,
        validated_output: ValidatedLocalVisualResolverOutput,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            validator_name=validator_name,
            status=AiBoundaryStatus.accepted,
            source_contract=source_contract,
            validated_output=validated_output,
            details={} if details is None else details,
        )

    @classmethod
    def rejected(
        cls,
        *,
        validator_name: str,
        source_contract: LocalVisualResolverContract,
        rejections: tuple[AiBoundaryRejection, ...],
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            validator_name=validator_name,
            status=AiBoundaryStatus.rejected,
            source_contract=source_contract,
            rejections=rejections,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        validator_name: str,
        source_contract: LocalVisualResolverContract,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            validator_name=validator_name,
            status=AiBoundaryStatus.rejected,
            source_contract=source_contract,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )
