"""Action contracts."""

from universal_visual_os_agent.actions.dry_run import (
    DryRunActionBatchResult,
    DryRunActionCheckOutcome,
    DryRunActionDisposition,
    DryRunActionEvaluation,
    DryRunActionEvaluationResult,
    DryRunActionEvaluationView,
    ObserveOnlyDryRunActionEngine,
)
from universal_visual_os_agent.actions.interfaces import (
    ActionExecutor,
    ActionIntentScaffolder,
    DryRunActionEngine,
    RealClickTransport,
    SafeClickExecutor,
)
from universal_visual_os_agent.actions.models import (
    ActionIntent,
    ActionIntentReasonCode,
    ActionIntentStatus,
    ActionPrecondition,
    ActionRequirementStatus,
    ActionResult,
    ActionSafetyGate,
    ActionTargetValidation,
)
from universal_visual_os_agent.actions.safe_click import (
    SafeClickExecution,
    SafeClickExecutionResult,
    SafeClickGateOutcome,
    SafeClickPrototypeExecutor,
    SafeClickPrototypeStatus,
)
from universal_visual_os_agent.actions.scaffolding import (
    ActionIntentScaffoldView,
    ActionIntentScaffoldingResult,
    ObserveOnlyActionIntentScaffolder,
)

__all__ = [
    "ActionExecutor",
    "ActionIntent",
    "ActionIntentReasonCode",
    "ActionIntentScaffoldView",
    "ActionIntentScaffolder",
    "ActionIntentScaffoldingResult",
    "ActionIntentStatus",
    "ActionPrecondition",
    "ActionRequirementStatus",
    "ActionResult",
    "ActionSafetyGate",
    "ActionTargetValidation",
    "DryRunActionBatchResult",
    "DryRunActionCheckOutcome",
    "DryRunActionDisposition",
    "DryRunActionEngine",
    "DryRunActionEvaluation",
    "DryRunActionEvaluationResult",
    "DryRunActionEvaluationView",
    "ObserveOnlyActionIntentScaffolder",
    "ObserveOnlyDryRunActionEngine",
    "RealClickTransport",
    "SafeClickExecution",
    "SafeClickExecutionResult",
    "SafeClickExecutor",
    "SafeClickGateOutcome",
    "SafeClickPrototypeExecutor",
    "SafeClickPrototypeStatus",
]
