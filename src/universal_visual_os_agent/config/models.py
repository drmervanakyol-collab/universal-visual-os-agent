"""Dataclass-based configuration with safe defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Mapping

from universal_visual_os_agent.config.modes import AgentMode


@dataclass(slots=True, frozen=True, kw_only=True)
class LoggingConfig:
    """Structured logging options for the agent package."""

    VALID_LEVELS: ClassVar[frozenset[str]] = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

    logger_name: str = "universal_visual_os_agent"
    level: str = "INFO"
    format_string: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

    def __post_init__(self) -> None:
        normalized = self.level.upper()
        if normalized not in self.VALID_LEVELS:
            raise ValueError(f"Unsupported log level: {self.level}")
        object.__setattr__(self, "level", normalized)

    @property
    def python_level(self) -> int:
        """Resolve the logging module constant for the configured level."""

        import logging

        return getattr(logging, self.level)


@dataclass(slots=True, frozen=True, kw_only=True)
class PersistenceConfig:
    """SQLite persistence defaults for checkpoints and recovery state."""

    database_path: Path = Path("data/agent_state.sqlite3")
    enable_checkpoints: bool = True


@dataclass(slots=True, frozen=True, kw_only=True)
class ReplayConfig:
    """Replay mode settings."""

    session_path: Path | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class RunConfig:
    """Top-level runtime configuration with explicit safety guarantees."""

    mode: AgentMode = AgentMode.observe_only
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)
    replay: ReplayConfig = field(default_factory=ReplayConfig)
    allow_live_input: bool = False

    def __post_init__(self) -> None:
        if self.allow_live_input:
            raise ValueError("Phase 1 does not permit real OS input.")
        if self.mode.reads_replay_source and self.replay.session_path is None:
            raise ValueError("replay_mode requires replay.session_path.")
        if self.mode.resumes_from_checkpoint and not self.persistence.enable_checkpoints:
            raise ValueError("recovery_mode requires checkpoint persistence.")

    @property
    def should_capture_live_state(self) -> bool:
        """Whether live screen observation is expected."""

        return self.mode in {AgentMode.observe_only, AgentMode.dry_run, AgentMode.recovery_mode}

    @property
    def should_read_replay(self) -> bool:
        """Whether replay fixtures are the state source."""

        return self.mode.reads_replay_source

    @property
    def should_plan_actions(self) -> bool:
        """Whether the planner should emit action intents."""

        return self.mode.plans_actions

    @property
    def should_attempt_recovery(self) -> bool:
        """Whether persisted checkpoints should be consulted."""

        return self.mode.resumes_from_checkpoint

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "RunConfig":
        """Build a run configuration from simple nested mappings."""

        mode = AgentMode(raw.get("mode", AgentMode.observe_only))
        logging_raw = _mapping(raw.get("logging"))
        persistence_raw = _mapping(raw.get("persistence"))
        replay_raw = _mapping(raw.get("replay"))
        return cls(
            mode=mode,
            logging=LoggingConfig(
                logger_name=str(logging_raw.get("logger_name", "universal_visual_os_agent")),
                level=str(logging_raw.get("level", "INFO")),
                format_string=str(
                    logging_raw.get(
                        "format_string",
                        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                    )
                ),
            ),
            persistence=PersistenceConfig(
                database_path=Path(str(persistence_raw.get("database_path", "data/agent_state.sqlite3"))),
                enable_checkpoints=bool(persistence_raw.get("enable_checkpoints", True)),
            ),
            replay=ReplayConfig(
                session_path=_optional_path(replay_raw.get("session_path")),
            ),
            allow_live_input=bool(raw.get("allow_live_input", False)),
        )


def _mapping(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("Configuration sections must be mappings.")
    return value


def _optional_path(value: Any) -> Path | None:
    if value in (None, ""):
        return None
    return Path(str(value))

