"""Synthetic replay session builders."""

from __future__ import annotations

from datetime import timedelta
from typing import Sequence

from universal_visual_os_agent.app.models import FrameDiff, LoopRequest
from universal_visual_os_agent.geometry.models import NormalizedBBox
from universal_visual_os_agent.perception.models import CapturedFrame
from universal_visual_os_agent.replay.models import DeterministicReplaySettings, ReplayEntry, ReplaySession
from universal_visual_os_agent.semantics import SemanticCandidate, SemanticStateSnapshot


def build_synthetic_replay_session(
    labels: Sequence[str],
    *,
    settings: DeterministicReplaySettings | None = None,
) -> ReplaySession:
    """Build a replay session from deterministic synthetic labels."""

    deterministic = settings or DeterministicReplaySettings()
    entries: list[ReplayEntry] = []
    for index, label in enumerate(labels):
        observed_at = deterministic.start_time + timedelta(milliseconds=deterministic.step_milliseconds * index)
        bounds = NormalizedBBox(left=0.1, top=0.2, width=0.3, height=0.1)
        snapshot = SemanticStateSnapshot(
            snapshot_id=f"snapshot-{deterministic.seed}-{index}",
            observed_at=observed_at,
            candidates=(
                SemanticCandidate(
                    candidate_id=f"candidate-{deterministic.seed}-{index}",
                    label=label,
                    bounds=bounds,
                    confidence=1.0 if deterministic.enabled else None,
                    metadata={"noise_disabled": deterministic.disable_noise},
                ),
            ),
            metadata={"synthetic": True, "noise_disabled": deterministic.disable_noise},
        )
        frame = CapturedFrame(
            frame_id=f"frame-{deterministic.seed}-{index}",
            width=100,
            height=100,
            captured_at=observed_at,
        )
        entries.append(
            ReplayEntry(
                request=LoopRequest(request_id=f"replay-request-{deterministic.seed}-{index}"),
                frame=frame,
                semantic_snapshot=snapshot,
                diff=FrameDiff(changed=True, summary=f"synthetic-step-{index}"),
                events=(f"synthetic:{label}",),
                metadata={"synthetic": True},
            )
        )
    return ReplaySession(
        session_id=f"synthetic-session-{deterministic.seed}",
        entries=tuple(entries),
        metadata={
            "synthetic": True,
            "deterministic": deterministic.enabled,
            "noise_disabled": deterministic.disable_noise,
        },
    )
