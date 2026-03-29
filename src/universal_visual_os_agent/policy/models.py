"""Policy and safety models for action gating."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping


class PolicyVerdict(StrEnum):
    """Policy decisions for a candidate action."""

    allow = "allow"
    deny = "deny"
    review = "review"


class ProtectedContextStatus(StrEnum):
    """Protected-context assessment outcomes."""

    clear = "clear"
    protected = "protected"
    unknown = "unknown"
    partial = "partial"


class PolicyContextCompleteness(StrEnum):
    """How much policy context is available for a decision."""

    complete = "complete"
    partial = "partial"
    unknown = "unknown"


class PauseStatus(StrEnum):
    """Pause state for action gating."""

    running = "running"
    paused = "paused"


@dataclass(slots=True, frozen=True, kw_only=True)
class PolicyRule:
    """A pure allowlist or denylist rule for action matching."""

    rule_id: str
    description: str
    action_types: tuple[str, ...] = ()
    required_metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.rule_id:
            raise ValueError("rule_id must not be empty.")
        if not self.description:
            raise ValueError("description must not be empty.")

    def matches(self, action_type: str, metadata: Mapping[str, object]) -> bool:
        """Return whether the rule applies to the provided action."""

        if self.action_types and action_type not in self.action_types:
            return False
        for key, value in self.required_metadata.items():
            if metadata.get(key) != value:
                return False
        return True


@dataclass(slots=True, frozen=True, kw_only=True)
class PolicyRuleSet:
    """Allowlist and denylist rules used by the policy engine."""

    allowlist: tuple[PolicyRule, ...] = ()
    denylist: tuple[PolicyRule, ...] = ()


@dataclass(slots=True, frozen=True, kw_only=True)
class ProtectedContextAssessment:
    """Assessment result from a protected-context detector hook."""

    status: ProtectedContextStatus = ProtectedContextStatus.unknown
    reason: str = "No protected-context signal provided."
    evidence: Mapping[str, object] = field(default_factory=dict)


@dataclass(slots=True, frozen=True, kw_only=True)
class KillSwitchState:
    """Snapshot of the kill switch state."""

    engaged: bool = False
    reason: str | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class PauseState:
    """Snapshot of pause/resume state."""

    status: PauseStatus = PauseStatus.running
    reason: str | None = None

    @property
    def paused(self) -> bool:
        """Whether action processing is currently paused."""

        return self.status is PauseStatus.paused


@dataclass(slots=True, frozen=True, kw_only=True)
class PolicyEvaluationContext:
    """Context passed into pure action gating before any future live execution."""

    completeness: PolicyContextCompleteness = PolicyContextCompleteness.unknown
    live_execution_requested: bool = False
    live_execution_enabled: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(slots=True, frozen=True, kw_only=True)
class PolicyDecision:
    """Structured policy decision with an auditable reason."""

    verdict: PolicyVerdict
    reason: str
    matched_rule_id: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    @property
    def blocked(self) -> bool:
        """Whether the action should be blocked from execution."""

        return self.verdict is not PolicyVerdict.allow
