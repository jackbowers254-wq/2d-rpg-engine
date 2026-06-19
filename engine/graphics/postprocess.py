"""
engine.graphics.postprocess
=========================
A configurable, toggleable retro post-processing chain applied on the CPU to the
small base surface (cheap, before upscaling -- and authentically pixelated). Each
effect is OFF by default; enable per effect in ``render.post``:

    "post": {
      "scanlines": {"enabled": true, "intensity": 0.25},
      "vignette":  {"enabled": true, "intensity": 0.5},
      "chromatic": {"enabled": false, "offset": 1},
      "bloom":     {"enabled": true, "strength": 70, "scale": 4},
      "color_grade": {"enabled": false, "tint": [255, 240, 220]}
    }

Order (post_process): bloom -> color grade -> chromatic aberration -> vignette ->
scanlines. Overlays (scanlines/vignette) are precomputed once at the base size.
Runtime toggling via :meth:`toggle` (e.g. from a debug key). No new dependency --
just pygame surface blends.
"""

from __future__ import annotations

from typing import Dict, Optional

import pygame

from engine.graphics.effects import RenderEffect
from engine.utils.logger import get_logger

log = get_logger("postfx")


class PostProcessStack(RenderEffect):
    def __init__(self, settings) -> None:
        self.cfg: Dict[str, dict] = settings.get("render.post", {}) or {}
        self._scanline_tex: Optional[pygame.Surface] = None
        self._vignette_tex: Optional[pygame.Surface] = None

    def _on(self, name: str) -> bool:
        return bool(self.cfg.get(name, {}).get("enabled", False))

    def toggle(self, name: str) -> bool:
        self.cfg.setdefault(name, {})["enabled"] = not self._on(name)
        return self._on(name)

    def toggle_preset(self) -> bool:
        """Flip a tasteful CRT preset (scanlines + vignette + bloom) on/off."""
        preset = ("scanlines", "vignette", "bloom")
        on = not any(self._on(n) for n in preset)
        for n in preset:
            self.cfg.setdefault(n, {})["enabled"] = on
        return on

    @property
    def any_enabled(self) -> bool:
        return any(self._on(n) for n in
                   ("scanlines", "vignette", "chromatic", "bloom", "color_grade"))

    # -- precomputed overlays ------------------------------------------------
    def _scanlines(self, size) -> pygame.Surface:
        if self._scanline_tex is None or self._scanline_tex.get_size() != size:
            w, h = size
            tex = pygame.Surface(size)
            tex.fill((255, 255, 255))
            dark = int(255 * (1 - self.cfg.get("scanlines", {}).get("intensity", 0.25)))
            for y in range(0, h, 2):
                pygame.draw.line(tex, (dark, dark, dark), (0, y), (w, y))
            self._scanline_tex = tex
        return self._scanline_tex

    def _vignette(self, size) -> pygame.Surface:
        if self._vignette_tex is None or self._vignette_tex.get_size() != size:
            intensity = self.cfg.get("vignette", {}).get("intensity", 0.5)
            # Compute on a small grid then smoothscale up (fast + smooth).
            sw, sh = 40, 24
            small = pygame.Surface((sw, sh))
            cx, cy = sw / 2, sh / 2
            maxd = (cx ** 2 + cy ** 2) ** 0.5
            for y in range(sh):
                for x in range(sw):
                    d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / maxd
                    v = int(255 * (1 - intensity * (d ** 2)))
                    small.set_at((x, y), (v, v, v))
            self._vignette_tex = pygame.transform.smoothscale(small, size)
        return self._vignette_tex

    # -- effects -------------------------------------------------------------
    def post_process(self, surface, renderer):
        if not self.any_enabled:
            return
        size = surface.get_size()
        if self._on("bloom"):
            self._apply_bloom(surface)
        if self._on("color_grade"):
            tint = self.cfg["color_grade"].get("tint", [255, 255, 255])
            surface.fill(tuple(tint), special_flags=pygame.BLEND_RGB_MULT)
        if self._on("chromatic"):
            self._apply_chromatic(surface)
        if self._on("vignette"):
            surface.blit(self._vignette(size), (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        if self._on("scanlines"):
            surface.blit(self._scanlines(size), (0, 0), special_flags=pygame.BLEND_RGB_MULT)

    def _apply_bloom(self, surface):
        cfg = self.cfg["bloom"]
        scale = max(2, cfg.get("scale", 4))
        strength = cfg.get("strength", 70)
        w, h = surface.get_size()
        small = pygame.transform.smoothscale(surface, (w // scale, h // scale))
        blur = pygame.transform.smoothscale(small, (w, h))
        blur.fill((strength, strength, strength), special_flags=pygame.BLEND_RGB_MULT)
        surface.blit(blur, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def _apply_chromatic(self, surface):
        off = self.cfg["chromatic"].get("offset", 1)
        red = surface.copy(); red.fill((255, 0, 0), special_flags=pygame.BLEND_RGB_MULT)
        green = surface.copy(); green.fill((0, 255, 0), special_flags=pygame.BLEND_RGB_MULT)
        blue = surface.copy(); blue.fill((0, 0, 255), special_flags=pygame.BLEND_RGB_MULT)
        surface.fill((0, 0, 0))
        surface.blit(green, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        surface.blit(red, (off, 0), special_flags=pygame.BLEND_RGB_ADD)
        surface.blit(blue, (-off, 0), special_flags=pygame.BLEND_RGB_ADD)
