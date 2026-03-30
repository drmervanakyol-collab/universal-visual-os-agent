from __future__ import annotations

import logging
from pathlib import Path

import pytest

from universal_visual_os_agent.app import configure_logging
from universal_visual_os_agent.config import AgentMode, RunConfig


def test_run_config_defaults_to_observe_only_and_safe_capture() -> None:
    config = RunConfig()

    assert config.mode is AgentMode.observe_only
    assert config.allow_live_input is False
    assert config.should_capture_live_state is True
    assert config.should_plan_actions is False


def test_safe_action_mode_supports_live_capture_and_explicit_live_input_flag() -> None:
    config = RunConfig.from_mapping({"mode": "safe_action_mode", "allow_live_input": True})

    assert config.mode is AgentMode.safe_action_mode
    assert config.allow_live_input is True
    assert config.should_capture_live_state is True
    assert config.should_plan_actions is True


def test_run_config_from_mapping_builds_nested_sections() -> None:
    config = RunConfig.from_mapping(
        {
            "mode": "dry_run",
            "logging": {"level": "debug"},
            "persistence": {"database_path": "state/test.sqlite3"},
        }
    )

    assert config.mode is AgentMode.dry_run
    assert config.logging.level == "DEBUG"
    assert config.persistence.database_path == Path("state/test.sqlite3")


def test_replay_mode_requires_session_path() -> None:
    with pytest.raises(ValueError, match="replay_mode requires replay.session_path"):
        RunConfig.from_mapping({"mode": "replay_mode"})


def test_configure_logging_returns_package_logger() -> None:
    config = RunConfig.from_mapping({"logging": {"level": "warning"}})

    logger = configure_logging(config.logging)

    assert logger.name == "universal_visual_os_agent"
    assert logger.level == logging.WARNING
