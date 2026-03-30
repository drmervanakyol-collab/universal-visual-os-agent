"""Safe observe-only scaffolding for future action intents."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Mapping, Self

from universal_visual_os_agent.actions.models import (
    ActionIntent,
    ActionIntentReasonCode,
    ActionIntentStatus,
    ActionPrecondition,
    ActionRequirementStatus,
    ActionSafetyGate,
    ActionTargetValidation,
)
from universal_visual_os_agent.geometry.models import NormalizedBBox, NormalizedPoint
from universal_visual_os_agent.semantics.candidate_exposure import (
    CandidateExposureView,
    ExposedCandidate,
)
from universal_visual_os_agent.semantics.state import (
    SemanticCandidate,
    SemanticLayoutRegion,
    SemanticStateSnapshot,
)


@dataclass(slots=True, frozen=True, kw_only=True)
class ActionIntentScaffoldView:
    """Stable downstream-facing view of scaffolded action intents."""

    snapshot_id: str
    intents: tuple[ActionIntent, ...]
    total_exposed_candidate_count: int
    scaffolded_intent_count: int
    incomplete_intent_count: int
    blocked_intent_count: int
    signal_status: str = "absent"
    sort_order: str = "candidate_rank_then_candidate_id"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            raise ValueError("snapshot_id must not be empty.")
        if self.total_exposed_candidate_count < 0:
            raise ValueError("total_exposed_candidate_count must not be negative.")
        if self.scaffolded_intent_count < 0:
            raise ValueError("scaffolded_intent_count must not be negative.")
        if self.incomplete_intent_count < 0:
            raise ValueError("incomplete_intent_count must not be negative.")
        if self.blocked_intent_count < 0:
            raise ValueError("blocked_intent_count must not be negative.")
        if self.total_exposed_candidate_count != len(self.intents):
            raise ValueError("total_exposed_candidate_count must match len(intents).")
        if (
            self.scaffolded_intent_count
            + self.incomplete_intent_count
            + self.blocked_intent_count
            != len(self.intents)
        ):
            raise ValueError("Intent status counts must match len(intents).")
        if self.signal_status not in {"available", "partial", "absent"}:
            raise ValueError("signal_status must be available, partial, or absent.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ActionIntentScaffoldingResult:
    """Structured result for observe-only action-intent scaffolding."""

    scaffolder_name: str
    success: bool
    source_snapshot: SemanticStateSnapshot | None = None
    exposure_view: CandidateExposureView | None = None
    scaffold_view: ActionIntentScaffoldView | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scaffolder_name:
            raise ValueError("scaffolder_name must not be empty.")
        if self.success and (
            self.source_snapshot is None or self.exposure_view is None or self.scaffold_view is None
        ):
            raise ValueError("Successful action scaffolding must include source_snapshot, exposure_view, and scaffold_view.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed action scaffolding must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful action scaffolding must not include error details.")
        if not self.success and self.scaffold_view is not None:
            raise ValueError("Failed action scaffolding must not include scaffold_view.")

    @classmethod
    def ok(
        cls,
        *,
        scaffolder_name: str,
        source_snapshot: SemanticStateSnapshot,
        exposure_view: CandidateExposureView,
        scaffold_view: ActionIntentScaffoldView,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            scaffolder_name=scaffolder_name,
            success=True,
            source_snapshot=source_snapshot,
            exposure_view=exposure_view,
            scaffold_view=scaffold_view,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        scaffolder_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            scaffolder_name=scaffolder_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class _ScaffoldArtifacts:
    intents: tuple[ActionIntent, ...]
    missing_snapshot_candidate_ids: tuple[str, ...] = ()
    missing_layout_region_ids: tuple[str, ...] = ()
    unsafe_candidate_ids: tuple[str, ...] = ()
    incomplete_candidate_ids: tuple[str, ...] = ()
    upstream_partial_input: bool = False

    @property
    def signal_status(self) -> str:
        if (
            self.missing_snapshot_candidate_ids
            or self.missing_layout_region_ids
            or self.unsafe_candidate_ids
            or self.incomplete_candidate_ids
            or self.upstream_partial_input
        ):
            return "partial"
        if self.intents:
            return "available"
        return "absent"


class ObserveOnlyActionIntentScaffolder:
    """Scaffold safe, non-executing action intents from exposed candidates."""

    scaffolder_name = "ObserveOnlyActionIntentScaffolder"

    def scaffold(
        self,
        snapshot: SemanticStateSnapshot,
        *,
        exposure_view: CandidateExposureView,
    ) -> ActionIntentScaffoldingResult:
        if snapshot.metadata.get("candidate_scoring") is not True:
            return ActionIntentScaffoldingResult.failure(
                scaffolder_name=self.scaffolder_name,
                error_code="candidate_scoring_unavailable",
                error_message="Action-intent scaffolding requires candidate scoring output.",
            )
        if exposure_view.snapshot_id != snapshot.snapshot_id:
            return ActionIntentScaffoldingResult.failure(
                scaffolder_name=self.scaffolder_name,
                error_code="candidate_exposure_snapshot_mismatch",
                error_message="Action-intent scaffolding requires an exposure view from the same snapshot.",
            )
        if (
            exposure_view.metadata.get("observe_only") is not True
            or exposure_view.metadata.get("analysis_only") is not True
            or exposure_view.metadata.get("non_actionable") is not True
        ):
            return ActionIntentScaffoldingResult.failure(
                scaffolder_name=self.scaffolder_name,
                error_code="candidate_exposure_unavailable",
                error_message="Action-intent scaffolding requires an observe-only candidate exposure view.",
            )

        try:
            artifacts = self._build_intents(snapshot, exposure_view=exposure_view)
            status_counts = Counter(intent.status.value for intent in artifacts.intents)
            scaffold_view = ActionIntentScaffoldView(
                snapshot_id=snapshot.snapshot_id,
                intents=artifacts.intents,
                total_exposed_candidate_count=exposure_view.exposed_candidate_count,
                scaffolded_intent_count=status_counts.get(ActionIntentStatus.scaffolded.value, 0),
                incomplete_intent_count=status_counts.get(ActionIntentStatus.incomplete.value, 0),
                blocked_intent_count=status_counts.get(ActionIntentStatus.blocked.value, 0),
                signal_status=artifacts.signal_status,
                metadata={
                    "observe_only": True,
                    "analysis_only": True,
                    "non_executing": True,
                    "dry_run_only": True,
                    "sorted_intent_ids": tuple(intent.intent_id for intent in artifacts.intents),
                    "intent_ids_by_candidate_id": tuple(
                        (intent.candidate_id, intent.intent_id) for intent in artifacts.intents
                    ),
                    "upstream_signal_status": exposure_view.signal_status,
                    "source_exposed_candidate_ids": tuple(
                        candidate.candidate_id for candidate in exposure_view.candidates
                    ),
                    "filtered_out_candidate_ids": exposure_view.filtered_out_candidate_ids,
                    "missing_snapshot_candidate_ids": artifacts.missing_snapshot_candidate_ids,
                    "missing_layout_region_ids": artifacts.missing_layout_region_ids,
                    "unsafe_candidate_ids": artifacts.unsafe_candidate_ids,
                    "incomplete_candidate_ids": artifacts.incomplete_candidate_ids,
                    "upstream_partial_input": artifacts.upstream_partial_input,
                },
            )
        except Exception as exc:  # noqa: BLE001 - scaffolding must remain failure-safe
            return ActionIntentScaffoldingResult.failure(
                scaffolder_name=self.scaffolder_name,
                error_code="action_intent_scaffolding_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return ActionIntentScaffoldingResult.ok(
            scaffolder_name=self.scaffolder_name,
            source_snapshot=snapshot,
            exposure_view=exposure_view,
            scaffold_view=scaffold_view,
            details={
                "intent_count": len(artifacts.intents),
                "signal_status": artifacts.signal_status,
            },
        )

    def _build_intents(
        self,
        snapshot: SemanticStateSnapshot,
        *,
        exposure_view: CandidateExposureView,
    ) -> _ScaffoldArtifacts:
        layout_regions_by_id = {region.region_id: region for region in snapshot.layout_regions}
        missing_snapshot_candidate_ids: list[str] = []
        missing_layout_region_ids: list[str] = []
        unsafe_candidate_ids: list[str] = []
        incomplete_candidate_ids: list[str] = []
        intents: list[ActionIntent] = []

        for candidate in exposure_view.candidates:
            snapshot_candidate = snapshot.get_candidate(candidate.candidate_id)
            source_layout_region = _lookup_layout_region(layout_regions_by_id, candidate.source_layout_region_id)

            if snapshot_candidate is None:
                missing_snapshot_candidate_ids.append(candidate.candidate_id)
            if candidate.source_layout_region_id is not None and source_layout_region is None:
                missing_layout_region_ids.append(candidate.candidate_id)
            if _candidate_is_unsafe(candidate):
                unsafe_candidate_ids.append(candidate.candidate_id)
            if _candidate_is_incomplete(candidate, snapshot_candidate=snapshot_candidate, source_layout_region=source_layout_region):
                incomplete_candidate_ids.append(candidate.candidate_id)

            intents.append(
                self._build_intent(
                    candidate,
                    snapshot_id=snapshot.snapshot_id,
                    snapshot_candidate=snapshot_candidate,
                    source_layout_region=source_layout_region,
                )
            )

        return _ScaffoldArtifacts(
            intents=tuple(intents),
            missing_snapshot_candidate_ids=tuple(sorted(set(missing_snapshot_candidate_ids))),
            missing_layout_region_ids=tuple(sorted(set(missing_layout_region_ids))),
            unsafe_candidate_ids=tuple(sorted(set(unsafe_candidate_ids))),
            incomplete_candidate_ids=tuple(sorted(set(incomplete_candidate_ids))),
            upstream_partial_input=exposure_view.signal_status == "partial",
        )

    def _build_intent(
        self,
        candidate: ExposedCandidate,
        *,
        snapshot_id: str,
        snapshot_candidate: SemanticCandidate | None,
        source_layout_region: SemanticLayoutRegion | None,
    ) -> ActionIntent:
        unsafe_candidate = _candidate_is_unsafe(candidate)
        incomplete_candidate = _candidate_is_incomplete(
            candidate,
            snapshot_candidate=snapshot_candidate,
            source_layout_region=source_layout_region,
        )
        if unsafe_candidate:
            status = ActionIntentStatus.blocked
            reason_code = ActionIntentReasonCode.safety_gating_required
            reason = "Safety requirements blocked this intent from any execution path."
        elif incomplete_candidate:
            status = ActionIntentStatus.incomplete
            reason_code = ActionIntentReasonCode.incomplete_candidate_metadata
            reason = "Candidate or semantic metadata was incomplete, so the intent remains scaffold-only."
        else:
            status = ActionIntentStatus.scaffolded
            reason_code = ActionIntentReasonCode.scaffold_only
            reason = "Intent scaffolded from observe-only candidate data; execution remains disabled."

        preconditions = _build_preconditions(candidate, snapshot_candidate=snapshot_candidate)
        target_validations = _build_target_validations(
            candidate,
            snapshot_candidate=snapshot_candidate,
            source_layout_region=source_layout_region,
        )
        safety_gates = _build_safety_gates(candidate, unsafe_candidate=unsafe_candidate)
        target_point = None if snapshot_candidate is None else _center_point(snapshot_candidate.bounds)

        return ActionIntent(
            action_type="candidate_select",
            target=target_point,
            status=status,
            reason_code=reason_code,
            reason=reason,
            candidate_id=candidate.candidate_id,
            candidate_label=candidate.label,
            candidate_rank=candidate.rank,
            candidate_score=candidate.score,
            precondition_requirements=preconditions,
            target_validation_requirements=target_validations,
            safety_gating_requirements=safety_gates,
            dry_run_only=True,
            executable=False,
            observe_only_source=True,
            metadata={
                **dict(candidate.metadata),
                "action_intent_scaffolded": True,
                "action_intent_scaffolder_name": self.scaffolder_name,
                "intent_status": status.value,
                "intent_reason_code": reason_code.value,
                "intent_reason": reason,
                "source_snapshot_id": snapshot_id,
                "source_candidate_id": candidate.candidate_id,
                "source_layout_region_id": candidate.source_layout_region_id,
                "source_text_region_id": candidate.source_text_region_id,
                "source_text_block_id": candidate.source_text_block_id,
                "observe_only": True,
                "analysis_only": True,
                "non_executing": True,
                "dry_run_only": True,
                "live_execution_allowed": False,
                "future_execution_requires_explicit_enablement": True,
                "precondition_ids": tuple(
                    requirement.requirement_id for requirement in preconditions
                ),
                "target_validation_ids": tuple(
                    validation.validation_id for validation in target_validations
                ),
                "safety_gate_ids": tuple(
                    gate.gate_id for gate in safety_gates
                ),
            },
        )


def _build_preconditions(
    candidate: ExposedCandidate,
    *,
    snapshot_candidate: SemanticCandidate | None,
) -> tuple[ActionPrecondition, ...]:
    return (
        ActionPrecondition(
            requirement_id="candidate_visible",
            summary="Candidate must remain visible in the observed state.",
            status=(
                ActionRequirementStatus.satisfied
                if candidate.visible
                else ActionRequirementStatus.blocked
            ),
            metadata={"candidate_id": candidate.candidate_id},
        ),
        ActionPrecondition(
            requirement_id="candidate_score_available",
            summary="Candidate score must remain available for future dry-run ranking.",
            status=(
                ActionRequirementStatus.satisfied
                if candidate.score is not None
                else ActionRequirementStatus.blocked
            ),
            metadata={"candidate_id": candidate.candidate_id, "candidate_score": candidate.score},
        ),
        ActionPrecondition(
            requirement_id="snapshot_candidate_present",
            summary="Candidate must still be present in the semantic snapshot.",
            status=(
                ActionRequirementStatus.satisfied
                if snapshot_candidate is not None
                else ActionRequirementStatus.blocked
            ),
            metadata={"candidate_id": candidate.candidate_id},
        ),
    )


def _build_target_validations(
    candidate: ExposedCandidate,
    *,
    snapshot_candidate: SemanticCandidate | None,
    source_layout_region: SemanticLayoutRegion | None,
) -> tuple[ActionTargetValidation, ...]:
    return (
        ActionTargetValidation(
            validation_id="candidate_id_consistency",
            summary="Candidate identifier must match a semantic candidate in the current snapshot.",
            status=(
                ActionRequirementStatus.satisfied
                if snapshot_candidate is not None
                else ActionRequirementStatus.blocked
            ),
            metadata={"candidate_id": candidate.candidate_id},
        ),
        ActionTargetValidation(
            validation_id="source_layout_region_consistency",
            summary="Source layout region must remain present for future target validation.",
            status=(
                ActionRequirementStatus.satisfied
                if candidate.source_layout_region_id is not None and source_layout_region is not None
                else ActionRequirementStatus.blocked
            ),
            metadata={"source_layout_region_id": candidate.source_layout_region_id},
        ),
        ActionTargetValidation(
            validation_id="candidate_completeness",
            summary="Exposed candidate must remain complete enough for safe target validation.",
            status=(
                ActionRequirementStatus.satisfied
                if candidate.completeness_status == "available"
                else ActionRequirementStatus.blocked
            ),
            metadata={"completeness_status": candidate.completeness_status},
        ),
    )


def _build_safety_gates(
    candidate: ExposedCandidate,
    *,
    unsafe_candidate: bool,
) -> tuple[ActionSafetyGate, ...]:
    return (
        ActionSafetyGate(
            gate_id="observe_only_origin_confirmed",
            summary="Intent source must remain observe-only and non-actionable.",
            status=(
                ActionRequirementStatus.satisfied
                if candidate.observe_only and candidate.non_actionable and not unsafe_candidate
                else ActionRequirementStatus.blocked
            ),
            metadata={"candidate_id": candidate.candidate_id},
        ),
        ActionSafetyGate(
            gate_id="dry_run_only_enforced",
            summary="Any future action handling must remain dry-run only in Phase 5A.",
            status=ActionRequirementStatus.satisfied,
            metadata={"dry_run_only": True},
        ),
        ActionSafetyGate(
            gate_id="explicit_execution_enablement_required",
            summary="Any execution path requires explicit later-phase enablement outside this scaffold.",
            status=ActionRequirementStatus.pending,
            metadata={"live_execution_allowed": False},
        ),
    )


def _lookup_layout_region(
    layout_regions_by_id: Mapping[str, SemanticLayoutRegion],
    region_id: str | None,
) -> SemanticLayoutRegion | None:
    if region_id is None:
        return None
    return layout_regions_by_id.get(region_id)


def _candidate_is_unsafe(candidate: ExposedCandidate) -> bool:
    return (
        candidate.enabled
        or candidate.actionable
        or not candidate.observe_only
        or not candidate.non_actionable
    )


def _candidate_is_incomplete(
    candidate: ExposedCandidate,
    *,
    snapshot_candidate: SemanticCandidate | None,
    source_layout_region: SemanticLayoutRegion | None,
) -> bool:
    if snapshot_candidate is None:
        return True
    if candidate.completeness_status != "available":
        return True
    if candidate.score is None:
        return True
    if candidate.source_layout_region_id is None or source_layout_region is None:
        return True
    return False


def _center_point(bounds: NormalizedBBox) -> NormalizedPoint:
    return NormalizedPoint(
        x=bounds.left + (bounds.width / 2.0),
        y=bounds.top + (bounds.height / 2.0),
    )
