"""Interfaces for shared AI ontology, contracts, arbitration, escalation, and resolver scaffolding."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.ai_architecture.arbitration import (
    ArbitrationConflict,
    ArbitrationEvaluationResult,
    EscalationDecision,
    EscalationPolicy,
)
from universal_visual_os_agent.ai_architecture.contracts import (
    PlannerResponseContract,
    PlannerRequestBuildResult,
    PlannerResponseBindResult,
    ResolverResponseContract,
    ResolverRequestBuildResult,
    ResolverResponseBindResult,
)
from universal_visual_os_agent.ai_architecture.escalation_engine import (
    DeterministicEscalationDecision,
    DeterministicEscalationEvaluationResult,
)
from universal_visual_os_agent.ai_architecture.local_visual_resolver import (
    LocalVisualResolverOutputContract,
    LocalVisualResolverRequest,
    LocalVisualResolverRequestBuildResult,
    LocalVisualResolverResponseBindResult,
    LocalVisualResolverTaskType,
)
from universal_visual_os_agent.ai_architecture.ontology import (
    SharedCandidateLabel,
    SharedCandidateOntologyBinding,
    SharedOntologyBindingResult,
    SharedTargetLabel,
)
from universal_visual_os_agent.ai_boundary.models import (
    CloudPlannerContract,
    LocalVisualResolverContract,
)
from universal_visual_os_agent.semantics.candidate_exposure import (
    CandidateExposureView,
    ExposedCandidate,
)
from universal_visual_os_agent.semantics.state import SemanticCandidate, SemanticStateSnapshot
from universal_visual_os_agent.verification.models import SemanticTransitionExpectation


class SharedOntologyBinder(Protocol):
    """Bind deterministic candidates to the shared AI ontology."""

    def bind_semantic_candidate(
        self,
        candidate: SemanticCandidate,
    ) -> SharedOntologyBindingResult:
        """Return a failure-safe shared-ontology binding result."""

    def bind_exposed_candidate(
        self,
        candidate: ExposedCandidate,
    ) -> SharedOntologyBindingResult:
        """Return a failure-safe shared-ontology binding result."""


class PlannerContractBuilder(Protocol):
    """Build observe-only planner requests and bind planner responses."""

    def build_request(
        self,
        snapshot: SemanticStateSnapshot,
        exposure_view: CandidateExposureView,
        *,
        summary: str,
        request_id: str,
        expected_transition: SemanticTransitionExpectation | None = None,
        scenario_id: str | None = None,
    ) -> PlannerRequestBuildResult:
        """Return a failure-safe planner-request construction result."""

    def bind_response(
        self,
        contract: CloudPlannerContract,
        *,
        exposure_view: CandidateExposureView | None = None,
    ) -> PlannerResponseBindResult:
        """Return a failure-safe planner-response binding result."""


class ResolverContractBuilder(Protocol):
    """Build observe-only resolver requests and bind resolver responses."""

    def build_request(
        self,
        snapshot: SemanticStateSnapshot,
        exposure_view: CandidateExposureView,
        *,
        candidate_id: str,
        summary: str,
        target_label: SharedTargetLabel = SharedTargetLabel.candidate_center,
        request_id: str | None = None,
        scenario_id: str | None = None,
    ) -> ResolverRequestBuildResult:
        """Return a failure-safe resolver-request construction result."""

    def bind_response(
        self,
        contract: LocalVisualResolverContract,
        *,
        exposure_view: CandidateExposureView | None = None,
    ) -> ResolverResponseBindResult:
        """Return a failure-safe resolver-response binding result."""


class EscalationPolicyDecider(Protocol):
    """Choose a conservative next step for hybrid AI arbitration."""

    def decide(
        self,
        *,
        deterministic_binding: SharedCandidateOntologyBinding | None,
        resolver_response: ResolverResponseContract | None = None,
        planner_response: PlannerResponseContract | None = None,
        conflicts: tuple[ArbitrationConflict, ...] = (),
        policy: EscalationPolicy | None = None,
    ) -> EscalationDecision:
        """Return a structured escalation recommendation."""


class DeterministicEscalationEngine(Protocol):
    """Decide the next conservative escalation path without executing anything."""

    def evaluate(
        self,
        *,
        deterministic_binding: SharedCandidateOntologyBinding | None,
        resolver_response: ResolverResponseContract | None = None,
        planner_response: PlannerResponseContract | None = None,
        conflicts: tuple[ArbitrationConflict, ...] = (),
        policy: EscalationPolicy | None = None,
    ) -> DeterministicEscalationEvaluationResult:
        """Return a failure-safe deterministic escalation decision."""


class LocalVisualResolverScaffolder(Protocol):
    """Build and bind future local visual resolver scaffolding safely."""

    def build_request(
        self,
        snapshot: SemanticStateSnapshot,
        exposure_view: CandidateExposureView,
        *,
        candidate_ids: tuple[str, ...],
        summary: str,
        request_id: str,
        task_type: LocalVisualResolverTaskType = LocalVisualResolverTaskType.choose_candidate,
        expected_target_label: SharedTargetLabel = SharedTargetLabel.candidate_center,
        allowed_candidate_labels: tuple[SharedCandidateLabel, ...] = (),
        escalation_decision: DeterministicEscalationDecision | None = None,
        scenario_id: str | None = None,
    ) -> LocalVisualResolverRequestBuildResult:
        """Return a failure-safe local visual resolver request scaffold."""

    def bind_response(
        self,
        request: LocalVisualResolverRequest,
        *,
        contract: LocalVisualResolverOutputContract,
    ) -> LocalVisualResolverResponseBindResult:
        """Return a failure-safe local visual resolver response binding result."""


class AiArbitrator(Protocol):
    """Arbitrate deterministic, local-resolver, and planner signals safely."""

    def arbitrate(
        self,
        *,
        deterministic_binding: SharedCandidateOntologyBinding | None,
        resolver_response: ResolverResponseContract | None = None,
        planner_response: PlannerResponseContract | None = None,
        policy: EscalationPolicy | None = None,
    ) -> ArbitrationEvaluationResult:
        """Return a failure-safe arbitration outcome."""
