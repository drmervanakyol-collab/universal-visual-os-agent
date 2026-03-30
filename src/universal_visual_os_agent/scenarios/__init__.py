"""Scenario-definition contracts."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

_EXPORT_MODULES = {
    ".action_flow": ("ObserveActVerifyScenarioRunner",),
    ".definition": ("SafetyFirstScenarioDefinitionBuilder",),
    ".interfaces": (
        "ScenarioActionRunner",
        "ScenarioDefinitionBuilder",
        "ScenarioRunner",
        "ScenarioStateMachine",
    ),
    ".loop": ("ObserveUnderstandVerifyScenarioRunner",),
    ".models": (
        "ScenarioActionDisposition",
        "ScenarioActionRun",
        "ScenarioActionRunResult",
        "ScenarioActionStepRun",
        "ScenarioActionStepStage",
        "ScenarioCandidateSelectionConstraint",
        "ScenarioDefinition",
        "ScenarioDefinitionResult",
        "ScenarioDefinitionStatus",
        "ScenarioDefinitionView",
        "ScenarioExecutionEligibility",
        "ScenarioRun",
        "ScenarioRunResult",
        "ScenarioRunStatus",
        "ScenarioSafetyRequirement",
        "ScenarioStepDefinition",
        "ScenarioStepRun",
        "ScenarioStepStage",
    ),
    ".state_machine": (
        "InstrumentedScenarioStateMachine",
        "ScenarioFlowState",
        "ScenarioStateMachineTrace",
        "ScenarioStateTransition",
    ),
}
_EXPORTS = {
    name: module_name
    for module_name, names in _EXPORT_MODULES.items()
    for name in names
}

__all__ = tuple(name for names in _EXPORT_MODULES.values() for name in names)


def __getattr__(name: str) -> object:
    """Lazily resolve scenario exports to keep the facade import-light."""

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
    from .action_flow import ObserveActVerifyScenarioRunner
    from .definition import SafetyFirstScenarioDefinitionBuilder
    from .interfaces import (
        ScenarioActionRunner,
        ScenarioDefinitionBuilder,
        ScenarioRunner,
        ScenarioStateMachine,
    )
    from .loop import ObserveUnderstandVerifyScenarioRunner
    from .models import (
        ScenarioActionDisposition,
        ScenarioActionRun,
        ScenarioActionRunResult,
        ScenarioActionStepRun,
        ScenarioActionStepStage,
        ScenarioCandidateSelectionConstraint,
        ScenarioDefinition,
        ScenarioDefinitionResult,
        ScenarioDefinitionStatus,
        ScenarioDefinitionView,
        ScenarioExecutionEligibility,
        ScenarioRun,
        ScenarioRunResult,
        ScenarioRunStatus,
        ScenarioSafetyRequirement,
        ScenarioStepDefinition,
        ScenarioStepRun,
        ScenarioStepStage,
    )
    from .state_machine import (
        InstrumentedScenarioStateMachine,
        ScenarioFlowState,
        ScenarioStateMachineTrace,
        ScenarioStateTransition,
    )
