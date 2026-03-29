"""Verification contracts for semantic state transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticStateExpectation:
    """Expected semantic state constraints after a planned transition."""

    target_candidate_id: str
    should_be_visible: bool = True
    should_be_enabled: bool = True
    should_be_occluded: bool = False

    def __post_init__(self) -> None:
        if not self.target_candidate_id:
            raise ValueError("target_candidate_id must not be empty.")

    def to_dict(self) -> dict[str, Any]:
        """Serialize expectation into JSON-friendly data."""

        return {
            "target_candidate_id": self.target_candidate_id,
            "should_be_visible": self.should_be_visible,
            "should_be_enabled": self.should_be_enabled,
            "should_be_occluded": self.should_be_occluded,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SemanticStateExpectation:
        """Parse and validate expectation payloads from persistence/replay."""

        return cls(
            target_candidate_id=str(payload["target_candidate_id"]),
            should_be_visible=bool(payload.get("should_be_visible", True)),
            should_be_enabled=bool(payload.get("should_be_enabled", True)),
            should_be_occluded=bool(payload.get("should_be_occluded", False)),
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class VerificationContract:
    """Contract that declares what verification must confirm."""

    contract_id: str
    expectations: tuple[SemanticStateExpectation, ...]
    require_all: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.contract_id:
            raise ValueError("contract_id must not be empty.")
        if not self.expectations:
            raise ValueError("expectations must not be empty.")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the contract for durable storage or replay fixtures."""

        return {
            "contract_id": self.contract_id,
            "expectations": [item.to_dict() for item in self.expectations],
            "require_all": self.require_all,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> VerificationContract:
        """Parse and validate contract payloads from persisted state."""

        raw_expectations = payload.get("expectations", [])
        expectations = tuple(
            SemanticStateExpectation.from_dict(item) for item in raw_expectations
        )
        return cls(
            contract_id=str(payload["contract_id"]),
            expectations=expectations,
            require_all=bool(payload.get("require_all", True)),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class VerificationResult:
    """Verification status for an expected state transition."""

    success: bool
    summary: str
