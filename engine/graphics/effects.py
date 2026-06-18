"""
engine.graphics.effects
=======================
Concrete render effects that plug into the renderer's extension hooks
(``after_layer`` between layers, ``post_process`` after all layers). They are
OPTIONAL and config-gated (``render.effects_enabled`` + ``render.effects``), so a
simple game pays nothing for them.

- :class:`LightingEffect` -- a 2D lighting pass. A configurable ambient colour
  darkens the world (multiply), then point lights add light back (additive). Lights
  are updated each frame by game code (e.g. a torch following the player; lights
  placed as map objects). ``set_ambient`` drives day/night or per-map mood.
  Per-light textures are cached. Phase C extends this with quantized/banded
  light and normal maps for a true pixel-art look.

- :class:`ParticleSystem` -- a small additive particle pool tuned for pixel art
  (chunky square particles). ``emit`` / ``emit_burst`` from anywhere (combat hits,
  pickups, weather); call ``update`` each frame (the renderer does this).

Both register via ``renderer.add_effect(...)`` and need no changes elsewhere.
"""

from __future__ import annotations

import random
from typing import Dict, List, Tuple

import pygame

Color = Tuple[int, int, int]


class RenderEffect:
    """Base class for a pluggable rendering effect. Override the hooks you need."""

    enabled: bool = True

    def update(self, dt: float) -> None:
        """Advance time-based state (particles, day/night). Default: no-op."""

    def after_layer(self, layer_name: str, surface: pygame.Surface, renderer) -> None:
        """Called after ``layer_name`` is flushed. Default: no-op."""

    def post_process(self, surface: pygame.Surface, renderer) -> None:
        """Called once after all layers, before scaling. Default: no-op."""


class LightingEffect(RenderEffect):
    def __init__(self, after_layer_name: str = "overhead",
                 ambient: Color = (255, 255, 255)) -> None:
        self._after = after_layer_name
        self.ambient: Color = ambient
        # Each light: (world_x, world_y, radius, color)
        self.lights: List[Tuple[float, float, float, Color]] = []
        self._tex_cache: Dict[Tuple[int, Color], pygame.Surface] = {}

    # -- light management (called by game code each frame) -------------------
    def set_ambient(self, color: Color) -> None:
        self.ambient = tuple(color)

    def clear_lights(self) -> None:
        self.lights.clear()

    def add_light(self, world_x: float, world_y: float, radius: float,
                  color: Color = (255, 240, 200)) -> None:
        self.lights.append((world_x, world_y, radius, color))

    def _light_texture(self, radius: int, color: Color) -> pygame.Surface:
        key = (radius, color)
        tex = self._tex_cache.get(key)
        if tex is None:
            tex = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            # Smooth-ish radial falloff (Phase C banding makes this pixel-art crisp).
            for r in range(radius, 0, -1):
                a = int(255 * (1 - r / radius) ** 1.6)
                pygame.draw.circle(tex, (*color, a), (radius, radius), r)
            self._tex_cache[key] = tex
        return tex

    def after_layer(self, layer_name, surface, renderer):
        if not self.enabled or layer_name != self._after:
            return
        if self.ambient == (255, 255, 255) and not self.lights:
            return  # fully lit, nothing to do
        dark = pygame.Surface(surface.get_size())
        dark.fill(self.ambient)
        cam = renderer.camera
        ox, oy = cam.offset if cam else (0, 0)
        for wx, wy, radius, color in self.lights:
            tex = self._light_texture(int(radius), tuple(color))
            dark.blit(tex, (wx - ox - radius, wy - oy - radius),
                      special_flags=pygame.BLEND_RGB_ADD)
        surface.blit(dark, (0, 0), special_flags=pygame.BLEND_RGB_MULT)


class ParticleSystem(RenderEffect):
    def __init__(self, gravity: float = 0.0, chunky: int = 2) -> None:
        self.gravity = gravity
        self.chunky = chunky  # particle pixel size (>=2 reads as pixel-art)
        self._particles: List[dict] = []

    def emit(self, x, y, vx, vy, life, color=(255, 255, 255), size=None) -> None:
        self._particles.append(dict(x=x, y=y, vx=vx, vy=vy, life=life,
                                    max_life=life, color=tuple(color),
                                    size=size or self.chunky))

    def emit_burst(self, x, y, count=8, speed=40, life=0.4, color=(255, 230, 120),
                   spread=360) -> None:
        import math
        for _ in range(count):
            ang = math.radians(random.uniform(0, spread))
            sp = speed * random.uniform(0.4, 1.0)
            self.emit(x, y, math.cos(ang) * sp, math.sin(ang) * sp,
                      life * random.uniform(0.6, 1.0), color)

    def update(self, dt: float) -> None:
        for p in self._particles:
            p["vy"] += self.gravity * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
        if self._particles:
            self._particles = [p for p in self._particles if p["life"] > 0]

    def post_process(self, surface, renderer):
        if not self.enabled or not self._particles:
            return
        cam = renderer.camera
        ox, oy = cam.offset if cam else (0, 0)
        for p in self._particles:
            alpha = max(0.0, min(1.0, p["life"] / p["max_life"]))
            color = tuple(int(c * alpha) for c in p["color"])
            sx, sy = int(p["x"] - ox), int(p["y"] - oy)
            surface.fill(color, (sx, sy, p["size"], p["size"]),
                         special_flags=pygame.BLEND_RGB_ADD)
