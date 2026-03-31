from __future__ import annotations

from dataclasses import replace

from test_ai_boundary_contracts import _boundary_context

from universal_visual_os_agent.ai_architecture import (
    AiArchitectureSignalStatus,
    LocalVisualResolverBackendAvailability,
    LocalVisualResolverBackendConfig,
    LocalVisualResolverOutcome,
    LocalVisualResolverRationaleCode,
    LocalVisualResolverTaskType,
    ObserveOnlyBackendBackedLocalVisualResolver,
    ObserveOnlyMetadataLocalVisualResolverBackend,
    ObserveOnlySharedOntologyBinder,
)


class _ExplodingResolverBackend(ObserveOnlyMetadataLocalVisualResolverBackend):
    def resolve(self, request):  # type: ignore[override]
        del request
        raise RuntimeError("resolver backend exploded")


def _shared_label_for_first_candidate():
    snapshot, exposure_view, _candidate = _boundary_context()
    binding_result = ObserveOnlySharedOntologyBinder().bind_exposed_candidate(
        exposure_view.candidates[0]
    )
    assert binding_result.success is True
    assert binding_result.binding is not None
    assert binding_result.binding.shared_candidate_label is not None
    return snapshot, exposure_view, binding_result.binding.shared_candidate_label


def test_local_visual_resolver_backend_resolves_choose_candidate_path() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    resolver = ObserveOnlyBackendBackedLocalVisualResolver()

    result = resolver.resolve(
        snapshot,
        exposure_view,
        candidate_ids=(candidate.candidate_id,),
        summary="Choose the single shortlisted candidate.",
        request_id="backend-choose-1",
        task_type=LocalVisualResolverTaskType.choose_candidate,
    )

    assert result.success is True
    assert result.request is not None
    assert result.backend_result is not None
    assert result.response is not None
    assert result.availability is LocalVisualResolverBackendAvailability.available
    assert result.response.outcome is LocalVisualResolverOutcome.resolved
    assert result.response.rationale_code is LocalVisualResolverRationaleCode.shortlist_disambiguation
    assert result.response.selected_candidate_id == candidate.candidate_id
    assert result.response.confidence is not None
    assert result.response.confidence >= 0.80
    assert result.response.observe_only is True
    assert result.response.read_only is True
    assert result.response.non_executing is True


def test_local_visual_resolver_backend_resolves_classify_region_path() -> None:
    snapshot, exposure_view, shared_label = _shared_label_for_first_candidate()
    candidate_id = exposure_view.candidates[0].candidate_id
    resolver = ObserveOnlyBackendBackedLocalVisualResolver()

    result = resolver.resolve(
        snapshot,
        exposure_view,
        candidate_ids=(candidate_id,),
        summary="Classify the cropped candidate region.",
        request_id="backend-classify-1",
        task_type=LocalVisualResolverTaskType.classify_region,
        allowed_candidate_labels=(shared_label,),
    )

    assert result.success is True
    assert result.response is not None
    assert result.response.outcome is LocalVisualResolverOutcome.resolved
    assert result.response.rationale_code is LocalVisualResolverRationaleCode.constrained_label_match
    assert result.response.selected_candidate_id == candidate_id
    assert result.response.selected_label is shared_label


def test_local_visual_resolver_backend_resolves_confirm_ui_role_path() -> None:
    snapshot, exposure_view, shared_label = _shared_label_for_first_candidate()
    candidate_id = exposure_view.candidates[0].candidate_id
    resolver = ObserveOnlyBackendBackedLocalVisualResolver()

    result = resolver.resolve(
        snapshot,
        exposure_view,
        candidate_ids=(candidate_id,),
        summary="Confirm the expected UI role for the shortlisted region.",
        request_id="backend-confirm-1",
        task_type=LocalVisualResolverTaskType.confirm_ui_role,
        allowed_candidate_labels=(shared_label,),
    )

    assert result.success is True
    assert result.response is not None
    assert result.response.outcome is LocalVisualResolverOutcome.resolved
    assert result.response.rationale_code is LocalVisualResolverRationaleCode.expected_role_confirmed
    assert result.response.selected_candidate_id == candidate_id
    assert result.response.selected_label is shared_label


def test_local_visual_resolver_backend_reports_backend_unavailable_safely() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    resolver = ObserveOnlyBackendBackedLocalVisualResolver(
        backend=ObserveOnlyMetadataLocalVisualResolverBackend(
            config=LocalVisualResolverBackendConfig(
                availability=LocalVisualResolverBackendAvailability.unavailable
            )
        )
    )

    result = resolver.resolve(
        snapshot,
        exposure_view,
        candidate_ids=(candidate.candidate_id,),
        summary="Exercise the unavailable backend path.",
        request_id="backend-unavailable-1",
    )

    assert result.success is False
    assert result.availability is LocalVisualResolverBackendAvailability.unavailable
    assert result.error_code == "local_visual_resolver_backend_unavailable"
    assert result.response is None


