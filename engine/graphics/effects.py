"""
engine.graphics.effects
=======================
EXTENSION HOOKS for advanced graphics.

The brief asks for *clearly marked extension hooks so I can ADD advanced graphics
later -- dynamic lighting, shaders, particle effects, animations,
post-processing -- without touching the rest of the engine.*

This module defines the contract for those additions. A :class:`RenderEffect` is
registered on the renderer via ``renderer.add_effect(...)`` and is called at two
well-defined points every frame (see ``PygameRenderer.end_frame``):

- ``after_layer(layer_name, surface, renderer)`` -- runs right after a specific
  layer is flushed. Use this for effects that must sit between layers, e.g. a
  lighting/shadow pass over the world but beneath the UI.
- ``post_process(surface, renderer)`` -- runs once after ALL layers, just before
  the base surface is scaled to the window. Use this for full-frame effects:
  bloom, colour grading, vignette, CRT/scanlines, screen shake, transitions.

Both receive the logical *base surface* (e.g. 320x180); mutate it in place. None
of the rest of the engine needs to change to add an effect -- you just write a
new RenderEffect subclass and register it.

The two classes below are working-but-deliberately-simple stubs that prove the
seam. Replace their internals (or swap the whole renderer for an OpenGL/moderngl
one) to raise fidelity.
"""

from __future__ import annotations

from typing import List, Tuple

import pygame


class RenderEffect:
    """Base class for a pluggable rendering effect. Override either hook."""

    enabled: bool = True

    def after_layer(self, layer_name: str, surface: pygame.Surface, renderer) -> None:
        """Called after ``layer_name`` is flushed. Default: no-op."""

    def post_process(self, surface: pygame.Surface, renderer) -> None:
        """Called once after all layers, before scaling. Default: no-op."""


class LightingEffect(RenderEffect):
    """STUB dynamic-lighting pass.

    Demonstrates a between-layers hook: it multiplies a darkness overlay onto the
    world after the configured layer, then 'cuts holes' for each registered light
    using additive blending. This is intentionally minimal -- a real
    implementation would use normal maps, soft shadows, coloured lights, etc.
    """

    def __init__(self, after_layer_name: str = "overhead",
                 ambient: Tuple[int, int, int] = (40, 40, 60)) -> None:
        self._after = after_layer_name
        self._ambient = ambient
        # Each light: (world_x, world_y, radius, color)
        self.lights: List[Tuple[float, float, float, Tuple[int, int, int]]] = []

    def add_light(self, world_x: float, world_y: float, radius: float,
                  color: Tuple[int, int, int] = (255, 240, 200)) -> None:
        self.lights.append((world_x, world_y, radius, color))

    def after_layer(self, layer_name, surface, renderer):
        if not self.enabled or layer_name != self._after:
            return
        # Darkness overlay (multiplicative).
        dark = pygame.Surface(surface.get_size())
        dark.fill(self._ambient)
        # Punch lights as additive radial blobs.
        cam = renderer.camera
        ox, oy = cam.offset if cam else (0, 0)
        for wx, wy, radius, color in self.lights:
            light = pygame.Surface((int(radius * 2), int(radius * 2)), pygame.SRCALPHA)
            for r in range(int(radius), 0, -2):
                a = int(255 * (1 - r / radius))
                pygame.draw.circle(light, (*color, a), (int(radius), int(radius)), r)
            dark.blit(light, (wx - ox - radius, wy - oy - radius), special_flags=pygame.BLEND_RGB_ADD)
        surface.blit(dark, (0, 0), special_flags=pygame.BLEND_RGB_MULT)


class ParticleSystem(RenderEffect):
    """STUB particle system.

    A self-contained, additive-blended particle pool drawn during post-process.
    Spawn particles from anywhere (combat hits, footsteps, weather) via
    :meth:`emit`. Replace with a richer system (textured sprites, gravity,
    GPU instancing) as needed -- the registration seam stays identical.
    """

    def __init__(self) -> None:
        # Each particle: dict(x, y, vx, vy, life, max_life, color, size)
        self._particles: List[dict] = []

    def emit(self, x, y, vx, vy, life, color=(255, 255, 255), size=1) -> None:
        self._particles.append(
            dict(x=x, y=y, vx=vx, vy=vy, life=life, max_life=life, color=color, size=size)
        )

    def update(self, dt: float) -> None:
        """Advance the simulation. Call from a scene's update()."""
        for p in self._particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
        self._particles = [p for p in self._particles if p["life"] > 0]

    def post_process(self, surface, renderer):
        if not self.enabled:
            return
        cam = renderer.camera
        ox, oy = cam.offset if cam else (0, 0)
        for p in self._particles:
            alpha = max(0.0, min(1.0, p["life"] / p["max_life"]))
            color = tuple(int(c * alpha) for c in p["color"])
            sx, sy = int(p["x"] - ox), int(p["y"] - oy)
            surface.fill(color, (sx, sy, p["size"], p["size"]),
                         special_flags=pygame.BLEND_RGB_ADD)
