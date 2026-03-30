"""Supported safe agent modes."""

from __future__ import annotations

from enum import StrEnum


class AgentMode(StrEnum):
    """Execution modes with safety-first defaults."""

    observe_only = "observe_only"
    dry_run = "dry_run"
    replay_mode = "replay_mode"
    recovery_mode = "recovery_mode"
    safe_action_mode = "safe_action_mode"

    @property
    def plans_actions(self) -> bool:
        """Whether the planner is expected to emit action intents."""

        return self is not AgentMode.observe_only

    @property
    def reads_replay_source(self) -> bool:
        """Whether a replay session must be provided."""

        return self is AgentMode.replay_mode

    @property
    def resumes_from_checkpoint(self) -> bool:
        """Whether checkpoint recovery is required."""

        return self is AgentMode.recovery_mode
