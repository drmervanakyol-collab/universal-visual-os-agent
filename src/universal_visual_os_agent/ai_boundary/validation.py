"""Observe-only validation for structured AI planner and resolver contracts."""

from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime, time
from enum import Enum, StrEnum
from typing import Mapping

from universal_visual_os_agent.ai_boundary.models import (
    AiActionEligibility,
    AiBoundaryRejection,
    AiBoundaryRejectionCode,
    AiBoundaryValidationContext,
    AiContractSource,
    AiSuggestedActionType,
    AiTargetLabel,
    CloudPlannerContract,
    LocalVisualResolverContract,
    PlannerActionSuggestionContract,
    PlannerContractValidationResult,
    ResolverContractValidationResult,
    ResolverPointContract,
    ValidatedCloudPlannerOutput,
    ValidatedLocalVisualResolverOutput,
    ValidatedPlannerActionSuggestion,
)
from universal_visual_os_agent.config import AgentMode
from universal_visual_os_agent.geometry.models import NormalizedBBox, NormalizedPoint
from universal_visual_os_agent.semantics.semantic_delta import SemanticDeltaCategory
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot
from universal_visual_os_agent.verification.models import (
    ExpectedSemanticChange,
    ExpectedSemanticOutcome,
    SemanticTransitionExpectation,
)


