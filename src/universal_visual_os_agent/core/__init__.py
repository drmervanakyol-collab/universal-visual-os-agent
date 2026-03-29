"""Core shared contracts and event primitives."""

from universal_visual_os_agent.core.events import EventEnvelope
from universal_visual_os_agent.core.interfaces import Clock, EventSink

__all__ = ["Clock", "EventEnvelope", "EventSink"]

