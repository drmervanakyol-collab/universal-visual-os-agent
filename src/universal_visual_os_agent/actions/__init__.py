"""Action contracts."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

_EXPORT_MODULES = {
    ".interfaces": (
        "ActionExecutor",
        "ActionIntentScaffolder",
        "DryRunActionEngine",
        "RealClickTransport",
        "SafeClickExecutor",
    ),
    ".models": (
        "ActionIntent",
        "ActionIntentReasonCode",
        "ActionIntentStatus",
        "ActionPrecondition",
        "ActionRequirementStatus",
        "ActionResult",
        "ActionSafetyGate",
        "ActionTargetValidation",
    ),
    ".dry_run_models": (
        "DryRunActionBatchResult",
        "DryRunActionCheckOutcome",
        "DryRunActionDisposition",
        "DryRunActionEvaluation",
        "DryRunActionEvaluationResult",
        "DryRunActionEvaluationView",
    ),
    ".dry_run": (
        "ObserveOnlyDryRunActionEngine",
    ),
    ".safe_click": (
        "SafeClickExecution",
        "SafeClickExecutionResult",
        "SafeClickGateOutcome",
        "SafeClickPrototypeExecutor",
        "SafeClickPrototypeStatus",
    ),
    ".scaffolding_models": (
        "ActionIntentScaffoldView",
        "ActionIntentScaffoldingResult",
    ),
    ".scaffolding": (
        "ObserveOnlyActionIntentScaffolder",
    ),
}
_EXPORTS = {
    name: module_name
    for module_name, names in _EXPORT_MODULES.items()
    for name in names
}

__all__ = tuple(name for names in _EXPORT_MODULES.values() for name in names)


def __getattr__(name: str) -> object:
    """Lazily resolve public action exports to reduce package import coupling."""

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
    from .dry_run import ObserveOnlyDryRunActionEngine
    from .dry_run_models import (
        DryRunActionBatchResult,
        DryRunActionCheckOutcome,
        DryRunActionDisposition,
        DryRunActionEvaluation,
        DryRunActionEvaluationResult,
        DryRunActionEvaluationView,
    )
    from .interfaces import (
        ActionExecutor,
        ActionIntentScaffolder,
        DryRunActionEngine,
        RealClickTransport,
        SafeClickExecutor,
    )
    from .models import (
        ActionIntent,
        ActionIntentReasonCode,
        ActionIntentStatus,
        ActionPrecondition,
        ActionRequirementStatus,
        ActionResult,
        ActionSafetyGate,
        ActionTargetValidation,
    )
    from .safe_click import (
        SafeClickExecution,
        SafeClickExecutionResult,
        SafeClickGateOutcome,
        SafeClickPrototypeExecutor,
        SafeClickPrototypeStatus,
    )
    from .scaffolding import ObserveOnlyActionIntentScaffolder
    from .scaffolding_models import (
        ActionIntentScaffoldView,
        ActionIntentScaffoldingResult,
    )
