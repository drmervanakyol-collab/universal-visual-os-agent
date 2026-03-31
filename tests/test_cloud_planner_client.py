from __future__ import annotations

import json

from test_ai_boundary_contracts import _boundary_context

from universal_visual_os_agent.actions.scaffolding import ObserveOnlyActionIntentScaffolder
from universal_visual_os_agent.ai_architecture import (
    AiArchitectureSignalStatus,
    CloudPlannerBackendAvailability,
    CloudPlannerClientConfig,
    CloudPlannerOutcome,
    DeterministicEscalationDecision,
    DeterministicEscalationDisposition,
    ObserveOnlyBackendBackedCloudPlanner,
    ObserveOnlyClientBackedCloudPlannerBackend,
    ObserveOnlyCloudPlannerScaffolder,
    ObserveOnlyOpenAiCompatibleCloudPlannerClient,
    SharedTargetLabel,
)
from universal_visual_os_agent.ai_architecture.arbitration import ArbitrationSource
from universal_visual_os_agent.ai_architecture.cloud_planner_client import (
    CloudPlannerTransportResponse,
)
from universal_visual_os_agent.ai_boundary import AiSuggestedActionType
from universal_visual_os_agent.scenarios.models import ScenarioDefinition
from universal_visual_os_agent.verification import (
    VerificationResult,
    VerificationStatus,
)


class _ScriptedPlannerClient:
    def __init__(
        self,
        responses: tuple[str, ...],
        *,
        raise_error: str | None = None,
        config: CloudPlannerClientConfig | None = None,
        availability: CloudPlannerBackendAvailability = CloudPlannerBackendAvailability.available,
    ) -> None:
        self._responses = list(responses)
        self._raise_error = raise_error
        self._availability = availability
        self._config = (
            CloudPlannerClientConfig(
                endpoint_url="https://planner.example.test/v1/chat/completions",
                model="planner-test-model",
                api_key="test-key",
            )
            if config is None
            else config
        )
        self.prompts = []

    @property
    def availability(self) -> CloudPlannerBackendAvailability:
        return self._availability

    @property
    def config(self) -> CloudPlannerClientConfig:
        return self._config

    def complete(self, prompt):  # type: ignore[override]
        self.prompts.append(prompt)
        if self._raise_error is not None:
            raise RuntimeError(self._raise_error)
        assert self._responses, "No scripted planner response remained."
        raw_text = self._responses.pop(0)
        return CloudPlannerTransportResponse.ok(
            client_name="ScriptedPlannerClient",
            availability=self._availability,
            prompt=prompt,
            raw_text=raw_text,
            status_code=200,
        )


def _scenario_definition() -> ScenarioDefinition:
    return ScenarioDefinition(
        scenario_id="scenario-confirm-primary",
        title="Confirm Primary Candidate",
        summary="Confirm the highest-confidence deterministic candidate safely.",
    )


def _verification_result(candidate_id: str) -> VerificationResult:
    return VerificationResult(
        status=VerificationStatus.satisfied,
        summary="The current semantic transition still supports the candidate goal.",
        matched_candidate_ids=(candidate_id,),
        matched_outcome_ids=("criterion-1",),
        observe_only=True,
        read_only=True,
        non_actionable=True,
    )


def _escalation_decision() -> DeterministicEscalationDecision:
    return DeterministicEscalationDecision(
        disposition=DeterministicEscalationDisposition.deterministic_ok,
        summary="Deterministic evidence is currently sufficient.",
        signal_status=AiArchitectureSignalStatus.available,
        recommended_source=ArbitrationSource.deterministic_pipeline,
    )


def _scaffold_view(snapshot, exposure_view):
    result = ObserveOnlyActionIntentScaffolder().scaffold(
        snapshot,
        exposure_view=exposure_view,
    )
    assert result.success is True
    assert result.scaffold_view is not None
    return result.scaffold_view


def _build_request():
    snapshot, exposure_view, candidate = _boundary_context()
    result = ObserveOnlyCloudPlannerScaffolder().build_request(
        snapshot,
        exposure_view,
        user_objective_summary="Confirm the primary button candidate safely.",
        request_id="planner-client-request-1",
        scenario_definition=_scenario_definition(),
        verification_result=_verification_result(candidate.candidate_id),
        action_scaffold_view=_scaffold_view(snapshot, exposure_view),
        escalation_decision=_escalation_decision(),
    )
    assert result.success is True
    assert result.request is not None
    return snapshot, exposure_view, candidate, result.request


def _planned_response_json(request, candidate) -> str:
    candidate_summary_entry = request.candidate_summary[0]
    shared_label = candidate_summary_entry.candidate_binding.shared_candidate_label
    assert shared_label is not None
    return json.dumps(
        {
            "summary": "Normalize the current objective into one dry-run candidate selection step.",
            "outcome": CloudPlannerOutcome.planned.value,
            "rationale_code": "goal_decomposition",
            "normalized_goal": "Confirm the primary button candidate without execution.",
            "success_criteria": [
                {
                    "criterion_id": "criterion-1",
                    "summary": "The selected candidate remains present in the semantic state.",
                    "expectation": {
                        "summary": "Candidate remains required.",
                        "required_candidate_ids": [candidate.candidate_id],
                    },
                }
            ],
            "subgoals": [
                {
                    "subgoal_id": "subgoal-select-primary",
                    "summary": "Bind the current primary candidate into a dry-run scenario step.",
                    "action_type": AiSuggestedActionType.candidate_select.value,
                    "candidate_id": candidate.candidate_id,
                    "candidate_label": shared_label.value,
                    "target_label": SharedTargetLabel.candidate_center.value,
                    "success_criterion_ids": ["criterion-1"],
                }
            ],
        },
        ensure_ascii=False,
    )