def test_local_visual_resolver_backend_returns_unknown_for_low_confidence() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    resolver = ObserveOnlyBackendBackedLocalVisualResolver()
    request_result = resolver._scaffolder.build_request(  # noqa: SLF001 - targeted test seam
        snapshot,
        exposure_view,
        candidate_ids=(candidate.candidate_id,),
        summary="Build a low-confidence resolver request.",
        request_id="backend-low-confidence-1",
    )
    assert request_result.success is True
    assert request_result.request is not None
    low_confidence_entry = replace(request_result.request.candidate_shortlist[0], score=0.20)
    request = replace(
        request_result.request,
        candidate_shortlist=(low_confidence_entry,),
    )

    result = resolver.resolve_request(request)

    assert result.success is True
    assert result.response is not None
    assert result.response.outcome is LocalVisualResolverOutcome.unknown
    assert result.response.rationale_code is LocalVisualResolverRationaleCode.unknown
    assert result.response.selected_candidate_id is None
    assert result.response.signal_status is AiArchitectureSignalStatus.partial


def test_local_visual_resolver_backend_returns_need_more_context_for_close_shortlist() -> None:
    snapshot, exposure_view, _candidate = _boundary_context()
    resolver = ObserveOnlyBackendBackedLocalVisualResolver()
    shortlist_ids = tuple(candidate.candidate_id for candidate in exposure_view.candidates[:2])

    result = resolver.resolve(
        snapshot,
        exposure_view,
        candidate_ids=shortlist_ids,
        summary="Resolve between two equally plausible shortlist candidates.",
        request_id="backend-close-shortlist-1",
        task_type=LocalVisualResolverTaskType.choose_candidate,
    )

    assert result.success is True
    assert result.response is not None
    assert result.response.outcome is LocalVisualResolverOutcome.unresolved
    assert result.response.need_more_context is True
    assert result.response.rationale_code is LocalVisualResolverRationaleCode.unresolved_shortlist


def test_local_visual_resolver_backend_handles_partial_and_conflicting_requests_safely() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    resolver = ObserveOnlyBackendBackedLocalVisualResolver()
    request_result = resolver._scaffolder.build_request(  # noqa: SLF001 - targeted test seam
        snapshot,
        exposure_view,
        candidate_ids=(candidate.candidate_id,),
        summary="Build a request that will be modified for safety checks.",
        request_id="backend-partial-conflict-1",
    )
    assert request_result.success is True
    assert request_result.request is not None

    partial_request = replace(
        request_result.request,
        signal_status=AiArchitectureSignalStatus.partial,
    )
    partial_result = resolver.resolve_request(partial_request)

    conflicting_request = replace(
        request_result.request,
        ambiguity_context=replace(
            request_result.request.ambiguity_context,
            source_conflict_present=True,
        ),
    )
    conflicting_result = resolver.resolve_request(conflicting_request)

    assert partial_result.success is True
    assert partial_result.response is not None
    assert partial_result.response.outcome is LocalVisualResolverOutcome.unresolved
    assert partial_result.response.need_more_context is True
    assert partial_result.response.rationale_code is LocalVisualResolverRationaleCode.insufficient_context

    assert conflicting_result.success is True
    assert conflicting_result.response is not None
    assert conflicting_result.response.outcome is LocalVisualResolverOutcome.unresolved
    assert conflicting_result.response.need_more_context is True
    assert conflicting_result.response.rationale_code is LocalVisualResolverRationaleCode.conflicting_signals


def test_local_visual_resolver_backend_does_not_propagate_unhandled_exceptions() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    resolver = ObserveOnlyBackendBackedLocalVisualResolver(
        backend=_ExplodingResolverBackend()
    )
    request_result = resolver._scaffolder.build_request(  # noqa: SLF001 - targeted test seam
        snapshot,
        exposure_view,
        candidate_ids=(candidate.candidate_id,),
        summary="Build a request for exception safety.",
        request_id="backend-explodes-1",
    )
    assert request_result.success is True
    assert request_result.request is not None

    result = resolver.resolve_request(request_result.request)

    assert result.success is False
    assert result.error_code == "local_visual_resolver_backend_exception"
    assert result.error_message == "resolver backend exploded"
