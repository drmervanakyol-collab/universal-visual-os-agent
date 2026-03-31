"""Real cloud planner client/runtime integration behind the observe-only scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import json
import os
from typing import IO, Any, Mapping, Protocol, Self, cast
from urllib import error as urllib_error
from urllib import request as urllib_request

from universal_visual_os_agent.ai_architecture.arbitration import ArbitrationSource
from universal_visual_os_agent.ai_architecture.cloud_planner import (
    CloudPlannerBoundResponse,
    CloudPlannerEscalationRecommendation,
    CloudPlannerFallbackPlan,
    CloudPlannerForbiddenActionLabel,
    CloudPlannerOutcome,
    CloudPlannerOutputContract,
    CloudPlannerRationaleCode,
    CloudPlannerRequest,
    CloudPlannerResponseBindResult,
    ObserveOnlyCloudPlannerScaffolder,
    CloudPlannerSubgoal,
    CloudPlannerSuccessCriterion,
)
from universal_visual_os_agent.ai_architecture.cloud_planner_prompt_engine import (
    CloudPlannerPromptEnvelope,
    ObserveOnlyCloudPlannerPromptEngine,
)
from universal_visual_os_agent.ai_architecture.escalation_engine import (
    DeterministicEscalationDecision,
    DeterministicEscalationDisposition,
    DeterministicEscalationReason,
)
from universal_visual_os_agent.ai_architecture.ontology import (
    SharedCandidateLabel,
    SharedTargetLabel,
)
from universal_visual_os_agent.ai_boundary.models import AiSuggestedActionType
from universal_visual_os_agent.actions.scaffolding_models import ActionIntentScaffoldView
from universal_visual_os_agent.scenarios.models import ScenarioDefinition
from universal_visual_os_agent.semantics.candidate_exposure import CandidateExposureView
from universal_visual_os_agent.semantics.semantic_delta import SemanticDeltaCategory
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot
from universal_visual_os_agent.verification.models import (
    CandidateScoreDeltaDirection,
    ExpectedSemanticChange,
    ExpectedSemanticOutcome,
    SemanticTransitionExpectation,
    VerificationOutcomeBranch,
    VerificationResult,
    VerificationTimingPolicy,
)


class CloudPlannerBackendAvailability(StrEnum):
    """Availability states for the real cloud planner backend."""

    available = "available"
    unavailable = "unavailable"


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerClientConfig:
    """Configuration for the first real cloud planner HTTP client."""

    endpoint_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    api_key_env_var: str = "OPENAI_API_KEY"
    provider_name: str = "openai_compatible_chat_completions"
    timeout_seconds: float = 20.0
    temperature: float = 0.0
    max_correction_retries: int = 1
    max_response_characters: int = 64000
    max_correction_feedback_characters: int = 1200
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    extra_headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be positive.")
        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError("temperature must be between 0.0 and 1.0 inclusive.")
        if self.max_correction_retries < 0:
            raise ValueError("max_correction_retries must not be negative.")
        if self.max_response_characters <= 0:
            raise ValueError("max_response_characters must be positive.")
        if self.max_correction_feedback_characters <= 0:
            raise ValueError("max_correction_feedback_characters must be positive.")
        if not self.api_key_env_var:
            raise ValueError("api_key_env_var must not be empty.")
        if not self.provider_name:
            raise ValueError("provider_name must not be empty.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Cloud planner client config must remain safety-first.")

    def resolved_api_key(self) -> str | None:
        """Return the configured API key or environment-provided fallback."""

        if self.api_key:
            return self.api_key
        return os.getenv(self.api_key_env_var)


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerTransportResponse:
    """Failure-safe raw client response from the cloud planner backend."""

    client_name: str
    success: bool
    availability: CloudPlannerBackendAvailability
    prompt: CloudPlannerPromptEnvelope | None = None
    raw_text: str | None = None
    status_code: int | None = None
    response_payload: Mapping[str, object] | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.client_name:
            raise ValueError("client_name must not be empty.")
        if self.success and self.raw_text is None:
            raise ValueError("Successful transport responses must include raw_text.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed transport responses must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful transport responses must not include error details.")
        if not self.success and self.raw_text is not None:
            raise ValueError("Failed transport responses must not include raw_text.")

    @classmethod
    def ok(
        cls,
        *,
        client_name: str,
        availability: CloudPlannerBackendAvailability,
        prompt: CloudPlannerPromptEnvelope,
        raw_text: str,
        status_code: int | None = None,
        response_payload: Mapping[str, object] | None = None,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            client_name=client_name,
            success=True,
            availability=availability,
            prompt=prompt,
            raw_text=raw_text,
            status_code=status_code,
            response_payload=response_payload,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        client_name: str,
        availability: CloudPlannerBackendAvailability,
        error_code: str,
        error_message: str,
        prompt: CloudPlannerPromptEnvelope | None = None,
        status_code: int | None = None,
        response_payload: Mapping[str, object] | None = None,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            client_name=client_name,
            success=False,
            availability=availability,
            prompt=prompt,
            status_code=status_code,
            response_payload=response_payload,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerBackendResult:
    """Failure-safe backend result for prompt -> client -> contract parsing."""

    backend_name: str
    success: bool
    availability: CloudPlannerBackendAvailability
    output_contract: CloudPlannerOutputContract | None = None
    prompt_attempts: tuple[CloudPlannerPromptEnvelope, ...] = ()
    transport_responses: tuple[CloudPlannerTransportResponse, ...] = ()
    correction_attempt_count: int = 0
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.backend_name:
            raise ValueError("backend_name must not be empty.")
        if self.correction_attempt_count < 0:
            raise ValueError("correction_attempt_count must not be negative.")
        if self.success and self.output_contract is None:
            raise ValueError("Successful backend results must include output_contract.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed backend results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful backend results must not include error details.")
        if not self.success and self.output_contract is not None:
            raise ValueError("Failed backend results must not include output_contract.")

    @classmethod
    def ok(
        cls,
        *,
        backend_name: str,
        availability: CloudPlannerBackendAvailability,
        output_contract: CloudPlannerOutputContract,
        prompt_attempts: tuple[CloudPlannerPromptEnvelope, ...],
        transport_responses: tuple[CloudPlannerTransportResponse, ...],
        correction_attempt_count: int,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            backend_name=backend_name,
            success=True,
            availability=availability,
            output_contract=output_contract,
            prompt_attempts=prompt_attempts,
            transport_responses=transport_responses,
            correction_attempt_count=correction_attempt_count,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        backend_name: str,
        availability: CloudPlannerBackendAvailability,
        error_code: str,
        error_message: str,
        prompt_attempts: tuple[CloudPlannerPromptEnvelope, ...] = (),
        transport_responses: tuple[CloudPlannerTransportResponse, ...] = (),
        correction_attempt_count: int = 0,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            backend_name=backend_name,
            success=False,
            availability=availability,
            prompt_attempts=prompt_attempts,
            transport_responses=transport_responses,
            correction_attempt_count=correction_attempt_count,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerExecutionResult:
    """End-to-end result for scaffolded request -> planner backend -> safe bind."""

    planner_name: str
    success: bool
    availability: CloudPlannerBackendAvailability
    request: CloudPlannerRequest | None = None
    backend_result: CloudPlannerBackendResult | None = None
    response_bind_result: CloudPlannerResponseBindResult | None = None
    response: CloudPlannerBoundResponse | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.planner_name:
            raise ValueError("planner_name must not be empty.")
        if self.success and (
            self.request is None
            or self.backend_result is None
            or self.response_bind_result is None
            or self.response is None
        ):
            raise ValueError(
                "Successful execution results must include request, backend_result, response_bind_result, and response."
            )
        if not self.success and self.error_code is None:
            raise ValueError("Failed execution results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful execution results must not include error details.")

    @classmethod
    def ok(
        cls,
        *,
        planner_name: str,
        availability: CloudPlannerBackendAvailability,
        request: CloudPlannerRequest,
        backend_result: CloudPlannerBackendResult,
        response_bind_result: CloudPlannerResponseBindResult,
        response: CloudPlannerBoundResponse,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            planner_name=planner_name,
            success=True,
            availability=availability,
            request=request,
            backend_result=backend_result,
            response_bind_result=response_bind_result,
            response=response,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        planner_name: str,
        availability: CloudPlannerBackendAvailability,
        error_code: str,
        error_message: str,
        request: CloudPlannerRequest | None = None,
        backend_result: CloudPlannerBackendResult | None = None,
        response_bind_result: CloudPlannerResponseBindResult | None = None,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            planner_name=planner_name,
            success=False,
            availability=availability,
            request=request,
            backend_result=backend_result,
            response_bind_result=response_bind_result,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


class _UrlopenLike(Protocol):
    def __call__(
        self,
        url: str | urllib_request.Request,
        data: bytes | None = None,
        timeout: float | object = ...,
    ) -> Any:
        ...


class ObserveOnlyOpenAiCompatibleCloudPlannerClient:
    """Minimal OpenAI-compatible chat-completions client using the standard library."""

    client_name = "ObserveOnlyOpenAiCompatibleCloudPlannerClient"

    def __init__(
        self,
        *,
        config: CloudPlannerClientConfig | None = None,
        urlopen: _UrlopenLike | None = None,
    ) -> None:
        self._config = CloudPlannerClientConfig() if config is None else config
        self._urlopen = urllib_request.urlopen if urlopen is None else urlopen

    @property
    def availability(self) -> CloudPlannerBackendAvailability:
        """Return the explicit client availability based on configuration."""

        if (
            self._config.endpoint_url
            and self._config.model
            and self._config.resolved_api_key()
        ):
            return CloudPlannerBackendAvailability.available
        return CloudPlannerBackendAvailability.unavailable

    @property
    def config(self) -> CloudPlannerClientConfig:
        """Expose the current client config."""

        return self._config

    def complete(
        self,
        prompt: CloudPlannerPromptEnvelope,
    ) -> CloudPlannerTransportResponse:
        availability = self.availability
        if availability is not CloudPlannerBackendAvailability.available:
            return CloudPlannerTransportResponse.failure(
                client_name=self.client_name,
                availability=availability,
                prompt=prompt,
                error_code="cloud_planner_backend_unavailable",
                error_message=(
                    "The cloud planner backend is unavailable because endpoint_url, model, or API key is missing."
                ),
                details={
                    "endpoint_configured": self._config.endpoint_url is not None,
                    "model_configured": self._config.model is not None,
                    "api_key_configured": self._config.resolved_api_key() is not None,
                },
            )

        request_payload = {
            "model": self._config.model,
            "temperature": self._config.temperature,
            "response_format": {"type": "json_object"},
            "messages": (
                {"role": "system", "content": prompt.system_prompt},
                {"role": "user", "content": prompt.user_prompt},
            ),
        }
        body = json.dumps(
            request_payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._config.resolved_api_key()}",
            "Content-Type": "application/json",
            **dict(self._config.extra_headers),
        }
        http_request = urllib_request.Request(
            url=cast(str, self._config.endpoint_url),
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            response = self._urlopen(http_request, timeout=self._config.timeout_seconds)
            with cast(IO[bytes], response) as http_response:
                raw_body = http_response.read()
                status_code = getattr(http_response, "status", None)
        except urllib_error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            return CloudPlannerTransportResponse.failure(
                client_name=self.client_name,
                availability=availability,
                prompt=prompt,
                status_code=exc.code,
                error_code="cloud_planner_transport_http_error",
                error_message=f"Cloud planner HTTP request failed with status {exc.code}.",
                details={"response_excerpt": error_body[:400]},
            )
        except urllib_error.URLError as exc:
            return CloudPlannerTransportResponse.failure(
                client_name=self.client_name,
                availability=availability,
                prompt=prompt,
                error_code="cloud_planner_transport_unavailable",
                error_message=str(exc.reason),
                details={"exception_type": type(exc).__name__},
            )
        except Exception as exc:  # noqa: BLE001 - client must remain failure-safe
            return CloudPlannerTransportResponse.failure(
                client_name=self.client_name,
                availability=availability,
                prompt=prompt,
                error_code="cloud_planner_client_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        try:
            decoded_body = raw_body.decode("utf-8", errors="replace")
            parsed_payload = json.loads(decoded_body)
        except json.JSONDecodeError:
            decoded_body = raw_body.decode("utf-8", errors="replace")
            parsed_payload = None

        raw_text = _extract_response_text(parsed_payload, decoded_body)
        if raw_text is None:
            return CloudPlannerTransportResponse.failure(
                client_name=self.client_name,
                availability=availability,
                prompt=prompt,
                status_code=status_code,
                response_payload=(
                    None if not isinstance(parsed_payload, Mapping) else parsed_payload
                ),
                error_code="cloud_planner_transport_response_unreadable",
                error_message="Cloud planner response did not contain readable structured content.",
            )
        if len(raw_text) > self._config.max_response_characters:
            return CloudPlannerTransportResponse.failure(
                client_name=self.client_name,
                availability=availability,
                prompt=prompt,
                status_code=status_code,
                response_payload=(
                    None if not isinstance(parsed_payload, Mapping) else parsed_payload
                ),
                error_code="cloud_planner_transport_response_too_large",
                error_message="Cloud planner response exceeded the configured size limit.",
                details={"response_length": len(raw_text)},
            )
        return CloudPlannerTransportResponse.ok(
            client_name=self.client_name,
            availability=availability,
            prompt=prompt,
            raw_text=raw_text,
            status_code=status_code,
            response_payload=(
                None if not isinstance(parsed_payload, Mapping) else parsed_payload
            ),
            details={
                "provider_name": self._config.provider_name,
                "response_length": len(raw_text),
            },
        )


class ObserveOnlyClientBackedCloudPlannerBackend:
    """Run prompt construction, cloud client completion, parsing, and correction safely."""

    backend_name = "ObserveOnlyClientBackedCloudPlannerBackend"

    def __init__(
        self,
        *,
        prompt_engine: ObserveOnlyCloudPlannerPromptEngine | None = None,
        client: ObserveOnlyOpenAiCompatibleCloudPlannerClient | None = None,
    ) -> None:
        self._prompt_engine = (
            ObserveOnlyCloudPlannerPromptEngine()
            if prompt_engine is None
            else prompt_engine
        )
        self._client = (
            ObserveOnlyOpenAiCompatibleCloudPlannerClient()
            if client is None
            else client
        )

    @property
    def availability(self) -> CloudPlannerBackendAvailability:
        """Return the current backend availability."""

        return self._client.availability

    def plan(
        self,
        request: CloudPlannerRequest,
    ) -> CloudPlannerBackendResult:
        if self.availability is not CloudPlannerBackendAvailability.available:
            return CloudPlannerBackendResult.failure(
                backend_name=self.backend_name,
                availability=self.availability,
                error_code="cloud_planner_backend_unavailable",
                error_message="The cloud planner backend is unavailable.",
                details={"request_id": request.request_id},
            )

        prompt_attempts: list[CloudPlannerPromptEnvelope] = []
        transport_responses: list[CloudPlannerTransportResponse] = []
        correction_feedback: str | None = None
        last_parse_error: _PlannerResponseParseError | None = None

        for attempt_index in range(1, self._client.config.max_correction_retries + 2):
            prompt_result = self._prompt_engine.build_prompt(
                request,
                attempt_index=attempt_index,
                correction_feedback=correction_feedback,
            )
            if not prompt_result.success or prompt_result.prompt is None:
                return CloudPlannerBackendResult.failure(
                    backend_name=self.backend_name,
                    availability=self.availability,
                    error_code="cloud_planner_prompt_build_failed",
                    error_message=(
                        "Cloud planner prompt construction failed."
                        if prompt_result.error_message is None
                        else prompt_result.error_message
                    ),
                    correction_attempt_count=attempt_index - 1,
                    details=dict(prompt_result.details),
                )
            prompt_attempts.append(prompt_result.prompt)

            try:
                transport_response = self._client.complete(prompt_result.prompt)
            except Exception as exc:  # noqa: BLE001 - backend must remain failure-safe
                return CloudPlannerBackendResult.failure(
                    backend_name=self.backend_name,
                    availability=self.availability,
                    error_code="cloud_planner_client_exception",
                    error_message=str(exc),
                    prompt_attempts=tuple(prompt_attempts),
                    transport_responses=tuple(transport_responses),
                    correction_attempt_count=attempt_index - 1,
                    details={"exception_type": type(exc).__name__},
                )
            transport_responses.append(transport_response)
            if not transport_response.success or transport_response.raw_text is None:
                return CloudPlannerBackendResult.failure(
                    backend_name=self.backend_name,
                    availability=transport_response.availability,
                    error_code=(
                        "cloud_planner_transport_failed"
                        if transport_response.error_code is None
                        else transport_response.error_code
                    ),
                    error_message=(
                        "Cloud planner transport failed."
                        if transport_response.error_message is None
                        else transport_response.error_message
                    ),
                    prompt_attempts=tuple(prompt_attempts),
                    transport_responses=tuple(transport_responses),
                    correction_attempt_count=attempt_index - 1,
                    details=dict(transport_response.details),
                )

            try:
                output_contract = _parse_output_contract(
                    request=request,
                    raw_text=transport_response.raw_text,
                    attempt_index=attempt_index,
                )
            except _PlannerResponseParseError as exc:
                last_parse_error = exc
                if attempt_index <= self._client.config.max_correction_retries:
                    correction_feedback = _correction_feedback(
                        parse_error=exc,
                        raw_text=transport_response.raw_text,
                        max_characters=self._client.config.max_correction_feedback_characters,
                    )
                    continue
                error_code = (
                    exc.code
                    if self._client.config.max_correction_retries == 0
                    else "cloud_planner_response_retry_exhausted"
                )
                error_message = (
                    str(exc)
                    if error_code == exc.code
                    else "Cloud planner correction retries were exhausted."
                )
                return CloudPlannerBackendResult.failure(
                    backend_name=self.backend_name,
                    availability=transport_response.availability,
                    error_code=error_code,
                    error_message=error_message,
                    prompt_attempts=tuple(prompt_attempts),
                    transport_responses=tuple(transport_responses),
                    correction_attempt_count=attempt_index - 1,
                    details={
                        "last_error_code": exc.code,
                        "field_path": exc.field_path,
                        "attempt_index": attempt_index,
                        **exc.details,
                    },
                )

            return CloudPlannerBackendResult.ok(
                backend_name=self.backend_name,
                availability=transport_response.availability,
                output_contract=output_contract,
                prompt_attempts=tuple(prompt_attempts),
                transport_responses=tuple(transport_responses),
                correction_attempt_count=attempt_index - 1,
                details={
                    "outcome": output_contract.outcome.value,
                    "rationale_code": output_contract.rationale_code.value,
                    "attempt_count": attempt_index,
                },
            )

        assert last_parse_error is not None  # pragma: no cover - loop always returns above
        return CloudPlannerBackendResult.failure(
            backend_name=self.backend_name,
            availability=self.availability,
            error_code="cloud_planner_response_retry_exhausted",
            error_message="Cloud planner correction retries were exhausted.",
            prompt_attempts=tuple(prompt_attempts),
            transport_responses=tuple(transport_responses),
            correction_attempt_count=len(prompt_attempts) - 1,
            details={"last_error_code": last_parse_error.code},
        )


class ObserveOnlyBackendBackedCloudPlanner:
    """Run scaffold building, cloud planner client, and safe response binding."""

    planner_name = "ObserveOnlyBackendBackedCloudPlanner"

    def __init__(
        self,
        *,
        scaffolder: ObserveOnlyCloudPlannerScaffolder | None = None,
        backend: ObserveOnlyClientBackedCloudPlannerBackend | None = None,
    ) -> None:
        self._scaffolder = (
            ObserveOnlyCloudPlannerScaffolder()
            if scaffolder is None
            else scaffolder
        )
        self._backend = (
            ObserveOnlyClientBackedCloudPlannerBackend()
            if backend is None
            else backend
        )

    def plan(
        self,
        snapshot: SemanticStateSnapshot,
        exposure_view: CandidateExposureView,
        *,
        user_objective_summary: str,
        request_id: str,
        scenario_definition: ScenarioDefinition | None = None,
        verification_result: VerificationResult | None = None,
        action_scaffold_view: ActionIntentScaffoldView | None = None,
        escalation_decision: DeterministicEscalationDecision | None = None,
    ) -> CloudPlannerExecutionResult:
        try:
            request_result = self._scaffolder.build_request(
                snapshot,
                exposure_view,
                user_objective_summary=user_objective_summary,
                request_id=request_id,
                scenario_definition=scenario_definition,
                verification_result=verification_result,
                action_scaffold_view=action_scaffold_view,
                escalation_decision=escalation_decision,
            )
        except Exception as exc:  # noqa: BLE001 - wrapper must remain failure-safe
            return CloudPlannerExecutionResult.failure(
                planner_name=self.planner_name,
                availability=self._backend.availability,
                error_code="cloud_planner_request_build_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        if not request_result.success or request_result.request is None:
            return CloudPlannerExecutionResult.failure(
                planner_name=self.planner_name,
                availability=self._backend.availability,
                error_code=(
                    "cloud_planner_request_build_failed"
                    if request_result.error_code is None
                    else request_result.error_code
                ),
                error_message=(
                    "Cloud planner request construction failed."
                    if request_result.error_message is None
                    else request_result.error_message
                ),
                details=dict(request_result.details),
            )
        return self.plan_request(request_result.request)

    def plan_request(
        self,
        request: CloudPlannerRequest,
    ) -> CloudPlannerExecutionResult:
        try:
            backend_result = self._backend.plan(request)
        except Exception as exc:  # noqa: BLE001 - wrapper must remain failure-safe
            return CloudPlannerExecutionResult.failure(
                planner_name=self.planner_name,
                availability=self._backend.availability,
                request=request,
                error_code="cloud_planner_backend_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        if not backend_result.success or backend_result.output_contract is None:
            return CloudPlannerExecutionResult.failure(
                planner_name=self.planner_name,
                availability=backend_result.availability,
                request=request,
                backend_result=backend_result,
                error_code=(
                    "cloud_planner_backend_failed"
                    if backend_result.error_code is None
                    else backend_result.error_code
                ),
                error_message=(
                    "Cloud planner backend failed."
                    if backend_result.error_message is None
                    else backend_result.error_message
                ),
                details=dict(backend_result.details),
            )

        try:
            response_bind_result = self._scaffolder.bind_response(
                request,
                contract=backend_result.output_contract,
            )
        except Exception as exc:  # noqa: BLE001 - wrapper must remain failure-safe
            return CloudPlannerExecutionResult.failure(
                planner_name=self.planner_name,
                availability=backend_result.availability,
                request=request,
                backend_result=backend_result,
                error_code="cloud_planner_response_bind_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        if not response_bind_result.success or response_bind_result.response is None:
            return CloudPlannerExecutionResult.failure(
                planner_name=self.planner_name,
                availability=backend_result.availability,
                request=request,
                backend_result=backend_result,
                response_bind_result=response_bind_result,
                error_code=(
                    "cloud_planner_response_bind_failed"
                    if response_bind_result.error_code is None
                    else response_bind_result.error_code
                ),
                error_message=(
                    "Cloud planner response binding failed."
                    if response_bind_result.error_message is None
                    else response_bind_result.error_message
                ),
                details=dict(response_bind_result.details),
            )

        return CloudPlannerExecutionResult.ok(
            planner_name=self.planner_name,
            availability=backend_result.availability,
            request=request,
            backend_result=backend_result,
            response_bind_result=response_bind_result,
            response=response_bind_result.response,
            details={
                "outcome": response_bind_result.response.outcome.value,
                "signal_status": response_bind_result.response.signal_status.value,
                "correction_attempt_count": backend_result.correction_attempt_count,
            },
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class _PlannerResponseParseError(Exception):
    code: str
    message: str
    field_path: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __str__(self) -> str:
        if self.field_path is None:
            return self.message
        return f"{self.message} (field: {self.field_path})"


def _correction_feedback(
    *,
    parse_error: _PlannerResponseParseError,
    raw_text: str,
    max_characters: int,
) -> str:
    excerpt = raw_text[:max_characters]
    return (
        "The previous JSON response could not be accepted. "
        f"error_code={parse_error.code}; "
        f"field_path={parse_error.field_path or '<root>'}; "
        f"message={parse_error.message}; "
        "Return one corrected JSON object only. "
        f"previous_response_excerpt={excerpt}"
    )


def _parse_output_contract(
    *,
    request: CloudPlannerRequest,
    raw_text: str,
    attempt_index: int,
) -> CloudPlannerOutputContract:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise _PlannerResponseParseError(
            code="cloud_planner_response_malformed",
            message="Cloud planner response was not valid JSON.",
            details={"json_error": str(exc)},
        ) from exc
    if not isinstance(payload, dict):
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message="Cloud planner response root must be a JSON object.",
            field_path="$",
        )

    summary = _required_string(payload, "summary")
    outcome = _required_enum(payload, "outcome", CloudPlannerOutcome)
    rationale_code = _required_enum(payload, "rationale_code", CloudPlannerRationaleCode)
    need_more_context = _optional_bool(payload, "need_more_context", default=False)
    forbidden_actions = _optional_enum_tuple(
        payload,
        "forbidden_actions",
        CloudPlannerForbiddenActionLabel,
        default=tuple(label for label in CloudPlannerForbiddenActionLabel),
    )
    fallback_plan = _optional_fallback_plan(payload, "fallback_plan")
    escalation_recommendation = _optional_escalation_recommendation(
        payload,
        "escalation_recommendation",
    )
    response_id = _optional_string(payload, "response_id")
    metadata = _optional_mapping(payload, "metadata", default={})

    if outcome is CloudPlannerOutcome.planned:
        normalized_goal = _required_string(payload, "normalized_goal")
        success_criteria = _parse_success_criteria(payload, "success_criteria")
        success_criteria_by_id = {
            criterion.criterion_id: criterion for criterion in success_criteria
        }
        subgoals = _parse_subgoals(
            payload=payload,
            field_name="subgoals",
            request=request,
            success_criteria_by_id=success_criteria_by_id,
        )
    else:
        normalized_goal = None
        success_criteria = ()
        subgoals = ()

    try:
        return CloudPlannerOutputContract(
            response_id=(
                f"{request.request_id}:planner_response:attempt_{attempt_index}"
                if response_id is None
                else response_id
            ),
            request_id=request.request_id,
            summary=summary,
            outcome=outcome,
            rationale_code=rationale_code,
            normalized_goal=normalized_goal,
            subgoals=subgoals,
            success_criteria=success_criteria,
            forbidden_actions=forbidden_actions,
            fallback_plan=fallback_plan,
            escalation_recommendation=escalation_recommendation,
            need_more_context=need_more_context,
            metadata={
                **dict(metadata),
                "client_parsed": True,
                "parser_attempt_index": attempt_index,
                "boundary_validation_required": True,
                "tool_boundary_required": True,
                "observe_only": True,
                "read_only": True,
                "non_executing": True,
            },
        )
    except Exception as exc:
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message=str(exc),
        ) from exc


def _parse_subgoals(
    *,
    payload: Mapping[str, object],
    field_name: str,
    request: CloudPlannerRequest,
    success_criteria_by_id: Mapping[str, CloudPlannerSuccessCriterion],
) -> tuple[CloudPlannerSubgoal, ...]:
    raw_values = _required_sequence(payload, field_name)
    allowed_candidate_ids = {
        entry.candidate_binding.candidate_id: entry for entry in request.candidate_summary
    }
    subgoals: list[CloudPlannerSubgoal] = []
    for index, raw_value in enumerate(raw_values):
        path = f"{field_name}[{index}]"
        item = _require_mapping(raw_value, path)
        candidate_id = _optional_string(item, "candidate_id")
        if candidate_id is not None and candidate_id not in allowed_candidate_ids:
            raise _PlannerResponseParseError(
                code="cloud_planner_response_schema_invalid",
                message="Planner subgoal candidate_id must reference a candidate from the request.",
                field_path=f"{path}.candidate_id",
            )
        success_criterion_ids = _optional_string_tuple(
            item,
            "success_criterion_ids",
            default=(),
        )
        missing_criterion_ids = tuple(
            criterion_id
            for criterion_id in success_criterion_ids
            if criterion_id not in success_criteria_by_id
        )
        if missing_criterion_ids:
            raise _PlannerResponseParseError(
                code="cloud_planner_response_schema_invalid",
                message="Planner subgoal referenced unknown success criteria.",
                field_path=f"{path}.success_criterion_ids",
                details={"missing_criterion_ids": missing_criterion_ids},
            )
        candidate_label = _optional_enum(item, "candidate_label", SharedCandidateLabel)
        target_label = _optional_enum(item, "target_label", SharedTargetLabel)
        if candidate_id is not None and target_label is not None:
            allowed_target_labels = allowed_candidate_ids[candidate_id].candidate_binding.allowed_target_labels
            if target_label not in allowed_target_labels:
                raise _PlannerResponseParseError(
                    code="cloud_planner_response_schema_invalid",
                    message="Planner subgoal target_label is not allowed for the referenced candidate.",
                    field_path=f"{path}.target_label",
                )
        try:
            subgoals.append(
                CloudPlannerSubgoal(
                    subgoal_id=_required_string(item, "subgoal_id"),
                    summary=_required_string(item, "summary"),
                    action_type=_required_enum(item, "action_type", AiSuggestedActionType),
                    candidate_id=candidate_id,
                    candidate_label=candidate_label,
                    target_label=target_label,
                    success_criterion_ids=success_criterion_ids,
                    dry_run_only=_optional_bool(item, "dry_run_only", default=True),
                    metadata=_optional_mapping(item, "metadata", default={}),
                )
            )
        except Exception as exc:
            raise _PlannerResponseParseError(
                code="cloud_planner_response_schema_invalid",
                message=str(exc),
                field_path=path,
            ) from exc
    return tuple(subgoals)


def _parse_success_criteria(
    payload: Mapping[str, object],
    field_name: str,
) -> tuple[CloudPlannerSuccessCriterion, ...]:
    raw_values = _optional_sequence(payload, field_name, default=())
    criteria: list[CloudPlannerSuccessCriterion] = []
    for index, raw_value in enumerate(raw_values):
        path = f"{field_name}[{index}]"
        item = _require_mapping(raw_value, path)
        expectation_payload = _require_mapping(item.get("expectation"), f"{path}.expectation")
        try:
            criteria.append(
                CloudPlannerSuccessCriterion(
                    criterion_id=_required_string(item, "criterion_id"),
                    summary=_required_string(item, "summary"),
                    expectation=_parse_expectation(
                        expectation_payload,
                        path=f"{path}.expectation",
                    ),
                    metadata=_optional_mapping(item, "metadata", default={}),
                )
            )
        except Exception as exc:
            raise _PlannerResponseParseError(
                code="cloud_planner_response_schema_invalid",
                message=str(exc),
                field_path=path,
            ) from exc
    return tuple(criteria)


def _parse_expectation(
    payload: Mapping[str, object],
    *,
    path: str,
) -> SemanticTransitionExpectation:
    expected_outcomes = tuple(
        _parse_expected_outcome(
            _require_mapping(raw_value, f"{path}.expected_outcomes[{index}]"),
            path=f"{path}.expected_outcomes[{index}]",
        )
        for index, raw_value in enumerate(
            _optional_sequence(payload, "expected_outcomes", default=())
        )
    )
    alternate_outcome_branches = tuple(
        _parse_outcome_branch(
            _require_mapping(raw_value, f"{path}.alternate_outcome_branches[{index}]"),
            path=f"{path}.alternate_outcome_branches[{index}]",
        )
        for index, raw_value in enumerate(
            _optional_sequence(payload, "alternate_outcome_branches", default=())
        )
    )
    timing_payload = _optional_mapping(payload, "timing", default=None)
    timing = None
    if timing_payload is not None:
        try:
            timing = VerificationTimingPolicy(
                timeout_seconds=_optional_float(timing_payload, "timeout_seconds"),
                poll_interval_ms=_optional_int(timing_payload, "poll_interval_ms"),
                max_poll_attempts=_optional_int(timing_payload, "max_poll_attempts"),
            )
        except Exception as exc:
            raise _PlannerResponseParseError(
                code="cloud_planner_response_schema_invalid",
                message=str(exc),
                field_path=f"{path}.timing",
            ) from exc
    return SemanticTransitionExpectation(
        summary=_required_string(payload, "summary"),
        required_candidate_ids=_optional_string_tuple(
            payload,
            "required_candidate_ids",
            default=(),
        ),
        forbidden_candidate_ids=_optional_string_tuple(
            payload,
            "forbidden_candidate_ids",
            default=(),
        ),
        required_node_ids=_optional_string_tuple(payload, "required_node_ids", default=()),
        expected_outcomes=expected_outcomes,
        alternate_outcome_branches=alternate_outcome_branches,
        timing=timing,
    )


def _parse_outcome_branch(
    payload: Mapping[str, object],
    *,
    path: str,
) -> VerificationOutcomeBranch:
    expected_outcomes = tuple(
        _parse_expected_outcome(
            _require_mapping(raw_value, f"{path}.expected_outcomes[{index}]"),
            path=f"{path}.expected_outcomes[{index}]",
        )
        for index, raw_value in enumerate(_required_sequence(payload, "expected_outcomes"))
    )
    return VerificationOutcomeBranch(
        branch_id=_required_string(payload, "branch_id"),
        summary=_required_string(payload, "summary"),
        expected_outcomes=expected_outcomes,
    )


def _parse_expected_outcome(
    payload: Mapping[str, object],
    *,
    path: str,
) -> ExpectedSemanticOutcome:
    try:
        return ExpectedSemanticOutcome(
            outcome_id=_required_string(payload, "outcome_id"),
            category=_required_enum(payload, "category", SemanticDeltaCategory),
            item_id=_required_string(payload, "item_id"),
            expected_change=_required_enum(
                payload,
                "expected_change",
                ExpectedSemanticChange,
            ),
            required_changed_fields=_optional_string_tuple(
                payload,
                "required_changed_fields",
                default=(),
            ),
            expected_before_state=_optional_mapping(
                payload,
                "expected_before_state",
                default={},
            ),
            expected_after_state=_optional_mapping(
                payload,
                "expected_after_state",
                default={},
            ),
            minimum_score_delta=_optional_float(payload, "minimum_score_delta"),
            score_delta_direction=_optional_enum(
                payload,
                "score_delta_direction",
                CandidateScoreDeltaDirection,
                default=CandidateScoreDeltaDirection.any_change,
            ),
            summary=_optional_string(payload, "summary"),
        )
    except Exception as exc:
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message=str(exc),
            field_path=path,
        ) from exc


def _optional_fallback_plan(
    payload: Mapping[str, object],
    field_name: str,
) -> CloudPlannerFallbackPlan | None:
    raw_value = payload.get(field_name)
    if raw_value is None:
        return None
    item = _require_mapping(raw_value, field_name)
    return CloudPlannerFallbackPlan(
        summary=_required_string(item, "summary"),
        recommended_disposition=_required_enum(
            item,
            "recommended_disposition",
            DeterministicEscalationDisposition,
        ),
        reason_codes=_optional_enum_tuple(
            item,
            "reason_codes",
            DeterministicEscalationReason,
            default=(),
        ),
        metadata=_optional_mapping(item, "metadata", default={}),
    )


def _optional_escalation_recommendation(
    payload: Mapping[str, object],
    field_name: str,
) -> CloudPlannerEscalationRecommendation | None:
    raw_value = payload.get(field_name)
    if raw_value is None:
        return None
    item = _require_mapping(raw_value, field_name)
    return CloudPlannerEscalationRecommendation(
        summary=_required_string(item, "summary"),
        recommended_disposition=_required_enum(
            item,
            "recommended_disposition",
            DeterministicEscalationDisposition,
        ),
        recommended_source=_optional_enum(
            item,
            "recommended_source",
            ArbitrationSource,
        ),
        reason_codes=_optional_enum_tuple(
            item,
            "reason_codes",
            DeterministicEscalationReason,
            default=(),
        ),
        metadata=_optional_mapping(item, "metadata", default={}),
    )


def _extract_response_text(
    parsed_payload: object,
    decoded_body: str,
) -> str | None:
    if isinstance(parsed_payload, Mapping):
        if "summary" in parsed_payload and "outcome" in parsed_payload:
            return json.dumps(parsed_payload, ensure_ascii=False, separators=(",", ":"))
        direct_text = parsed_payload.get("output_text")
        if isinstance(direct_text, str) and direct_text.strip():
            return direct_text
        direct_content = parsed_payload.get("content")
        if isinstance(direct_content, str) and direct_content.strip():
            return direct_content
        choices = parsed_payload.get("choices")
        if isinstance(choices, list) and choices:
            choice = choices[0]
            if isinstance(choice, Mapping):
                message = choice.get("message")
                if isinstance(message, Mapping):
                    content_text = _text_from_content_payload(message.get("content"))
                    if content_text is not None:
                        return content_text
        output = parsed_payload.get("output")
        if isinstance(output, list) and output:
            first_output = output[0]
            if isinstance(first_output, Mapping):
                content_text = _text_from_content_payload(first_output.get("content"))
                if content_text is not None:
                    return content_text
    stripped = decoded_body.strip()
    return stripped or None


def _text_from_content_payload(content: object) -> str | None:
    if isinstance(content, str):
        return content if content.strip() else None
    if isinstance(content, list):
        text_fragments: list[str] = []
        for item in content:
            if isinstance(item, Mapping):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    text_fragments.append(text)
        if text_fragments:
            return "".join(text_fragments)
    return None


def _require_mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message="Expected an object.",
            field_path=path,
        )
    return cast(Mapping[str, object], value)


def _required_string(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message="Expected a non-empty string.",
            field_path=field_name,
        )
    return value.strip()


def _optional_string(payload: Mapping[str, object], field_name: str) -> str | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message="Expected a non-empty string when provided.",
            field_path=field_name,
        )
    return value.strip()


def _required_sequence(payload: Mapping[str, object], field_name: str) -> tuple[object, ...]:
    value = payload.get(field_name)
    if not isinstance(value, list):
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message="Expected an array.",
            field_path=field_name,
        )
    return tuple(value)


def _optional_sequence(
    payload: Mapping[str, object],
    field_name: str,
    *,
    default: tuple[object, ...],
) -> tuple[object, ...]:
    value = payload.get(field_name)
    if value is None:
        return default
    if not isinstance(value, list):
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message="Expected an array when provided.",
            field_path=field_name,
        )
    return tuple(value)


def _optional_mapping(
    payload: Mapping[str, object],
    field_name: str,
    *,
    default: Mapping[str, object] | None,
) -> Mapping[str, object] | None:
    value = payload.get(field_name)
    if value is None:
        return default
    if not isinstance(value, Mapping):
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message="Expected an object when provided.",
            field_path=field_name,
        )
    return cast(Mapping[str, object], value)


def _required_enum(payload, field_name, enum_type):
    raw_value = _required_string(payload, field_name)
    try:
        return enum_type(raw_value)
    except ValueError as exc:
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message=f"Expected one of {[item.value for item in enum_type]}.",
            field_path=field_name,
        ) from exc


def _optional_enum(payload, field_name, enum_type, *, default=None):
    raw_value = payload.get(field_name)
    if raw_value is None:
        return default
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message="Expected a non-empty enum value when provided.",
            field_path=field_name,
        )
    try:
        return enum_type(raw_value.strip())
    except ValueError as exc:
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message=f"Expected one of {[item.value for item in enum_type]}.",
            field_path=field_name,
        ) from exc


def _optional_enum_tuple(payload, field_name, enum_type, *, default):
    raw_values = payload.get(field_name)
    if raw_values is None:
        return default
    if not isinstance(raw_values, list):
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message="Expected an array when provided.",
            field_path=field_name,
        )
    values = []
    for index, raw_value in enumerate(raw_values):
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise _PlannerResponseParseError(
                code="cloud_planner_response_schema_invalid",
                message="Expected a non-empty enum value.",
                field_path=f"{field_name}[{index}]",
            )
        try:
            values.append(enum_type(raw_value.strip()))
        except ValueError as exc:
            raise _PlannerResponseParseError(
                code="cloud_planner_response_schema_invalid",
                message=f"Expected one of {[item.value for item in enum_type]}.",
                field_path=f"{field_name}[{index}]",
            ) from exc
    return tuple(values)


def _optional_string_tuple(
    payload: Mapping[str, object],
    field_name: str,
    *,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    raw_values = payload.get(field_name)
    if raw_values is None:
        return default
    if not isinstance(raw_values, list):
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message="Expected an array when provided.",
            field_path=field_name,
        )
    values: list[str] = []
    for index, raw_value in enumerate(raw_values):
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise _PlannerResponseParseError(
                code="cloud_planner_response_schema_invalid",
                message="Expected a non-empty string.",
                field_path=f"{field_name}[{index}]",
            )
        values.append(raw_value.strip())
    return tuple(values)


def _optional_bool(
    payload: Mapping[str, object],
    field_name: str,
    *,
    default: bool,
) -> bool:
    raw_value = payload.get(field_name)
    if raw_value is None:
        return default
    if not isinstance(raw_value, bool):
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message="Expected a boolean when provided.",
            field_path=field_name,
        )
    return raw_value


def _optional_float(
    payload: Mapping[str, object],
    field_name: str,
) -> float | None:
    raw_value = payload.get(field_name)
    if raw_value is None:
        return None
    if not isinstance(raw_value, int | float) or isinstance(raw_value, bool):
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message="Expected a number when provided.",
            field_path=field_name,
        )
    return float(raw_value)


def _optional_int(
    payload: Mapping[str, object],
    field_name: str,
) -> int | None:
    raw_value = payload.get(field_name)
    if raw_value is None:
        return None
    if not isinstance(raw_value, int) or isinstance(raw_value, bool):
        raise _PlannerResponseParseError(
            code="cloud_planner_response_schema_invalid",
            message="Expected an integer when provided.",
            field_path=field_name,
        )
    return raw_value
