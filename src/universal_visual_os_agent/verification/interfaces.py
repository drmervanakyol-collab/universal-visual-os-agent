"""Verification interfaces."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.verification.models import (
    SemanticStateTransition,
    SemanticTransitionExpectation,
    VerificationResult,
)


class SemanticTransitionVerifier(Protocol):
    """Verification contract for semantic-state transitions."""

    def verify(
        self,
        expectation: SemanticTransitionExpectation,
        transition: SemanticStateTransition,
    ) -> VerificationResult:
        """Check whether an expected semantic transition is satisfied."""


class Verifier(SemanticTransitionVerifier, Protocol):
    """Backwards-compatible alias for the generic verifier contract."""