def test_cloud_planner_client_runtime_supports_successful_planner_path() -> None:
    _snapshot, _exposure_view, candidate, request = _build_request()
    planner = ObserveOnlyBackendBackedCloudPlanner(
        backend=ObserveOnlyClientBackedCloudPlannerBackend(
            client=_ScriptedPlannerClient(
                responses=(_planned_response_json(request, candidate),),
            )
        )
    )

    result = planner.plan_request(request)

    assert result.success is True
    assert result.backend_result is not None
    assert result.response is not None
    assert result.availability is CloudPlannerBackendAvailability.available
    assert result.response.outcome is CloudPlannerOutcome.planned
    assert result.response.scenario_definition is not None
    assert result.response.scenario_definition_view is not None
    assert result.response.non_executing is True
    assert result.backend_result.correction_attempt_count == 0
    assert result.backend_result.prompt_attempts[0].compact_context["candidate_summary"]


def test_cloud_planner_client_retries_malformed_response_and_recovers() -> None:
    _snapshot, _exposure_view, candidate, request = _build_request()
    scripted_client = _ScriptedPlannerClient(
        responses=(
            "{not-valid-json",
            _planned_response_json(request, candidate),
        ),
        config=CloudPlannerClientConfig(
            endpoint_url="https://planner.example.test/v1/chat/completions",
            model="planner-test-model",
            api_key="test-key",
            max_correction_retries=1,
        ),
    )
    planner = ObserveOnlyBackendBackedCloudPlanner(
        backend=ObserveOnlyClientBackedCloudPlannerBackend(client=scripted_client)
    )

    result = planner.plan_request(request)

    assert result.success is True
    assert result.backend_result is not None
    assert result.response is not None
    assert result.backend_result.correction_attempt_count == 1
    assert len(result.backend_result.prompt_attempts) == 2
    assert result.backend_result.prompt_attempts[1].correction_feedback is not None
    assert result.response.outcome is CloudPlannerOutcome.planned


def test_cloud_planner_client_reports_backend_unavailable_safely() -> None:
    _snapshot, _exposure_view, _candidate, request = _build_request()
    backend = ObserveOnlyClientBackedCloudPlannerBackend(
        client=ObserveOnlyOpenAiCompatibleCloudPlannerClient(
            config=CloudPlannerClientConfig()
        )
    )

    result = backend.plan(request)

    assert result.success is False
    assert result.availability is CloudPlannerBackendAvailability.unavailable
    assert result.error_code == "cloud_planner_backend_unavailable"


def test_cloud_planner_client_reports_schema_invalid_response_safely() -> None:
    _snapshot, _exposure_view, _candidate, request = _build_request()
    backend = ObserveOnlyClientBackedCloudPlannerBackend(
        client=_ScriptedPlannerClient(
            responses=(
                json.dumps(
                    {
                        "summary": "Invalid planned response without subgoals.",
                        "outcome": "planned",
                        "rationale_code": "goal_decomposition",
                        "normalized_goal": "Still invalid.",
                        "subgoals": [],
                    }
                ),
            ),
            config=CloudPlannerClientConfig(
                endpoint_url="https://planner.example.test/v1/chat/completions",
                model="planner-test-model",
                api_key="test-key",
                max_correction_retries=0,
            ),
        )
    )

    result = backend.plan(request)

    assert result.success is False
    assert result.error_code == "cloud_planner_response_schema_invalid"
    assert result.output_contract is None


def test_cloud_planner_client_reports_retry_exhaustion_safely() -> None:
    _snapshot, _exposure_view, _candidate, request = _build_request()
    backend = ObserveOnlyClientBackedCloudPlannerBackend(
        client=_ScriptedPlannerClient(
            responses=("{", "{"),
            config=CloudPlannerClientConfig(
                endpoint_url="https://planner.example.test/v1/chat/completions",
                model="planner-test-model",
                api_key="test-key",
                max_correction_retries=1,
            ),
        )
    )

    result = backend.plan(request)

    assert result.success is False
    assert result.error_code == "cloud_planner_response_retry_exhausted"
    assert result.details["last_error_code"] == "cloud_planner_response_malformed"


def test_cloud_planner_client_does_not_propagate_unhandled_exceptions() -> None:
    _snapshot, _exposure_view, _candidate, request = _build_request()
    backend = ObserveOnlyClientBackedCloudPlannerBackend(
        client=_ScriptedPlannerClient(
            responses=(),
            raise_error="planner client exploded",
        )
    )

    result = backend.plan(request)

    assert result.success is False
    assert result.error_code == "cloud_planner_client_exception"
    assert result.error_message == "planner client exploded"
