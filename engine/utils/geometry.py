"""
engine.utils.geometry
=====================
Tiny math / geometry helpers used across the engine. Kept free of pygame so it
can be imported anywhere (including headless tools and tests).
"""

from __future__ import annotations

from enum import Enum
from typing import Tuple


def clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into the inclusive range ``[low, high]``."""
    return low if value < low else high if value > high else value


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation from ``a`` to ``b`` by factor ``t`` in [0, 1]."""
    return a + (b - a) * t


def sign(value: float) -> int:
    """Return -1, 0 or 1 according to the sign of ``value``."""
    return (value > 0) - (value < 0)


def aabb_overlap(
    ax: float, ay: float, aw: float, ah: float,
    bx: float, by: float, bw: float, bh: float,
) -> bool:
    """Return True if two axis-aligned bounding boxes overlap."""
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def rect_from_center(cx: float, cy: float, w: float, h: float) -> Tuple[float, float, float, float]:
    """Return ``(x, y, w, h)`` for a rect centred on ``(cx, cy)``."""
    return (cx - w / 2.0, cy - h / 2.0, w, h)


class Direction(Enum):
    """Four cardinal facing directions (handy for animation + interaction)."""

    DOWN = (0, 1)
    UP = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    @classmethod
    def from_vector(cls, dx: float, dy: float, fallback: "Direction") -> "Direction":
        """Pick the dominant cardinal direction from a movement vector."""
        if dx == 0 and dy == 0:
            return fallback
        if abs(dx) >= abs(dy):
            return cls.RIGHT if dx > 0 else cls.LEFT
        return cls.DOWN if dy > 0 else cls.UP
