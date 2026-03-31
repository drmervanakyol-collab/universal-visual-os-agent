"""Runtime-I/O boundary helpers for event-first orchestration hardening."""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Callable, Mapping
from time import perf_counter

from universal_visual_os_agent.app.runtime_io_models import (
    RuntimeIoCallResult,
    RuntimeIoExecutionClass,
    RuntimeIoExecutionPolicy,
    RuntimeIoOperationKind,
    RuntimeIoTraceEntry,
)


_LOGGER = logging.getLogger(__name__)


class ObserveOnlyRuntimeIoBoundary:
    """Execute runtime-adjacent support calls with explicit boundary diagnostics."""

    boundary_name = "observe_only_runtime_io_boundary"

    def __init__(
        self,
        *,
        execution_policy: RuntimeIoExecutionPolicy | None = None,
    ) -> None:
        self._execution_policy = (
            RuntimeIoExecutionPolicy()
            if execution_policy is None
            else execution_policy
        )

    async def call(
        self,
        *,
        operation_kind: RuntimeIoOperationKind,
        summary: str,
        func: Callable[..., object],
        args: tuple[object, ...] = (),
        kwargs: Mapping[str, object] | None = None,
    ) -> RuntimeIoCallResult:
        active_kwargs = {} if kwargs is None else dict(kwargs)
        preferred_execution_class = self._execution_policy.preferred_execution_class(operation_kind)
        start = perf_counter()
        try:
            if _is_async_callable(func):
                value = await func(*args, **active_kwargs)
                trace_entry = _trace_entry(
                    operation_kind=operation_kind,
                    execution_class=RuntimeIoExecutionClass.event_loop_safe,
                    summary=summary,
                    duration_ms=_duration_ms(start),
                    thread_offloaded=False,
                    metadata={
                        "preferred_execution_class": preferred_execution_class.value,
                        "callable_name": _callable_name(func),
                        "async_callable": True,
                    },
                )
                return RuntimeIoCallResult.ok(
                    boundary_name=self.boundary_name,
                    trace_entry=trace_entry,
                    value=value,
                )

            resolved_execution_class = _resolved_execution_class(
                preferred_execution_class=preferred_execution_class,
                allow_synchronous_fallback=self._execution_policy.allow_synchronous_fallback,
                thread_offload_supported=_thread_offload_supported(func),
            )
            if resolved_execution_class is RuntimeIoExecutionClass.thread_offloaded:
                value = await asyncio.to_thread(_invoke_callable, func, args, active_kwargs)
            else:
                value = func(*args, **active_kwargs)
                if inspect.isawaitable(value):
                    value = await value
                    resolved_execution_class = RuntimeIoExecutionClass.event_loop_safe

            trace_entry = _trace_entry(
                operation_kind=operation_kind,
                execution_class=resolved_execution_class,
                summary=summary,
                duration_ms=_duration_ms(start),
                thread_offloaded=(resolved_execution_class is RuntimeIoExecutionClass.thread_offloaded),
                metadata={
                    "preferred_execution_class": preferred_execution_class.value,
                    "callable_name": _callable_name(func),
                    "thread_offload_supported": _thread_offload_supported(func),
                    "fallback_reason": _fallback_reason(
                        preferred_execution_class=preferred_execution_class,
                        resolved_execution_class=resolved_execution_class,
                    ),
                },
            )
            return RuntimeIoCallResult.ok(
                boundary_name=self.boundary_name,
                trace_entry=trace_entry,
                value=value,
            )
        except Exception as exc:  # noqa: BLE001 - failure-safe boundary result
            _LOGGER.exception(
                "Runtime I/O boundary call failed for %s.",
                operation_kind.value,
            )
            resolved_execution_class = _resolved_execution_class(
                preferred_execution_class=preferred_execution_class,
                allow_synchronous_fallback=self._execution_policy.allow_synchronous_fallback,
                thread_offload_supported=_thread_offload_supported(func),
            )
            trace_entry = _trace_entry(
                operation_kind=operation_kind,
                execution_class=resolved_execution_class,
                summary=summary,
                duration_ms=_duration_ms(start),
                thread_offloaded=(resolved_execution_class is RuntimeIoExecutionClass.thread_offloaded),
                success=False,
                error_type=type(exc).__name__,
                error_message=str(exc),
                metadata={
                    "preferred_execution_class": preferred_execution_class.value,
                    "callable_name": _callable_name(func),
                    "thread_offload_supported": _thread_offload_supported(func),
                    "fallback_reason": _fallback_reason(
                        preferred_execution_class=preferred_execution_class,
                        resolved_execution_class=resolved_execution_class,
                    ),
                },
            )
            return RuntimeIoCallResult.failure(
                boundary_name=self.boundary_name,
                trace_entry=trace_entry,
                error_type=type(exc).__name__,
                error_message=str(exc),
                details={"operation_kind": operation_kind.value},
            )


