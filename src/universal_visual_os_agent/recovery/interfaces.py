"""Recovery loading and reconciliation contracts."""

from __future__ import annotations

from typing import Mapping, Protocol

from universal_visual_os_agent.recovery.models import ReconciliationResult, RecoverySnapshot


class RecoverySnapshotLoader(Protocol):
    """Load persisted recovery state without touching live OS state."""

    def load_latest(self, task_id: str) -> RecoverySnapshot | None:
        """Return the latest recovery snapshot for a task, if available."""


class StateReconciler(Protocol):
    """Compare recovered state to current observed or replayed state."""

    def reconcile(
        self,
        snapshot: RecoverySnapshot,
        observed_state: Mapping[str, object] | None = None,
    ) -> ReconciliationResult:
        """Produce a reconciliation result without performing live actions."""

