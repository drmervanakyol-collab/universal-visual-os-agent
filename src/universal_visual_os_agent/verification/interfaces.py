"""Verification interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .models import (
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


class GoalOrientedVerifier(SemanticTransitionVerifier, Protocol):
    """Verification contract for semantic-delta-based expected outcomes."""


class VerificationExplainer(Protocol):
    """Enrich verification results with structured explanations and taxonomy."""

    def explain(
        self,
        result: VerificationResult,
        *,
        expectation: SemanticTransitionExpectation,
        transition: SemanticStateTransition,
    ) -> VerificationResult:
        """Return a verification result enriched with observe-only explanations."""
