"""Verification interfaces."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.actions.models import ActionIntent
from universal_visual_os_agent.verification.models import VerificationResult


class Verifier(Protocol):
    """Verification contract for simulated or future actions."""

    def verify(self, action: ActionIntent) -> VerificationResult:
        """Check whether an intended state transition is satisfied."""

