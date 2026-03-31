"""Runtime I/O boundary models for event-first orchestration hardening."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Self


class RuntimeIoOperationKind(StrEnum):
    """Stable runtime-adjacent support operations tracked at the I/O boundary."""

    runtime_event_submit = "runtime_event_submit"
    runtime_event_dispatch = "runtime_event_dispatch"
    recovery_load = "recovery_load"
    recovery_reconcile = "recovery_reconcile"
    policy_evaluate = "policy_evaluate"


class RuntimeIoExecutionClass(StrEnum):
    """How a runtime support call was executed relative to the event loop."""

    event_loop_safe = "event_loop_safe"
    thread_offloaded = "thread_offloaded"
    synchronous_fallback_only = "synchronous_fallback_only"


@dataclass(slots=True, frozen=True, kw_only=True)
class RuntimeIoTraceEntry:
    """One structured runtime-I/O trace record."""

    operation_kind: RuntimeIoOperationKind
    execution_class: RuntimeIoExecutionClass
    summary: str
    success: bool
    duration_ms: float
    thread_offloaded: bool = False
    error_type: str | None = None
    error_message: str | None = None
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if self.duration_ms < 0.0:
            raise ValueError("duration_ms must not be negative.")
        if self.success and (self.error_type is not None or self.error_message is not None):
            raise ValueError("Successful runtime I/O trace entries must not include error details.")
        if not self.success and self.error_type is None:
            raise ValueError("Failed runtime I/O trace entries must include error_type.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Runtime I/O trace entries must remain safety-first and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class RuntimeIoCallResult:
    """Failure-safe result for one runtime-I/O boundary call."""

    boundary_name: str
    success: bool
    trace_entry: RuntimeIoTraceEntry
    value: object | None = None
    error_type: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.boundary_name:
            raise ValueError("boundary_name must not be empty.")
        if self.success and (self.error_type is not None or self.error_message is not None):
            raise ValueError("Successful runtime I/O call results must not include error details.")
        if not self.success and self.error_type is None:
            raise ValueError("Failed runtime I/O call results must include error_type.")

    @classmethod
    def ok(
        cls,
        *,
        boundary_name: str,
        trace_entry: RuntimeIoTraceEntry,
        value: object | None = None,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            boundary_name=boundary_name,
            success=True,
            trace_entry=trace_entry,
            value=value,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        boundary_name: str,
        trace_entry: RuntimeIoTraceEntry,
        error_type: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            boundary_name=boundary_name,
            success=False,
            trace_entry=trace_entry,
            error_type=error_type,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class RuntimeIoExecutionPolicy:
    """Conservative execution preferences for runtime-adjacent support calls."""

    event_loop_safe_operations: tuple[RuntimeIoOperationKind, ...] = (
        RuntimeIoOperationKind.runtime_event_submit,
        RuntimeIoOperationKind.runtime_event_dispatch,
        RuntimeIoOperationKind.policy_evaluate,
    )
    thread_offload_preferred_operations: tuple[RuntimeIoOperationKind, ...] = (
        RuntimeIoOperationKind.recovery_load,
        RuntimeIoOperationKind.recovery_reconcile,
    )
    allow_synchronous_fallback: bool = True
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True

    def __post_init__(self) -> None:
        overlap = set(self.event_loop_safe_operations) & set(self.thread_offload_preferred_operations)
        if overlap:
            raise ValueError(
                "event_loop_safe_operations and thread_offload_preferred_operations must not overlap."
            )
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Runtime I/O execution policies must remain safety-first and non-executing.")

    def preferred_execution_class(
        self,
        operation_kind: RuntimeIoOperationKind,
    ) -> RuntimeIoExecutionClass:
        if operation_kind in self.event_loop_safe_operations:
            return RuntimeIoExecutionClass.event_loop_safe
        if operation_kind in self.thread_offload_preferred_operations:
            return RuntimeIoExecutionClass.thread_offloaded
        return RuntimeIoExecutionClass.synchronous_fallback_only


__all__ = [
    "RuntimeIoCallResult",
    "RuntimeIoExecutionClass",
    "RuntimeIoExecutionPolicy",
    "RuntimeIoOperationKind",
    "RuntimeIoTraceEntry",
]
