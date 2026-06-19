"""
engine.graphics.daynight
======================
A data-driven day/night cycle that produces a time-varying ambient colour for the
lighting system. Outdoor maps feed this colour to the LightingEffect as ambient,
so the world darkens and warms across the day and the player's torch matters at
night. Indoor maps that set their own ``ambient`` ignore it.

Config (``render.day_night``):
    {
      "enabled": true,
      "period": 120,                 # seconds for a full day
      "start": 0.15,                 # initial phase 0..1 (0.15 = morning)
      "keyframes": [                 # phase -> ambient colour (interpolated)
        {"t": 0.0,  "color": [255, 255, 255]},
        {"t": 0.45, "color": [235, 205, 180]},
        {"t": 0.6,  "color": [120, 110, 165]},
        {"t": 0.75, "color": [70, 75, 120]},
        {"t": 0.9,  "color": [120, 110, 165]}
      ]
    }
"""

from __future__ import annotations

from typing import List, Tuple

_DEFAULT_KEYS = [
    {"t": 0.0, "color": [255, 255, 255]},
    {"t": 0.45, "color": [235, 205, 180]},
    {"t": 0.6, "color": [120, 110, 165]},
    {"t": 0.75, "color": [70, 75, 120]},
    {"t": 0.9, "color": [120, 110, 165]},
]


class DayNightCycle:
    def __init__(self, settings) -> None:
        cfg = settings.get("render.day_night", {}) or {}
        self.enabled = cfg.get("enabled", False)
        self.period = max(1.0, cfg.get("period", 120))
        self.keys = sorted(cfg.get("keyframes", _DEFAULT_KEYS), key=lambda k: k["t"])
        self.time = cfg.get("start", 0.15) * self.period

    def update(self, dt: float) -> None:
        if self.enabled:
            self.time = (self.time + dt) % self.period

    @property
    def phase(self) -> float:
        return self.time / self.period

    def ambient(self) -> Tuple[int, int, int]:
        """Interpolate the keyframes (wrapping) at the current phase."""
        p = self.phase
        keys = self.keys
        if not keys:
            return (255, 255, 255)
        # Find the surrounding keyframes (wrapping around 1.0 -> 0.0).
        prev = keys[-1]
        nxt = keys[0]
        for i, k in enumerate(keys):
            if k["t"] > p:
                nxt = k
                prev = keys[i - 1] if i > 0 else keys[-1]
                break
        else:
            prev, nxt = keys[-1], keys[0]
        span = (nxt["t"] - prev["t"]) % 1.0 or 1.0
        local = ((p - prev["t"]) % 1.0) / span
        return tuple(int(a + (b - a) * local) for a, b in zip(prev["color"], nxt["color"]))
