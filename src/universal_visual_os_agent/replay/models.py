"""Replay session and deterministic-mode models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping
from uuid import uuid4

from universal_visual_os_agent.app.models import FrameDiff, LoopRequest, LoopResult, LoopStatus
from universal_visual_os_agent.perception.models import CapturedFrame
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot


@dataclass(slots=True, frozen=True, kw_only=True)
class DeterministicReplaySettings:
    """Settings for deterministic replay and synthetic test data."""

    enabled: bool = True
    seed: int = 0
    disable_noise: bool = True
    start_time: datetime = field(default_factory=lambda: datetime(2026, 1, 1, tzinfo=UTC))
    step_milliseconds: int = 100

    def __post_init__(self) -> None:
        if self.step_milliseconds <= 0:
            raise ValueError("step_milliseconds must be positive.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ReplayEntry:
    """One replay step containing recorded or synthetic state."""

    request: LoopRequest
    frame: CapturedFrame | None = None
    semantic_snapshot: SemanticStateSnapshot | None = None
    diff: FrameDiff | None = None
    events: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(slots=True, frozen=True, kw_only=True)
class ReplaySession:
    """A deterministic or recorded sequence of replay entries."""

    entries: tuple[ReplayEntry, ...]
    session_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        request_ids = {entry.request.request_id for entry in self.entries}
        if len(request_ids) != len(self.entries):
            raise ValueError("Replay entry request identifiers must be unique.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ReplayHarnessResult:
    """Result summary for a replay harness run."""

    status: LoopStatus
    results: tuple[LoopResult, ...] = ()
    missing_replay_data: bool = False
    safe_abort_reason: str | None = None
    live_execution_attempted: bool = False
