"""
engine.graphics.palette
======================
Palettes + runtime palette swapping + quantization/dithering.

Two uses:
- **Recolour** a sprite at runtime by swapping a set of source colours for new
  ones (faction/variant tints, e.g. reusing the green slime art for a red hunter)
  -- no duplicate art. Swaps are data (``data/palettes/*.json``):
      {"hunter_red": {"#6ec878": "#d26e6e", "#469655": "#964646"}}
  Results are cached per (surface, swap).
- **Quantize** a surface to a fixed palette (optionally with ordered dithering)
  for a cohesive retro look -- used by the post-processing stack and useful when
  importing art.

Pure pygame, CPU-side; cheap because sprites are tiny and results are cached.
"""

from __future__ import annotations

import glob
import json
import os
from typing import Dict, List, Optional, Tuple

import pygame

from engine.utils.logger import get_logger

log = get_logger("palette")

# 4x4 Bayer matrix for ordered dithering (values 0..15).
_BAYER4 = [
    [0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5],
]


def _hex(c: str) -> Tuple[int, int, int]:
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


class PaletteManager:
    def __init__(self) -> None:
        self.swaps: Dict[str, Dict[str, str]] = {}
        self.palettes: Dict[str, List[Tuple[int, int, int]]] = {}
        self._recolor_cache: Dict[tuple, pygame.Surface] = {}

    # -- loading -------------------------------------------------------------
    def load_dir(self, directory: str) -> None:
        for path in glob.glob(os.path.join(directory, "*.json")):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for key, value in data.items():
                if key.startswith("_"):
                    continue
                if isinstance(value, dict):          # a colour swap map
                    self.swaps[key] = value
                elif isinstance(value, list):         # a named palette
                    self.palettes[key] = [_hex(c) for c in value]
        log.info("Loaded %d palette swaps, %d palettes",
                 len(self.swaps), len(self.palettes))

    # -- recolour ------------------------------------------------------------
    def recolor(self, surface: pygame.Surface, swap_id: str) -> pygame.Surface:
        swap = self.swaps.get(swap_id)
        if not swap:
            return surface
        key = (id(surface), swap_id)
        cached = self._recolor_cache.get(key)
        if cached is not None:
            return cached
        out = surface.copy()
        arr = pygame.PixelArray(out)
        for src, dst in swap.items():
            arr.replace(pygame.Color(*_hex(src)), pygame.Color(*_hex(dst)), 0.02)
        arr.close()
        self._recolor_cache[key] = out
        return out

    # -- quantize / dither ---------------------------------------------------
    def quantize(self, surface: pygame.Surface, palette_id: str,
                 dither: bool = False) -> pygame.Surface:
        palette = self.palettes.get(palette_id)
        if not palette:
            return surface
        out = surface.copy()
        arr = pygame.PixelArray(out)
        w, h = out.get_size()
        for y in range(h):
            for x in range(w):
                r, g, b, a = out.unmap_rgb(arr[x, y])
                if a == 0:
                    continue
                if dither:
                    t = (_BAYER4[y % 4][x % 4] / 16.0 - 0.5) * 24
                    r, g, b = r + t, g + t, b + t
                arr[x, y] = out.map_rgb(_nearest(palette, r, g, b))
        arr.close()
        return out


def _nearest(palette, r, g, b):
    best, bd = palette[0], 1e18
    for pr, pg, pb in palette:
        d = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2
        if d < bd:
            bd, best = d, (pr, pg, pb)
    return best
