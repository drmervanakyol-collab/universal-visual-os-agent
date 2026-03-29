"""Test configuration for the src/ layout."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TEST_TMP_ROOT = ROOT / ".tmp_test_artifacts"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from universal_visual_os_agent.testing import (  # noqa: E402
    build_recovery_mode_config,
    build_recovery_mode_request,
    build_replay_mode_config,
)


@pytest.fixture
def workspace_tmp_path() -> Path:
    """Create a temporary directory inside the workspace."""

    path = TEST_TMP_ROOT / uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def replay_mode_config(workspace_tmp_path: Path):
    """Reusable replay-mode configuration fixture."""

    return build_replay_mode_config(workspace_tmp_path / "replay-session.json")


@pytest.fixture
def recovery_mode_config():
    """Reusable recovery-mode configuration fixture."""

    return build_recovery_mode_config()


@pytest.fixture
def recovery_mode_request():
    """Reusable recovery-mode request fixture."""

    return build_recovery_mode_request()
