"""
engine.graphics.spritesheet
==========================
A sprite sheet = one atlas image + a list of frame rectangles. Frames can be
defined by a regular grid (``from_grid``) or by explicit rects (e.g. parsed from
an Aseprite export, where frames may be packed/trimmed irregularly).

Slicing returns cached ``subsurface`` views, so no pixels are copied. The asset
manager owns the atlas surface; this class only indexes into it.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import pygame

Rect = Tuple[int, int, int, int]


class SpriteSheet:
    def __init__(self, atlas: pygame.Surface, frames: List[Rect]) -> None:
        self.atlas = atlas
        self.frames = frames  # ordered list of (x, y, w, h)
        self._cache: Dict[int, pygame.Surface] = {}

    @classmethod
    def from_grid(cls, atlas: pygame.Surface, frame_w: int, frame_h: int,
                  *, margin: int = 0, spacing: int = 0) -> "SpriteSheet":
        """Slice a regular grid (left-to-right, top-to-bottom)."""
        frames: List[Rect] = []
        aw, ah = atlas.get_size()
        y = margin
        while y + frame_h <= ah:
            x = margin
            while x + frame_w <= aw:
                frames.append((x, y, frame_w, frame_h))
                x += frame_w + spacing
            y += frame_h + spacing
        return cls(atlas, frames)

    def __len__(self) -> int:
        return len(self.frames)

    def frame(self, index: int) -> pygame.Surface:
        """Return the sub-surface for frame ``index`` (cached, clamped)."""
        if not self.frames:
            return self.atlas
        index = max(0, min(index, len(self.frames) - 1))
        surf = self._cache.get(index)
        if surf is None:
            surf = self.atlas.subsurface(pygame.Rect(self.frames[index]))
            self._cache[index] = surf
        return surf
