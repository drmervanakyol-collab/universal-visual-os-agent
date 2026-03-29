"""Audit sink interfaces."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.audit.models import AuditEvent


class AuditSink(Protocol):
    """Append-only sink for audit events."""

    def write(self, event: AuditEvent) -> None:
        """Persist or forward an audit event."""

