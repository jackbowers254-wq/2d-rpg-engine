"""
engine.utils.tween
================
Easing functions + a tiny Tween for time-based interpolation. Used for UI motion,
sprite hops, hit-flash decay, screen-shake falloff and scene transitions. Works on
scalars or equal-length sequences (interpolated component-wise).
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Sequence, Union

Number = Union[float, Sequence[float]]


def linear(t: float) -> float:
    return t


def ease_in_quad(t: float) -> float:
    return t * t


def ease_out_quad(t: float) -> float:
    return 1 - (1 - t) * (1 - t)


def ease_in_out_quad(t: float) -> float:
    return 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2


def ease_out_back(t: float) -> float:
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out_bounce(t: float) -> float:
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    if t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


EASINGS: Dict[str, Callable[[float], float]] = {
    "linear": linear,
    "ease_in": ease_in_quad,
    "ease_out": ease_out_quad,
    "ease_in_out": ease_in_out_quad,
    "ease_out_back": ease_out_back,
    "ease_out_bounce": ease_out_bounce,
}


def _lerp(a, b, t):
    if isinstance(a, (int, float)):
        return a + (b - a) * t
    return [av + (bv - av) * t for av, bv in zip(a, b)]


class Tween:
    def __init__(self, start: Number, end: Number, duration: float,
                 easing: str = "linear", on_complete: Optional[Callable] = None) -> None:
        self.start = start
        self.end = end
        self.duration = max(1e-6, duration)
        self.ease = EASINGS.get(easing, linear)
        self.on_complete = on_complete
        self.elapsed = 0.0
        self.value = start
        self.done = False

    def update(self, dt: float) -> Number:
        if self.done:
            return self.value
        self.elapsed += dt
        t = min(1.0, self.elapsed / self.duration)
        self.value = _lerp(self.start, self.end, self.ease(t))
        if t >= 1.0:
            self.done = True
            self.value = self.end
            if self.on_complete:
                self.on_complete()
        return self.value
