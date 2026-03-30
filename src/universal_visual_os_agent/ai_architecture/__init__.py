"""AI architecture scaffolding exports."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

_EXPORT_MODULES = {
    ".arbitration": (
        "ArbitrationConflict",
        "ArbitrationConflictKind",
        "ArbitrationEvaluationResult",
        "ArbitrationOutcome",
        "ArbitrationSource",
        "ArbitrationStatus",
        "EscalationAction",
        "EscalationDecision",
        "EscalationPolicy",
        "ObserveOnlyAiArbitrator",
        "ObserveOnlyEscalationPolicyDecider",
    ),
    ".contracts": (
        "AI_ARCHITECTURE_SCHEMA_VERSION",
        "AiArchitectureSignalStatus",
        "ObserveOnlyPlannerContractBuilder",
        "ObserveOnlyResolverContractBuilder",
        "PlannerRequestBuildResult",
        "PlannerRequestContract",
        "PlannerResponseBindResult",
        "PlannerResponseContract",
        "ResolverRequestBuildResult",
        "ResolverRequestContract",
        "ResolverResponseBindResult",
        "ResolverResponseContract",
    ),
    ".cloud_planner": (
        "CloudPlannerBoundResponse",
        "CloudPlannerBoundSubgoal",
        "CloudPlannerCandidateSummaryEntry",
        "CloudPlannerEscalationContext",
        "CloudPlannerEscalationRecommendation",
        "CloudPlannerFallbackPlan",
        "CloudPlannerForbiddenActionLabel",
        "CloudPlannerOutcome",
        "CloudPlannerOutputContract",
        "CloudPlannerRationaleCode",
        "CloudPlannerRequest",
        "CloudPlannerRequestBuildResult",
        "CloudPlannerResponseBindResult",
        "CloudPlannerScenarioContext",
        "CloudPlannerSubgoal",
        "CloudPlannerSuccessCriterion",
        "CloudPlannerVerificationContext",
        "ObserveOnlyCloudPlannerScaffolder",
    ),
    ".escalation_engine": (
        "DeterministicEscalationDecision",
        "DeterministicEscalationDisposition",
        "DeterministicEscalationEvaluationResult",
        "DeterministicEscalationReason",
        "ObserveOnlyDeterministicEscalationEngine",
    ),
    ".local_visual_resolver": (
        "LocalVisualResolverAmbiguityContext",
        "LocalVisualResolverCropReference",
        "LocalVisualResolverOutputContract",
        "LocalVisualResolverOutcome",
        "LocalVisualResolverRationaleCode",
        "LocalVisualResolverRequest",
        "LocalVisualResolverRequestBuildResult",
        "LocalVisualResolverResponse",
        "LocalVisualResolverResponseBindResult",
        "LocalVisualResolverShortlistEntry",
        "LocalVisualResolverTaskType",
        "ObserveOnlyLocalVisualResolverScaffolder",
    ),
    ".interfaces": (
        "AiArbitrator",
        "CloudPlannerScaffolder",
        "DeterministicEscalationEngine",
        "EscalationPolicyDecider",
        "LocalVisualResolverScaffolder",
        "PlannerContractBuilder",
        "ResolverContractBuilder",
        "SharedOntologyBinder",
    ),
    ".ontology": (
        "SHARED_AI_ONTOLOGY_VERSION",
        "ObserveOnlySharedOntologyBinder",
        "SharedCandidateLabel",
        "SharedCandidateOntologyBinding",
        "SharedOntologyBindingResult",
        "SharedTargetLabel",
    ),
}
_EXPORTS = {
    name: module_name
    for module_name, names in _EXPORT_MODULES.items()
    for name in names
}

__all__ = tuple(name for names in _EXPORT_MODULES.values() for name in names)


def __getattr__(name: str) -> object:
    """Lazily resolve AI architecture exports to keep the facade import-light."""

    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name, __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return a stable view of module globals plus lazy exports."""

    return sorted((*globals(), *__all__))


if TYPE_CHECKING:
    from .arbitration import (
        ArbitrationConflict,
        ArbitrationConflictKind,
        ArbitrationEvaluationResult,
        ArbitrationOutcome,
        ArbitrationSource,
        ArbitrationStatus,
        EscalationAction,
        EscalationDecision,
        EscalationPolicy,
        ObserveOnlyAiArbitrator,
        ObserveOnlyEscalationPolicyDecider,
    )
    from .cloud_planner import (
        CloudPlannerBoundResponse,
        CloudPlannerBoundSubgoal,
        CloudPlannerCandidateSummaryEntry,
        CloudPlannerEscalationContext,
        CloudPlannerEscalationRecommendation,
        CloudPlannerFallbackPlan,
        CloudPlannerForbiddenActionLabel,
        CloudPlannerOutcome,
        CloudPlannerOutputContract,
        CloudPlannerRationaleCode,
        CloudPlannerRequest,
        CloudPlannerRequestBuildResult,
        CloudPlannerResponseBindResult,
        CloudPlannerScenarioContext,
        CloudPlannerSubgoal,
        CloudPlannerSuccessCriterion,
        CloudPlannerVerificationContext,
        ObserveOnlyCloudPlannerScaffolder,
    )
    from .contracts import (
        AI_ARCHITECTURE_SCHEMA_VERSION,
        AiArchitectureSignalStatus,
        ObserveOnlyPlannerContractBuilder,
        ObserveOnlyResolverContractBuilder,
        PlannerRequestBuildResult,
        PlannerRequestContract,
        PlannerResponseBindResult,
        PlannerResponseContract,
        ResolverRequestBuildResult,
        ResolverRequestContract,
        ResolverResponseBindResult,
        ResolverResponseContract,
    )
    from .escalation_engine import (
        DeterministicEscalationDecision,
        DeterministicEscalationDisposition,
        DeterministicEscalationEvaluationResult,
        DeterministicEscalationReason,
        ObserveOnlyDeterministicEscalationEngine,
    )
    from .interfaces import (
        AiArbitrator,
        CloudPlannerScaffolder,
        DeterministicEscalationEngine,
        EscalationPolicyDecider,
        LocalVisualResolverScaffolder,
        PlannerContractBuilder,
        ResolverContractBuilder,
        SharedOntologyBinder,
    )
    from .local_visual_resolver import (
        LocalVisualResolverAmbiguityContext,
        LocalVisualResolverCropReference,
        LocalVisualResolverOutputContract,
        LocalVisualResolverOutcome,
        LocalVisualResolverRationaleCode,
        LocalVisualResolverRequest,
        LocalVisualResolverRequestBuildResult,
        LocalVisualResolverResponse,
        LocalVisualResolverResponseBindResult,
        LocalVisualResolverShortlistEntry,
        LocalVisualResolverTaskType,
        ObserveOnlyLocalVisualResolverScaffolder,
    )
    from .ontology import (
        SHARED_AI_ONTOLOGY_VERSION,
        ObserveOnlySharedOntologyBinder,
        SharedCandidateLabel,
        SharedCandidateOntologyBinding,
        SharedOntologyBindingResult,
        SharedTargetLabel,
    )
