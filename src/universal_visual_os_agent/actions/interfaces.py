"""Action executor and scaffolding interfaces."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.actions.dry_run import (
    DryRunActionBatchResult,
    DryRunActionEvaluationResult,
)
from universal_visual_os_agent.actions.scaffolding import ActionIntentScaffoldingResult
from universal_visual_os_agent.actions.models import ActionIntent, ActionResult
from universal_visual_os_agent.actions.scaffolding import ActionIntentScaffoldView
from universal_visual_os_agent.semantics.candidate_exposure import CandidateExposureView
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot


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
