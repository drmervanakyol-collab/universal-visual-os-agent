"""Action executor and scaffolding interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from universal_visual_os_agent.config.models import RunConfig
    from universal_visual_os_agent.geometry.models import ScreenPoint, VirtualDesktopMetrics
    from universal_visual_os_agent.policy.models import PolicyEvaluationContext
    from universal_visual_os_agent.semantics.candidate_exposure import CandidateExposureView
    from universal_visual_os_agent.semantics.state import SemanticStateSnapshot

    from .dry_run import DryRunActionBatchResult, DryRunActionEvaluationResult
    from .models import ActionIntent, ActionResult
    from .safe_click import SafeClickExecutionResult
    from .scaffolding import ActionIntentScaffoldView, ActionIntentScaffoldingResult


class ActionExecutor(Protocol):
    """Executor contract for simulated or future live actions."""

    def execute(self, action: ActionIntent) -> ActionResult:
        """Handle an action intent without assuming live OS control."""


class ActionIntentScaffolder(Protocol):
    """Contract for observe-only action-intent scaffolding."""

    def scaffold(
        self,
        snapshot: SemanticStateSnapshot,
        *,
        exposure_view: CandidateExposureView,
    ) -> ActionIntentScaffoldingResult:
        """Build non-executing action-intent scaffolds from exposed candidates."""


class DryRunActionEngine(Protocol):
    """Contract for dry-run evaluation of scaffolded action intents."""

    def evaluate_intent(
        self,
        intent: ActionIntent,
        *,
        snapshot: SemanticStateSnapshot | None = None,
    ) -> DryRunActionEvaluationResult:
        """Evaluate one action intent without performing any real action."""

    def evaluate_scaffold(
        self,
        scaffold_view: ActionIntentScaffoldView,
        *,
        snapshot: SemanticStateSnapshot | None = None,
    ) -> DryRunActionBatchResult:
        """Evaluate a scaffolded intent set without performing any real action."""


class RealClickTransport(Protocol):
    """Minimal transport for one real click after all safety gates pass."""

    def click(self, point: ScreenPoint) -> None:
        """Perform one real click at the provided screen point."""


class SafeClickExecutor(Protocol):
    """Contract for the minimal real safe-click prototype."""

    def handle(
        self,
        intent: ActionIntent,
        *,
        config: RunConfig,
        metrics: VirtualDesktopMetrics | None = None,
        snapshot: SemanticStateSnapshot | None = None,
        policy_context: PolicyEvaluationContext | None = None,
        execute: bool = False,
    ) -> SafeClickExecutionResult:
        """Evaluate or execute one narrowly scoped safe-click prototype path."""
