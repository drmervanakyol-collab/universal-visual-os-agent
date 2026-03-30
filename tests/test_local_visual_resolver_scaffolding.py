from __future__ import annotations

from dataclasses import replace

from test_ai_boundary_contracts import _boundary_context

from universal_visual_os_agent.ai_architecture import (
    AiArchitectureSignalStatus,
    DeterministicEscalationDecision,
    DeterministicEscalationDisposition,
    DeterministicEscalationReason,
    LocalVisualResolverOutcome,
    LocalVisualResolverOutputContract,
    LocalVisualResolverRationaleCode,
    LocalVisualResolverTaskType,
    ObserveOnlyLocalVisualResolverScaffolder,
    ObserveOnlySharedOntologyBinder,
    SharedCandidateLabel,
)


class _ExplodingLocalVisualResolverScaffolder(ObserveOnlyLocalVisualResolverScaffolder):
    def _build_shortlist_entry(
        self,
        *,
        snapshot,
        semantic_candidate,
        exposed_candidate,
        rank,
    ):
        del snapshot, semantic_candidate, exposed_candidate, rank
        raise RuntimeError("local visual resolver exploded")


def _escalation_decision() -> DeterministicEscalationDecision:
    return DeterministicEscalationDecision(
        disposition=DeterministicEscalationDisposition.local_resolver_recommended,
        summary="Local resolver is recommended for shortlist disambiguation.",
        signal_status=AiArchitectureSignalStatus.available,
        reason_codes=(
            DeterministicEscalationReason.disambiguation_needed,
            DeterministicEscalationReason.high_selection_risk,
        ),
    )


def test_local_visual_resolver_builds_valid_request() -> None:
    snapshot, exposure_view, _candidate = _boundary_context()
    scaffolder = ObserveOnlyLocalVisualResolverScaffolder()
    shortlist_ids = tuple(candidate.candidate_id for candidate in exposure_view.candidates[:2])

    result = scaffolder.build_request(
        snapshot,
        exposure_view,
        candidate_ids=shortlist_ids,
        summary="Choose among the top ambiguous candidates.",
        request_id="resolver-shortlist-1",
        task_type=LocalVisualResolverTaskType.choose_candidate,
        escalation_decision=_escalation_decision(),
    )

    assert result.success is True
    assert result.request is not None
    assert result.request.observe_only is True
    assert result.request.read_only is True
    assert result.request.non_executing is True
    assert result.request.signal_status is AiArchitectureSignalStatus.available
    assert tuple(
        entry.candidate_binding.candidate_id for entry in result.request.candidate_shortlist
    ) == shortlist_ids
    assert all(
        entry.metadata["candidate_resolver_readiness_status"] in {"ready", "conflicted"}
        for entry in result.request.candidate_shortlist
    )
    assert all(
        entry.crop_reference.snapshot_id == snapshot.snapshot_id
        for entry in result.request.candidate_shortlist
    )
    assert result.request.metadata["resolver_readiness_status_counts"]
    assert result.request.metadata["resolver_ready_candidate_ids"] or result.request.metadata[
        "resolver_conflicted_candidate_ids"
    ]
    assert (
        result.request.ambiguity_context.escalation_disposition
        is DeterministicEscalationDisposition.local_resolver_recommended
    )


def test_local_visual_resolver_binds_valid_resolved_response() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    scaffolder = ObserveOnlyLocalVisualResolverScaffolder()
    request_result = scaffolder.build_request(
        snapshot,
        exposure_view,
        candidate_ids=(candidate.candidate_id,),
        summary="Confirm the single shortlisted candidate.",
        request_id="resolver-response-1",
        task_type=LocalVisualResolverTaskType.choose_candidate,
    )
    assert request_result.success is True
    assert request_result.request is not None

    response_result = scaffolder.bind_response(
        request_result.request,
        contract=LocalVisualResolverOutputContract(
            response_id="resolver-response-1",
            request_id=request_result.request.request_id,
            summary="The shortlisted candidate is the best match.",
            task_type=LocalVisualResolverTaskType.choose_candidate,
            outcome=LocalVisualResolverOutcome.resolved,
            rationale_code=LocalVisualResolverRationaleCode.shortlist_disambiguation,
            selected_candidate_id=candidate.candidate_id,
            confidence=0.93,
        ),
    )

    assert response_result.success is True
    assert response_result.response is not None
    assert response_result.response.outcome is LocalVisualResolverOutcome.resolved
    assert response_result.response.selected_candidate_id == candidate.candidate_id
    assert response_result.response.selected_candidate_binding is not None
    assert response_result.response.selected_crop_reference is not None
    assert response_result.response.selected_label is not None
    assert response_result.response.signal_status is AiArchitectureSignalStatus.available
    assert response_result.response.non_executing is True


def test_local_visual_resolver_supports_unknown_outcome_safely() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    binding_result = ObserveOnlySharedOntologyBinder().bind_exposed_candidate(exposure_view.candidates[0])
    assert binding_result.success is True
    assert binding_result.binding is not None
    assert binding_result.binding.shared_candidate_label is not None
    scaffolder = ObserveOnlyLocalVisualResolverScaffolder()
    request_result = scaffolder.build_request(
        snapshot,
        exposure_view,
        candidate_ids=(candidate.candidate_id,),
        summary="Classify a cropped region conservatively.",
        request_id="resolver-unknown-1",
        task_type=LocalVisualResolverTaskType.classify_region,
        allowed_candidate_labels=(binding_result.binding.shared_candidate_label,),
    )
    assert request_result.success is True
    assert request_result.request is not None

    response_result = scaffolder.bind_response(
        request_result.request,
        contract=LocalVisualResolverOutputContract(
            response_id="resolver-unknown-1",
            request_id=request_result.request.request_id,
            summary="The crop could not be classified confidently.",
            task_type=LocalVisualResolverTaskType.classify_region,
            outcome=LocalVisualResolverOutcome.unknown,
            rationale_code=LocalVisualResolverRationaleCode.unknown,
        ),
    )

    assert response_result.success is True
    assert response_result.response is not None
    assert response_result.response.outcome is LocalVisualResolverOutcome.unknown
    assert response_result.response.selected_candidate_id is None
    assert response_result.response.signal_status is AiArchitectureSignalStatus.partial


