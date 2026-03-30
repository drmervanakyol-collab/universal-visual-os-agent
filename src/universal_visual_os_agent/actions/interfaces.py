"""Action executor and scaffolding interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from universal_visual_os_agent.ai_boundary.models import (
        ValidatedLocalVisualResolverOutput,
        ValidatedPlannerActionSuggestion,
    )
    from universal_visual_os_agent.config.models import RunConfig
    from universal_visual_os_agent.geometry.models import ScreenPoint, VirtualDesktopMetrics
    from universal_visual_os_agent.policy.models import PolicyDecision, PolicyEvaluationContext
    from universal_visual_os_agent.semantics.candidate_exposure import CandidateExposureView
    from universal_visual_os_agent.semantics.state import SemanticStateSnapshot

    from .dry_run_models import (
        DryRunActionBatchResult,
        DryRunActionEvaluation,
        DryRunActionEvaluationResult,
    )
    from .models import ActionIntent, ActionResult
    from .safe_click import SafeClickExecutionResult
    from .scaffolding_models import ActionIntentScaffoldView, ActionIntentScaffoldingResult
    from .tool_boundary_models import (
        ActionToolBoundaryEvaluationResult,
        ActionToolBoundarySurface,
    )


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


class ActionToolBoundaryGuard(Protocol):
    """Final eligibility guard between structured artifacts and tool surfaces."""

    def evaluate_planner_action_suggestion_for_surface(
        self,
        suggestion: ValidatedPlannerActionSuggestion,
        *,
        surface: ActionToolBoundarySurface,
    ) -> ActionToolBoundaryEvaluationResult:
        """Reject direct structured planner outputs unless they are rebound safely."""

    def evaluate_resolver_output_for_surface(
        self,
        output: ValidatedLocalVisualResolverOutput,
        *,
        surface: ActionToolBoundarySurface,
    ) -> ActionToolBoundaryEvaluationResult:
        """Reject direct structured resolver outputs unless they are rebound safely."""

    def evaluate_intent_for_dry_run(
        self,
        intent: ActionIntent,
        *,
        snapshot: SemanticStateSnapshot | None = None,
    ) -> ActionToolBoundaryEvaluationResult:
        """Validate a scaffolded intent before it reaches the dry-run engine."""

    def evaluate_intent_for_safe_click(
        self,
        intent: ActionIntent,
        *,
        config: RunConfig,
        target_screen_point: ScreenPoint | None,
        dry_run_evaluation: DryRunActionEvaluation,
        policy_decision: PolicyDecision | None,
        snapshot: SemanticStateSnapshot | None = None,
        execute: bool = False,
        click_transport_available: bool = False,
    ) -> ActionToolBoundaryEvaluationResult:
        """Validate a scaffolded intent before it reaches the safe-click prototype."""


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