def _invoke_callable(
    func: Callable[..., object],
    args: tuple[object, ...],
    kwargs: Mapping[str, object],
) -> object:
    return func(*args, **kwargs)


def _is_async_callable(func: Callable[..., object]) -> bool:
    if inspect.iscoroutinefunction(func):
        return True
    call_method = getattr(func, "__call__", None)
    return inspect.iscoroutinefunction(call_method)


def _callable_name(func: Callable[..., object]) -> str:
    qualname = getattr(func, "__qualname__", None)
    if isinstance(qualname, str) and qualname:
        return qualname
    name = getattr(func, "__name__", None)
    if isinstance(name, str) and name:
        return name
    return type(func).__name__


def _thread_offload_supported(func: Callable[..., object]) -> bool:
    for candidate in (func, getattr(func, "__self__", None)):
        if candidate is None:
            continue
        supported = getattr(candidate, "runtime_io_thread_offload_safe", None)
        if isinstance(supported, bool):
            return supported
    return False


def _resolved_execution_class(
    *,
    preferred_execution_class: RuntimeIoExecutionClass,
    allow_synchronous_fallback: bool,
    thread_offload_supported: bool,
) -> RuntimeIoExecutionClass:
    if preferred_execution_class is not RuntimeIoExecutionClass.thread_offloaded:
        return preferred_execution_class
    if thread_offload_supported:
        return RuntimeIoExecutionClass.thread_offloaded
    if allow_synchronous_fallback:
        return RuntimeIoExecutionClass.synchronous_fallback_only
    return RuntimeIoExecutionClass.thread_offloaded


def _fallback_reason(
    *,
    preferred_execution_class: RuntimeIoExecutionClass,
    resolved_execution_class: RuntimeIoExecutionClass,
) -> str | None:
    if (
        preferred_execution_class is RuntimeIoExecutionClass.thread_offloaded
        and resolved_execution_class is RuntimeIoExecutionClass.synchronous_fallback_only
    ):
        return "thread_offload_not_supported"
    return None


def _duration_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000.0, 3)


def _trace_entry(
    *,
    operation_kind: RuntimeIoOperationKind,
    execution_class: RuntimeIoExecutionClass,
    summary: str,
    duration_ms: float,
    thread_offloaded: bool,
    success: bool = True,
    error_type: str | None = None,
    error_message: str | None = None,
    metadata: Mapping[str, object] | None = None,
) -> RuntimeIoTraceEntry:
    return RuntimeIoTraceEntry(
        operation_kind=operation_kind,
        execution_class=execution_class,
        summary=summary,
        success=success,
        duration_ms=duration_ms,
        thread_offloaded=thread_offloaded,
        error_type=error_type,
        error_message=error_message,
        metadata={} if metadata is None else dict(metadata),
    )


__all__ = ["ObserveOnlyRuntimeIoBoundary"]
