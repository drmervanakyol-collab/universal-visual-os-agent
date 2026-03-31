"""Async-friendly orchestration protocols."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Mapping, Protocol

from universal_visual_os_agent.app.models import FrameDiff, LoopPlan, LoopRequest
from universal_visual_os_agent.app.runtime_event_models import (
    RuntimeEvent,
    RuntimeEventDispatchResult,
    RuntimeEventSubmissionResult,
)
from universal_visual_os_agent.app.runtime_io_models import (
    RuntimeIoCallResult,
    RuntimeIoOperationKind,
)
from universal_visual_os_agent.actions.models import ActionIntent, ActionResult
from universal_visual_os_agent.config.modes import AgentMode
from universal_visual_os_agent.config.models import RunConfig
from universal_visual_os_agent.perception.models import CapturedFrame
from universal_visual_os_agent.recovery.models import ReconciliationResult, RecoverySnapshot
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot
from universal_visual_os_agent.verification.models import (
    SemanticStateTransition,
    SemanticTransitionExpectation,
    VerificationResult,
)


class ObservationProvider(Protocol):
    """Observe the current frame for one orchestration request."""

    def observe(
        self,
        request: LoopRequest,
        *,
        config: RunConfig,
    ) -> CapturedFrame | Awaitable[CapturedFrame]:
        """Return the current frame metadata."""


class FrameDiffer(Protocol):
    """Compute a pure diff between two frames."""

    def diff(
        self,
        previous: CapturedFrame | None,
        current: CapturedFrame,
    ) -> FrameDiff | Awaitable[FrameDiff]:
        """Return diff metadata for the current frame."""


class SemanticRebuilder(Protocol):
    """Rebuild semantic state from the current frame and diff."""

    def rebuild(
        self,
        frame: CapturedFrame,
        diff: FrameDiff,
    ) -> SemanticStateSnapshot | Awaitable[SemanticStateSnapshot]:
        """Return the current semantic state snapshot."""


class LoopPlanner(Protocol):
    """Planner contract used by the async loop skeleton."""

    def plan(
        self,
        semantic_state: SemanticStateSnapshot,
        *,
        mode: AgentMode,
        recovery_snapshot: RecoverySnapshot | None = None,
        reconciliation_result: ReconciliationResult | None = None,
    ) -> LoopPlan | Awaitable[LoopPlan]:
        """Produce the next loop plan."""


class TransitionVerifier(Protocol):
    """Verification contract used by the async loop skeleton."""

    def verify(
        self,
        expectation: SemanticTransitionExpectation,
        transition: SemanticStateTransition,
    ) -> VerificationResult | Awaitable[VerificationResult]:
        """Verify a semantic transition."""


class RecoveryLoader(Protocol):
    """Recovery snapshot loader used by recovery mode."""

    def load_latest(self, task_id: str) -> RecoverySnapshot | None | Awaitable[RecoverySnapshot | None]:
        """Load the latest recovery snapshot for a task."""


class RecoveryReconciler(Protocol):
    """Reconcile recovered state against observed or replayed state."""

    def reconcile(
        self,
        snapshot: RecoverySnapshot,
        observed_state: Mapping[str, object] | None = None,
    ) -> ReconciliationResult | Awaitable[ReconciliationResult]:
        """Produce a reconciliation result."""


class LoopActionExecutor(Protocol):
    """Placeholder executor contract for future live execution."""

    def execute(self, action: ActionIntent) -> ActionResult | Awaitable[ActionResult]:
        """Execute or simulate an action intent."""


class RuntimeEventCoordinator(Protocol):
    """Event-first runtime coordination contract for non-executing scaffolding."""

    @property
    def pending_count(self) -> int:
        """Return the number of queued runtime events."""

    def submit(self, event: RuntimeEvent) -> RuntimeEventSubmissionResult:
        """Queue one runtime event for later dispatch."""

    def dispatch_next(self) -> RuntimeEventDispatchResult:
        """Build the next runtime dispatch plan from queued events."""


class RuntimeIoBoundary(Protocol):
    """Boundary contract for runtime-adjacent blocking/support calls."""

    async def call(
        self,
        *,
        operation_kind: RuntimeIoOperationKind,
        summary: str,
        func: Callable[..., object],
        args: tuple[object, ...] = (),
        kwargs: Mapping[str, object] | None = None,
    ) -> RuntimeIoCallResult:
        """Execute one runtime support call with explicit boundary diagnostics."""
