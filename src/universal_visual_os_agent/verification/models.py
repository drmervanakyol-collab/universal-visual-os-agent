"""Verification contracts for semantic state transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


def _read_bool(payload: dict[str, Any], key: str, *, default: bool) -> bool:
    raw = payload.get(key, default)
    if isinstance(raw, bool):
        return raw
    raise ValueError(f"{key} must be a bool.")


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

        if not isinstance(payload, dict):
            raise ValueError("payload must be a mapping.")
        return cls(
            target_candidate_id=str(payload["target_candidate_id"]),
            should_be_visible=_read_bool(payload, "should_be_visible", default=True),
            should_be_enabled=_read_bool(payload, "should_be_enabled", default=True),
            should_be_occluded=_read_bool(payload, "should_be_occluded", default=False),
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class VerificationContract:
    """Contract that declares what verification must confirm."""

    contract_id: str
    expectations: tuple[SemanticStateExpectation, ...]
    require_all: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.contract_id:
            raise ValueError("contract_id must not be empty.")
        if not self.expectations:
            raise ValueError("expectations must not be empty.")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

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

        if not isinstance(payload, dict):
            raise ValueError("payload must be a mapping.")
        raw_expectations = payload.get("expectations", [])
        if not isinstance(raw_expectations, list):
            raise ValueError("expectations must be a list.")
        expectations = tuple(
            SemanticStateExpectation.from_dict(item) for item in raw_expectations
        )
        raw_metadata = payload.get("metadata", {})
        if not isinstance(raw_metadata, dict):
            raise ValueError("metadata must be a mapping.")
        return cls(
            contract_id=str(payload["contract_id"]),
            expectations=expectations,
            require_all=_read_bool(payload, "require_all", default=True),
            metadata=raw_metadata,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class VerificationResult:
    """Verification status for an expected state transition."""

    success: bool
    summary: str