def test_local_visual_resolver_supports_need_more_context_path() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    binding_result = ObserveOnlySharedOntologyBinder().bind_exposed_candidate(exposure_view.candidates[0])
    assert binding_result.success is True
    assert binding_result.binding is not None
    assert binding_result.binding.shared_candidate_label is not None
    scaffolder = ObserveOnlyLocalVisualResolverScaffolder()
    request_result = scaffolder.build_request(
        snapshot,
        exposure_view,
        candidate_ids=(candidate.candidate_id,),
        summary="Confirm whether the crop matches the expected UI role.",
        request_id="resolver-more-context-1",
        task_type=LocalVisualResolverTaskType.confirm_ui_role,
        allowed_candidate_labels=(binding_result.binding.shared_candidate_label,),
    )
    assert request_result.success is True
    assert request_result.request is not None

    response_result = scaffolder.bind_response(
        request_result.request,
        contract=LocalVisualResolverOutputContract(
            response_id="resolver-more-context-1",
            request_id=request_result.request.request_id,
            summary="The crop needs a wider context window before role confirmation.",
            task_type=LocalVisualResolverTaskType.confirm_ui_role,
            outcome=LocalVisualResolverOutcome.unresolved,
            rationale_code=LocalVisualResolverRationaleCode.insufficient_context,
            need_more_context=True,
        ),
    )

    assert response_result.success is True
    assert response_result.response is not None
    assert response_result.response.need_more_context is True
    assert response_result.response.outcome is LocalVisualResolverOutcome.unresolved
    assert response_result.response.signal_status is AiArchitectureSignalStatus.partial


def test_local_visual_resolver_handles_partial_and_conflicting_input_safely() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    partial_candidate = replace(exposure_view.candidates[0], completeness_status="partial")
    partial_exposure_view = replace(
        exposure_view,
        candidates=(partial_candidate,) + exposure_view.candidates[1:],
        signal_status="partial",
    )
    scaffolder = ObserveOnlyLocalVisualResolverScaffolder()

    partial_result = scaffolder.build_request(
        snapshot,
        partial_exposure_view,
        candidate_ids=(candidate.candidate_id,),
        summary="Build a request with partial shortlist metadata.",
        request_id="resolver-partial-1",
    )
    assert partial_result.success is True
    assert partial_result.request is not None
    conflicted_candidate = replace(
        exposure_view.candidates[0],
        source_conflict_present=True,
        disambiguation_needed=True,
        requires_local_resolver=True,
    )
    conflicted_exposure_view = replace(
        exposure_view,
        candidates=(conflicted_candidate,) + exposure_view.candidates[1:],
    )
    conflicted_result = scaffolder.build_request(
        snapshot,
        conflicted_exposure_view,
        candidate_ids=(candidate.candidate_id,),
        summary="Build a request with a conflicted but complete shortlist candidate.",
        request_id="resolver-conflicted-1",
    )

    shortlist_labels = {
        entry.candidate_binding.shared_candidate_label
        for entry in partial_result.request.candidate_shortlist
        if entry.candidate_binding.shared_candidate_label is not None
    }
    conflicting_label = next(
        label for label in SharedCandidateLabel if label not in shortlist_labels
    )
    conflict_result = scaffolder.build_request(
        snapshot,
        exposure_view,
        candidate_ids=(candidate.candidate_id,),
        summary="Build a request with conflicting label constraints.",
        request_id="resolver-conflict-1",
        task_type=LocalVisualResolverTaskType.classify_region,
        allowed_candidate_labels=(conflicting_label,),
    )

    assert partial_result.request.signal_status is AiArchitectureSignalStatus.partial
    assert partial_result.request.metadata["partial_candidate_ids"] == (candidate.candidate_id,)
    assert partial_result.request.metadata["resolver_partial_candidate_ids"] == (
        candidate.candidate_id,
    )
    assert partial_result.request.metadata["resolver_readiness_status_counts"] == (
        ("conflicted", 0),
        ("partial", 1),
        ("ready", 0),
    )
    assert conflicted_result.success is True
    assert conflicted_result.request is not None
    assert conflicted_result.request.signal_status is AiArchitectureSignalStatus.available
    assert conflicted_result.request.metadata["resolver_conflicted_candidate_ids"] == (
        candidate.candidate_id,
    )
    assert conflict_result.success is False
    assert conflict_result.error_code == "local_visual_resolver_request_label_conflict"


def test_local_visual_resolver_does_not_propagate_unhandled_exceptions() -> None:
    snapshot, exposure_view, candidate = _boundary_context()

    result = _ExplodingLocalVisualResolverScaffolder().build_request(
        snapshot,
        exposure_view,
        candidate_ids=(candidate.candidate_id,),
        summary="Exercise exception safety.",
        request_id="resolver-explodes-1",
    )

    assert result.success is False
    assert result.error_code == "local_visual_resolver_request_build_exception"
    assert result.error_message == "local visual resolver exploded"
