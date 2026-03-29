"""Normalized geometry primitives."""

from __future__ import annotations

from dataclasses import dataclass


def _validate_normalized(value: float, *, field_name: str) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0 inclusive.")


@dataclass(slots=True, frozen=True, kw_only=True)
class NormalizedPoint:
    """A normalized screen coordinate."""

    x: float
    y: float

    def __post_init__(self) -> None:
        _validate_normalized(self.x, field_name="x")
        _validate_normalized(self.y, field_name="y")


@dataclass(slots=True, frozen=True, kw_only=True)
class NormalizedBBox:
    """A normalized bounding box."""

    left: float
    top: float
    width: float
    height: float

    def __post_init__(self) -> None:
        _validate_normalized(self.left, field_name="left")
        _validate_normalized(self.top, field_name="top")
        _validate_normalized(self.width, field_name="width")
        _validate_normalized(self.height, field_name="height")
        if self.left + self.width > 1.0:
            raise ValueError("left + width must not exceed 1.0.")
        if self.top + self.height > 1.0:
            raise ValueError("top + height must not exceed 1.0.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ScreenMetrics:
    """Physical screen metrics required for later DPI-aware transforms."""

    width_px: int
    height_px: int
    dpi_scale: float = 1.0

    def __post_init__(self) -> None:
        if self.width_px <= 0:
            raise ValueError("width_px must be positive.")
        if self.height_px <= 0:
            raise ValueError("height_px must be positive.")
        if self.dpi_scale <= 0.0:
            raise ValueError("dpi_scale must be positive.")

