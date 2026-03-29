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
    """Physical screen metrics for one display in the virtual desktop."""

    width_px: int
    height_px: int
    origin_x_px: int = 0
    origin_y_px: int = 0
    dpi_scale: float = 1.0
    display_id: str = "primary"
    is_primary: bool = False

    def __post_init__(self) -> None:
        if self.width_px <= 0:
            raise ValueError("width_px must be positive.")
        if self.height_px <= 0:
            raise ValueError("height_px must be positive.")
        if self.dpi_scale <= 0.0:
            raise ValueError("dpi_scale must be positive.")
        if not self.display_id:
            raise ValueError("display_id must not be empty.")

    @property
    def right_px(self) -> int:
        """Return the exclusive right edge in virtual desktop coordinates."""

        return self.origin_x_px + self.width_px

    @property
    def bottom_px(self) -> int:
        """Return the exclusive bottom edge in virtual desktop coordinates."""

        return self.origin_y_px + self.height_px

    @property
    def logical_width_px(self) -> float:
        """Return the logical width before DPI scaling."""

        return self.width_px / self.dpi_scale

    @property
    def logical_height_px(self) -> float:
        """Return the logical height before DPI scaling."""

        return self.height_px / self.dpi_scale


@dataclass(slots=True, frozen=True, kw_only=True)
class ScreenPoint:
    """A physical screen point in virtual desktop coordinates."""

    x_px: int
    y_px: int


@dataclass(slots=True, frozen=True, kw_only=True)
class ScreenBBox:
    """A physical screen bounding box in virtual desktop coordinates."""

    left_px: int
    top_px: int
    width_px: int
    height_px: int

    def __post_init__(self) -> None:
        if self.width_px < 0:
            raise ValueError("width_px must be non-negative.")
        if self.height_px < 0:
            raise ValueError("height_px must be non-negative.")

    @property
    def right_px(self) -> int:
        """Return the exclusive right edge in virtual desktop coordinates."""

        return self.left_px + self.width_px

    @property
    def bottom_px(self) -> int:
        """Return the exclusive bottom edge in virtual desktop coordinates."""

        return self.top_px + self.height_px


@dataclass(slots=True, frozen=True, kw_only=True)
class VirtualDesktopMetrics:
    """A multi-monitor-safe view of the virtual desktop layout."""

    displays: tuple[ScreenMetrics, ...]

    def __post_init__(self) -> None:
        if not self.displays:
            raise ValueError("Virtual desktop must include at least one display.")

        display_ids = {display.display_id for display in self.displays}
        if len(display_ids) != len(self.displays):
            raise ValueError("Display identifiers must be unique.")

        primary_count = sum(display.is_primary for display in self.displays)
        if primary_count > 1:
            raise ValueError("Virtual desktop can have at most one primary display.")

    @property
    def primary_display(self) -> ScreenMetrics:
        """Return the designated primary display or the first display."""

        for display in self.displays:
            if display.is_primary:
                return display
        return self.displays[0]

    @property
    def bounds(self) -> ScreenBBox:
        """Return the bounding box that encloses every display."""

        left = min(display.origin_x_px for display in self.displays)
        top = min(display.origin_y_px for display in self.displays)
        right = max(display.right_px for display in self.displays)
        bottom = max(display.bottom_px for display in self.displays)
        return ScreenBBox(
            left_px=left,
            top_px=top,
            width_px=right - left,
            height_px=bottom - top,
        )