class ObserveOnlyAiBoundaryValidator:
    """Validate structured AI outputs before they can reach downstream runtime paths."""

    validator_name = "ObserveOnlyAiBoundaryValidator"

    def validate_planner_contract(
        self,
        contract: CloudPlannerContract,
        *,
        context: AiBoundaryValidationContext,
    ) -> PlannerContractValidationResult:
        try:
            rejections: list[AiBoundaryRejection] = []
            validated_action: ValidatedPlannerActionSuggestion | None = None

            if contract.action_suggestion is not None:
                validated_action, action_rejections = self._validate_planner_action_suggestion(
                    contract.action_suggestion,
                    context=context,
                )
                rejections.extend(action_rejections)

            rejections.extend(
                self._validate_expected_transition(
                    contract.expected_transition,
                    snapshot=context.snapshot,
                )
            )
            if rejections:
                return PlannerContractValidationResult.rejected(
                    validator_name=self.validator_name,
                    source_contract=contract,
                    rejections=tuple(rejections),
                    details={
                        "rejection_count": len(rejections),
                        "rejection_codes": tuple(rejection.code.value for rejection in rejections),
                    },
                )

            validated_output = ValidatedCloudPlannerOutput(
                decision_id=contract.decision_id,
                summary=contract.summary,
                action_suggestion=validated_action,
                expected_transition=contract.expected_transition,
                schema_version=contract.schema_version,
                observe_only=True,
                read_only=True,
                non_executing=True,
                metadata={
                    **dict(contract.metadata),
                    "ai_boundary_validated": True,
                    "ai_boundary_validator": self.validator_name,
                    "ai_contract_source": AiContractSource.cloud_planner.value,
                    "action_suggestion_present": validated_action is not None,
                    "has_expected_transition": contract.expected_transition is not None,
                    "snapshot_id": None if context.snapshot is None else context.snapshot.snapshot_id,
                },
            )
        except Exception as exc:  # noqa: BLE001 - boundary must remain rejection-safe
            return PlannerContractValidationResult.failure(
                validator_name=self.validator_name,
                source_contract=contract,
                error_code="planner_contract_validation_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return PlannerContractValidationResult.accepted(
            validator_name=self.validator_name,
            source_contract=contract,
            validated_output=validated_output,
            details={
                "action_eligibility": (
                    None
                    if validated_action is None
                    else validated_action.action_eligibility.value
                ),
                "validated_candidate_id": (
                    None if validated_action is None else validated_action.candidate_id
                ),
            },
        )

    def validate_resolver_contract(
        self,
        contract: LocalVisualResolverContract,
        *,
        context: AiBoundaryValidationContext,
    ) -> ResolverContractValidationResult:
        try:
            rejections: list[AiBoundaryRejection] = []

            action_type = self._coerce_action_type(
                contract.action_type,
                source=AiContractSource.local_visual_resolver,
                field_path="action_type",
                rejections=rejections,
            )
            confidence = self._coerce_confidence(
                contract.confidence,
                source=AiContractSource.local_visual_resolver,
                field_path="confidence",
                rejections=rejections,
            )
            target_label = self._coerce_target_label(
                contract.target_label,
                source=AiContractSource.local_visual_resolver,
                field_path="target_label",
                rejections=rejections,
            )
            point = self._coerce_point(
                contract.point,
                source=AiContractSource.local_visual_resolver,
                field_path="point",
                rejections=rejections,
            )
            snapshot_candidate, exposed_candidate, candidate_rejections = self._resolve_candidate_reference(
                contract.candidate_id,
                contract.candidate_label,
                source=AiContractSource.local_visual_resolver,
                field_path="candidate_id",
                context=context,
            )
            rejections.extend(candidate_rejections)
            if snapshot_candidate is not None and point is not None and not _point_in_bounds(
                point,
                snapshot_candidate.bounds,
            ):
                rejections.append(
                    self._rejection(
                        source=AiContractSource.local_visual_resolver,
                        code=AiBoundaryRejectionCode.candidate_target_mismatch,
                        summary=(
                            f"Resolved point for candidate '{contract.candidate_id}' must remain inside "
                            "the candidate bounds."
                        ),
                        field_path="point",
                        related_candidate_id=contract.candidate_id,
                    )
                )

            if action_type is not None and action_type is not AiSuggestedActionType.candidate_select:
                rejections.append(
                    self._rejection(
                        source=AiContractSource.local_visual_resolver,
                        code=AiBoundaryRejectionCode.invalid_action_eligibility,
                        summary=(
                            f"Resolver output does not support action type '{contract.action_type}'."
                        ),
                        field_path="action_type",
                    )
                )

            if rejections:
                return ResolverContractValidationResult.rejected(
                    validator_name=self.validator_name,
                    source_contract=contract,
                    rejections=tuple(rejections),
                    details={
                        "rejection_count": len(rejections),
                        "rejection_codes": tuple(rejection.code.value for rejection in rejections),
                    },
                )

            assert action_type is not None
            assert target_label is not None
            assert confidence is not None
            assert point is not None
            validated_output = ValidatedLocalVisualResolverOutput(
                resolution_id=contract.resolution_id,
                summary=contract.summary,
                action_type=action_type,
                candidate_id=contract.candidate_id,
                candidate_label=None if snapshot_candidate is None else snapshot_candidate.label,
                target_label=target_label,
                point=point,
                confidence=confidence,
                schema_version=contract.schema_version,
                observe_only=True,
                read_only=True,
                non_executing=True,
                metadata={
                    **dict(contract.metadata),
                    "ai_boundary_validated": True,
                    "ai_boundary_validator": self.validator_name,
                    "ai_contract_source": AiContractSource.local_visual_resolver.value,
                    "snapshot_id": None if context.snapshot is None else context.snapshot.snapshot_id,
                    "candidate_exposed": exposed_candidate is not None,
                },
            )
        except Exception as exc:  # noqa: BLE001 - boundary must remain rejection-safe
            return ResolverContractValidationResult.failure(
                validator_name=self.validator_name,
                source_contract=contract,
                error_code="resolver_contract_validation_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return ResolverContractValidationResult.accepted(
            validator_name=self.validator_name,
            source_contract=contract,
            validated_output=validated_output,
            details={
                "validated_candidate_id": contract.candidate_id,
                "validated_target_label": target_label.value,
            },
        )

    def _validate_planner_action_suggestion(
        self,
        suggestion: PlannerActionSuggestionContract,
        *,
        context: AiBoundaryValidationContext,
    ) -> tuple[ValidatedPlannerActionSuggestion | None, tuple[AiBoundaryRejection, ...]]:
        rejections: list[AiBoundaryRejection] = []

        action_type = self._coerce_action_type(
            suggestion.action_type,
            source=AiContractSource.cloud_planner,
            field_path="action_suggestion.action_type",
            rejections=rejections,
        )
        confidence = self._coerce_confidence(
            suggestion.confidence,
            source=AiContractSource.cloud_planner,
            field_path="action_suggestion.confidence",
            rejections=rejections,
        )
        target_label: AiTargetLabel | None = None
        snapshot_candidate = None
        exposed_candidate = None
        action_eligibility: AiActionEligibility | None = None

        if action_type is AiSuggestedActionType.observe_only:
            if suggestion.live_execution_requested:
                rejections.append(
                    self._rejection(
                        source=AiContractSource.cloud_planner,
                        code=AiBoundaryRejectionCode.invalid_action_eligibility,
                        summary="observe_only action suggestions must not request live execution.",
                        field_path="action_suggestion.live_execution_requested",
                    )
                )
            if not suggestion.dry_run_only:
                rejections.append(
                    self._rejection(
                        source=AiContractSource.cloud_planner,
                        code=AiBoundaryRejectionCode.invalid_action_eligibility,
                        summary="Planner action suggestions must remain dry-run only at the AI boundary.",
                        field_path="action_suggestion.dry_run_only",
                    )
                )
            action_eligibility = AiActionEligibility.observe_only
        elif action_type is AiSuggestedActionType.candidate_select:
            snapshot_candidate, exposed_candidate, candidate_rejections = self._resolve_candidate_reference(
                suggestion.candidate_id,
                suggestion.candidate_label,
                source=AiContractSource.cloud_planner,
                field_path="action_suggestion.candidate_id",
                context=context,
            )
            rejections.extend(candidate_rejections)
            target_label = self._coerce_target_label(
                suggestion.target_label,
                source=AiContractSource.cloud_planner,
                field_path="action_suggestion.target_label",
                rejections=rejections,
            )
            if not suggestion.dry_run_only:
                rejections.append(
                    self._rejection(
                        source=AiContractSource.cloud_planner,
                        code=AiBoundaryRejectionCode.invalid_action_eligibility,
                        summary="Planner action suggestions must remain dry-run only at the AI boundary.",
                        field_path="action_suggestion.dry_run_only",
                        related_candidate_id=suggestion.candidate_id,
                    )
                )
            eligibility_rejection = self._validate_action_eligibility(
                suggestion,
                context=context,
            )
            if eligibility_rejection is not None:
                rejections.append(eligibility_rejection)
            else:
                action_eligibility = (
                    AiActionEligibility.live_execution_eligible
                    if suggestion.live_execution_requested
                    else AiActionEligibility.dry_run_only
                )

        if rejections:
            return None, tuple(rejections)

        assert action_type is not None
        assert confidence is not None
        assert action_eligibility is not None
        return (
            ValidatedPlannerActionSuggestion(
                action_type=action_type,
                confidence=confidence,
                action_eligibility=action_eligibility,
                candidate_id=suggestion.candidate_id,
                candidate_label=(
                    suggestion.candidate_label
                    if suggestion.candidate_label is not None
                    else None if snapshot_candidate is None else snapshot_candidate.label
                ),
                target_label=target_label,
                dry_run_only=True,
                live_execution_requested=suggestion.live_execution_requested,
                observe_only=True,
                read_only=True,
                non_executing=True,
                metadata={
                    **dict(suggestion.metadata),
                    "ai_boundary_validated": True,
                    "ai_boundary_validator": self.validator_name,
                    "candidate_exposed": exposed_candidate is not None,
                },
            ),
            (),
        )

    def _validate_action_eligibility(
        self,
        suggestion: PlannerActionSuggestionContract,
        *,
        context: AiBoundaryValidationContext,
    ) -> AiBoundaryRejection | None:
        if not suggestion.live_execution_requested:
            return None

        failed_gate_ids: list[str] = []
        if context.run_config.mode is not AgentMode.safe_action_mode:
            failed_gate_ids.append("run_mode_safe_action")
        if context.run_config.allow_live_input is not True:
            failed_gate_ids.append("allow_live_input_enabled")
        if _enum_value(getattr(context.protected_context_assessment, "status", None)) != "clear":
            failed_gate_ids.append("protected_context_clear")
        if context.kill_switch_state.engaged:
            failed_gate_ids.append("kill_switch_disengaged")
        if context.pause_state.paused:
            failed_gate_ids.append("pause_state_running")
        if context.policy_context.live_execution_enabled is not True:
            failed_gate_ids.append("policy_live_execution_enabled")
        if context.policy_context.live_execution_requested is not True:
            failed_gate_ids.append("policy_live_execution_requested")
        if not failed_gate_ids:
            return None

        return self._rejection(
            source=AiContractSource.cloud_planner,
            code=AiBoundaryRejectionCode.invalid_action_eligibility,
            summary=(
                "Planner action suggestion is not eligible for the current mode or safety state."
            ),
            field_path="action_suggestion.live_execution_requested",
            related_candidate_id=suggestion.candidate_id,
            metadata={"failed_gate_ids": tuple(failed_gate_ids)},
        )

    def _validate_expected_transition(
        self,
        expectation: SemanticTransitionExpectation | None,
        *,
        snapshot: SemanticStateSnapshot | None,
    ) -> tuple[AiBoundaryRejection, ...]:
        if expectation is None:
            return ()
        if snapshot is None:
            return (
                self._rejection(
                    source=AiContractSource.cloud_planner,
                    code=AiBoundaryRejectionCode.missing_input,
                    summary="Semantic snapshot input is required to validate expected semantic outcomes.",
                    field_path="expected_transition",
                ),
            )

        rejections: list[AiBoundaryRejection] = []
        for outcome in expectation.expected_outcomes:
            rejections.extend(self._validate_expected_outcome(outcome, snapshot=snapshot))
        return tuple(rejections)

    def _validate_expected_outcome(
        self,
        outcome: ExpectedSemanticOutcome,
        *,
        snapshot: SemanticStateSnapshot,
    ) -> tuple[AiBoundaryRejection, ...]:
        exists, current_state, partial_reason = _semantic_item_state(snapshot, outcome.category, outcome.item_id)
        field_path = f"expected_transition.expected_outcomes[{outcome.outcome_id}]"
        if exists is None:
            return (
                self._rejection(
                    source=AiContractSource.cloud_planner,
                    code=AiBoundaryRejectionCode.partial_input,
                    summary=partial_reason or "Semantic input was incomplete for expected outcome validation.",
                    field_path=field_path,
                    related_candidate_id=(
                        outcome.item_id if outcome.category is SemanticDeltaCategory.candidate else None
                    ),
                ),
            )

        if outcome.expected_change is ExpectedSemanticChange.appeared and exists:
            return (
                self._rejection(
                    source=AiContractSource.cloud_planner,
                    code=AiBoundaryRejectionCode.impossible_state_transition,
                    summary=(
                        f"Expected outcome '{outcome.outcome_id}' cannot appear because "
                        f"'{outcome.item_id}' already exists in the current semantic snapshot."
                    ),
                    field_path=field_path,
                    related_candidate_id=(
                        outcome.item_id if outcome.category is SemanticDeltaCategory.candidate else None
                    ),
                ),
            )

        if outcome.expected_change in {
            ExpectedSemanticChange.disappeared,
            ExpectedSemanticChange.changed,
        } and not exists:
            return (
                self._rejection(
                    source=AiContractSource.cloud_planner,
                    code=AiBoundaryRejectionCode.impossible_state_transition,
                    summary=(
                        f"Expected outcome '{outcome.outcome_id}' requires '{outcome.item_id}' to be present "
                        "in the current semantic snapshot."
                    ),
                    field_path=field_path,
                    related_candidate_id=(
                        outcome.item_id if outcome.category is SemanticDeltaCategory.candidate else None
                    ),
                ),
            )

        if current_state is not None and outcome.expected_before_state:
            for key, value in outcome.expected_before_state.items():
                if current_state.get(key) != _freeze_value(value):
                    return (
                        self._rejection(
                            source=AiContractSource.cloud_planner,
                            code=AiBoundaryRejectionCode.impossible_state_transition,
                            summary=(
                                f"Expected outcome '{outcome.outcome_id}' does not match the current "
                                f"before-state field '{key}'."
                            ),
                            field_path=f"{field_path}.expected_before_state.{key}",
                            related_candidate_id=(
                                outcome.item_id
                                if outcome.category is SemanticDeltaCategory.candidate
                                else None
                            ),
                        ),
                    )

        if (
            outcome.category is SemanticDeltaCategory.candidate
            and outcome.minimum_score_delta is not None
            and current_state is not None
            and current_state.get("confidence") is None
        ):
            return (
                self._rejection(
                    source=AiContractSource.cloud_planner,
                    code=AiBoundaryRejectionCode.partial_input,
                    summary=(
                        f"Expected score change for candidate '{outcome.item_id}' requires current "
                        "candidate confidence metadata."
                    ),
                    field_path=f"{field_path}.minimum_score_delta",
                    related_candidate_id=outcome.item_id,
                ),
            )

        return ()

    def _resolve_candidate_reference(
        self,
        candidate_id: str | None,
        candidate_label: str | None,
        *,
        source: AiContractSource,
        field_path: str,
        context: AiBoundaryValidationContext,
    ):
        rejections: list[AiBoundaryRejection] = []
        if not candidate_id:
            rejections.append(
                self._rejection(
                    source=source,
                    code=AiBoundaryRejectionCode.invalid_candidate_reference,
                    summary="candidate_id must be provided for candidate-targeted AI output.",
                    field_path=field_path,
                )
            )
            return None, None, tuple(rejections)

        if context.snapshot is None:
            rejections.append(
                self._rejection(
                    source=source,
                    code=AiBoundaryRejectionCode.missing_input,
                    summary="Semantic snapshot input is required for candidate validation.",
                    field_path=field_path,
                    related_candidate_id=candidate_id,
                )
            )
            return None, None, tuple(rejections)

        snapshot_candidate = context.snapshot.get_candidate(candidate_id)
        if snapshot_candidate is None:
            rejections.append(
                self._rejection(
                    source=source,
                    code=AiBoundaryRejectionCode.invalid_candidate_reference,
                    summary=f"Candidate '{candidate_id}' does not exist in the current semantic snapshot.",
                    field_path=field_path,
                    related_candidate_id=candidate_id,
                )
            )
            return None, None, tuple(rejections)

        exposed_candidate = None
        if context.exposure_view is not None:
            if context.exposure_view.snapshot_id != context.snapshot.snapshot_id:
                rejections.append(
                    self._rejection(
                        source=source,
                        code=AiBoundaryRejectionCode.partial_input,
                        summary="Exposure view must come from the same semantic snapshot as the boundary context.",
                        field_path="exposure_view.snapshot_id",
                        related_candidate_id=candidate_id,
                    )
                )
                return None, None, tuple(rejections)

            exposed_candidate = next(
                (
                    candidate
                    for candidate in context.exposure_view.candidates
                    if candidate.candidate_id == candidate_id
                ),
                None,
            )
            if exposed_candidate is None:
                rejections.append(
                    self._rejection(
                        source=source,
                        code=AiBoundaryRejectionCode.invalid_candidate_reference,
                        summary=(
                            f"Candidate '{candidate_id}' is not present in the current exposed-candidate view."
                        ),
                        field_path=field_path,
                        related_candidate_id=candidate_id,
                    )
                )
                return None, None, tuple(rejections)

            if (
                context.exposure_view.signal_status == "partial"
                or exposed_candidate.completeness_status != "available"
            ):
                rejections.append(
                    self._rejection(
                        source=source,
                        code=AiBoundaryRejectionCode.partial_input,
                        summary=(
                            f"Candidate '{candidate_id}' exposure metadata is incomplete for safe AI-boundary use."
                        ),
                        field_path=field_path,
                        related_candidate_id=candidate_id,
                    )
                )
                return None, None, tuple(rejections)

        if candidate_label is not None and snapshot_candidate.label != candidate_label:
            rejections.append(
                self._rejection(
                    source=source,
                    code=AiBoundaryRejectionCode.invalid_candidate_reference,
                    summary=(
                        f"Candidate label '{candidate_label}' does not match current snapshot label "
                        f"'{snapshot_candidate.label}'."
                    ),
                    field_path=field_path,
                    related_candidate_id=candidate_id,
                )
            )
            return None, None, tuple(rejections)

        return snapshot_candidate, exposed_candidate, ()

    def _coerce_action_type(
        self,
        value: str,
        *,
        source: AiContractSource,
        field_path: str,
        rejections: list[AiBoundaryRejection],
    ) -> AiSuggestedActionType | None:
        try:
            return AiSuggestedActionType(value)
        except ValueError:
            rejections.append(
                self._rejection(
                    source=source,
                    code=AiBoundaryRejectionCode.invalid_action_eligibility,
                    summary=f"Unsupported action type '{value}'.",
                    field_path=field_path,
                )
            )
            return None

    def _coerce_target_label(
        self,
        value: str | None,
        *,
        source: AiContractSource,
        field_path: str,
        rejections: list[AiBoundaryRejection],
    ) -> AiTargetLabel | None:
        if not value:
            rejections.append(
                self._rejection(
                    source=source,
                    code=AiBoundaryRejectionCode.unsupported_target_label,
                    summary="target_label must be provided and supported.",
                    field_path=field_path,
                )
            )
            return None
        try:
            return AiTargetLabel(value)
        except ValueError:
            rejections.append(
                self._rejection(
                    source=source,
                    code=AiBoundaryRejectionCode.unsupported_target_label,
                    summary=f"Unsupported target label '{value}'.",
                    field_path=field_path,
                )
            )
            return None

    def _coerce_confidence(
        self,
        value: object,
        *,
        source: AiContractSource,
        field_path: str,
        rejections: list[AiBoundaryRejection],
    ) -> float | None:
        if isinstance(value, bool) or not isinstance(value, int | float):
            rejections.append(
                self._rejection(
                    source=source,
                    code=AiBoundaryRejectionCode.malformed_confidence,
                    summary="confidence must be a numeric value between 0.0 and 1.0 inclusive.",
                    field_path=field_path,
                )
            )
            return None

        confidence = float(value)
        if not 0.0 <= confidence <= 1.0:
            rejections.append(
                self._rejection(
                    source=source,
                    code=AiBoundaryRejectionCode.malformed_confidence,
                    summary="confidence must be between 0.0 and 1.0 inclusive.",
                    field_path=field_path,
                )
            )
            return None
        return confidence

    def _coerce_point(
        self,
        point: ResolverPointContract,
        *,
        source: AiContractSource,
        field_path: str,
        rejections: list[AiBoundaryRejection],
    ) -> NormalizedPoint | None:
        x = self._coerce_coordinate_component(
            point.x,
            source=source,
            field_path=f"{field_path}.x",
            rejections=rejections,
        )
        y = self._coerce_coordinate_component(
            point.y,
            source=source,
            field_path=f"{field_path}.y",
            rejections=rejections,
        )
        if x is None or y is None:
            return None
        return NormalizedPoint(x=x, y=y)

    def _coerce_coordinate_component(
        self,
        value: object,
        *,
        source: AiContractSource,
        field_path: str,
        rejections: list[AiBoundaryRejection],
    ) -> float | None:
        if isinstance(value, bool) or not isinstance(value, int | float):
            rejections.append(
                self._rejection(
                    source=source,
                    code=AiBoundaryRejectionCode.malformed_coordinate,
                    summary="Coordinates must be numeric normalized values.",
                    field_path=field_path,
                )
            )
            return None

        coordinate = float(value)
        if not 0.0 <= coordinate <= 1.0:
            rejections.append(
                self._rejection(
                    source=source,
                    code=AiBoundaryRejectionCode.out_of_bounds_coordinate,
                    summary="Coordinates must remain between 0.0 and 1.0 inclusive.",
                    field_path=field_path,
                )
            )
            return None
        return coordinate

    def _rejection(
        self,
        *,
        source: AiContractSource,
        code: AiBoundaryRejectionCode,
        summary: str,
        field_path: str | None = None,
        related_candidate_id: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> AiBoundaryRejection:
        return AiBoundaryRejection(
            source=source,
            code=code,
            summary=summary,
            field_path=field_path,
            related_candidate_id=related_candidate_id,
            observe_only=True,
            read_only=True,
            non_executing=True,
            metadata={} if metadata is None else metadata,
        )


def _semantic_item_state(
    snapshot: SemanticStateSnapshot,
    category: SemanticDeltaCategory,
    item_id: str,
) -> tuple[bool | None, Mapping[str, object] | None, str | None]:
    if category is SemanticDeltaCategory.layout_tree_node:
        if snapshot.layout_tree is None:
            return None, None, "Layout-tree input is unavailable for expected outcome validation."
        node = next((node for node in snapshot.layout_tree.walk() if node.node_id == item_id), None)
        if node is None:
            return False, None, None
        return True, _layout_tree_node_state(node), None

    if category is SemanticDeltaCategory.region_block:
        block = next((block for block in snapshot.region_blocks if block.block_id == item_id), None)
        if block is None:
            return False, None, None
        return True, _dataclass_state(block, id_field="block_id"), None

    if category is SemanticDeltaCategory.layout_region:
        region = next((region for region in snapshot.layout_regions if region.region_id == item_id), None)
        if region is None:
            return False, None, None
        return True, _dataclass_state(region, id_field="region_id"), None

    if category is SemanticDeltaCategory.text_region:
        region = next((region for region in snapshot.text_regions if region.region_id == item_id), None)
        if region is None:
            return False, None, None
        return True, _dataclass_state(region, id_field="region_id"), None

    if category is SemanticDeltaCategory.text_block:
        block = next((block for block in snapshot.text_blocks if block.text_block_id == item_id), None)
        if block is None:
            return False, None, None
        return True, _dataclass_state(block, id_field="text_block_id"), None

    if category is SemanticDeltaCategory.candidate:
        candidate = snapshot.get_candidate(item_id)
        if candidate is None:
            return False, None, None
        return (
            True,
            {
                **_dataclass_state(candidate, id_field="candidate_id"),
                "actionable": candidate.actionable,
            },
            None,
        )

    if category is SemanticDeltaCategory.snapshot_metadata:
        if item_id not in snapshot.metadata:
            return False, None, None
        return True, {"value": _freeze_value(snapshot.metadata[item_id])}, None

    return False, None, None


def _layout_tree_node_state(node: object) -> Mapping[str, object]:
    return {
        "role": _freeze_value(getattr(node, "role", None)),
        "name": _freeze_value(getattr(node, "name", None)),
        "bounds": _freeze_value(getattr(node, "bounds", None)),
        "visible": _freeze_value(getattr(node, "visible", None)),
        "enabled": _freeze_value(getattr(node, "enabled", None)),
        "child_node_ids": tuple(child.node_id for child in getattr(node, "children", ())),
        "attributes": _freeze_value(getattr(node, "attributes", {})),
    }


def _dataclass_state(item: object, *, id_field: str) -> Mapping[str, object]:
    state: dict[str, object] = {}
    for dataclass_field in fields(item):
        if dataclass_field.name == id_field:
            continue
        state[dataclass_field.name] = _freeze_value(getattr(item, dataclass_field.name))
    return state


def _freeze_value(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, NormalizedBBox):
        return {
            "left": value.left,
            "top": value.top,
            "width": value.width,
            "height": value.height,
        }
    if isinstance(value, NormalizedPoint):
        return {"x": value.x, "y": value.y}
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, Mapping):
        frozen_mapping: dict[str, object] = {}
        for key in sorted(value, key=str):
            frozen_mapping[str(key)] = _freeze_value(value[key])
        return frozen_mapping
    if isinstance(value, tuple | list):
        return tuple(_freeze_value(item) for item in value)
    return value


def _enum_value(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Enum):
        return value.value
    return value


def _point_in_bounds(point: NormalizedPoint, bounds: NormalizedBBox) -> bool:
    return (
        bounds.left <= point.x <= bounds.left + bounds.width
        and bounds.top <= point.y <= bounds.top + bounds.height
    )
