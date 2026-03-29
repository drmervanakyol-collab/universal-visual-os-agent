"""Post-action verification models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True, kw_only=True)
class VerificationResult:
    """Verification status for an expected state transition."""

    success: bool
    summary: str

