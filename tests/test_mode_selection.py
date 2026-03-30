from __future__ import annotations

import pytest

from universal_visual_os_agent.config import AgentMode, RunConfig


@pytest.mark.parametrize(
    ("mode", "plans_actions", "reads_replay_source", "resumes_from_checkpoint"),
    [
        (AgentMode.observe_only, False, False, False),
        (AgentMode.dry_run, True, False, False),
        (AgentMode.replay_mode, True, True, False),
        (AgentMode.recovery_mode, True, False, True),
        (AgentMode.safe_action_mode, True, False, False),
    ],
)
def test_agent_mode_properties(
    mode: AgentMode,
    plans_actions: bool,
    reads_replay_source: bool,
    resumes_from_checkpoint: bool,
) -> None:
    assert mode.plans_actions is plans_actions
    assert mode.reads_replay_source is reads_replay_source
    assert mode.resumes_from_checkpoint is resumes_from_checkpoint


def test_recovery_mode_requires_checkpoints() -> None:
    with pytest.raises(ValueError, match="recovery_mode requires checkpoint persistence"):
        RunConfig.from_mapping(
            {
                "mode": "recovery_mode",
                "persistence": {"enable_checkpoints": False},
            }
        )


def test_live_input_requires_safe_action_mode() -> None:
    with pytest.raises(ValueError, match="allow_live_input requires safe_action_mode"):
        RunConfig.from_mapping({"allow_live_input": True})


def test_safe_action_mode_can_explicitly_enable_live_input() -> None:
    config = RunConfig.from_mapping({"mode": "safe_action_mode", "allow_live_input": True})

    assert config.mode is AgentMode.safe_action_mode
    assert config.allow_live_input is True
