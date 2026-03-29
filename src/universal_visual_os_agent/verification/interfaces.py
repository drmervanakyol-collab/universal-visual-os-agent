"""Verification interfaces."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.actions.models import ActionIntent
from universal_visual_os_agent.semantics.models import SemanticStateSnapshot
from universal_visual_os_agent.verification.models import (
    VerificationContract,
    VerificationResult,
)


class Verifier(Protocol):
    """Verification contract for simulated or future actions."""

    def verify(
        self,
        action: ActionIntent,
        before_state: SemanticStateSnapshot | None,
        after_state: SemanticStateSnapshot | None,
        contract: VerificationContract,
    ) -> VerificationResult:
        """Check whether an intended semantic transition is satisfied."""
