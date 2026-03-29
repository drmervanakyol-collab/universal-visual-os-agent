"""Policy outcomes for safe execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PolicyVerdict(StrEnum):
    """Policy decisions for a candidate action."""

    allow = "allow"
    deny = "deny"
    review = "review"


@dataclass(slots=True, frozen=True, kw_only=True)
class PolicyDecision:
    """Structured policy decision with an auditable reason."""

    verdict: PolicyVerdict
    reason: str

