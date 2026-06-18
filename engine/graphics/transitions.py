"""
engine.graphics.transitions
==========================
Short full-screen transitions for scene/map changes: ``fade``, ``wipe`` and a
chunky ``pixel`` dissolve tuned for pixel art (whole cells, not soft gradients).

A transition has two halves: COVER (screen fills in) then REVEAL (screen clears).
``on_cover`` fires once at the fully-covered midpoint -- that's where the caller
swaps the map/scene, so the change is hidden. Drawn on the ``overlay`` layer in
logical pixels, so it scales and stays crisp with the rest of the render.

Usage:
    t = Transition("pixel", 0.45, color=(0,0,0), on_cover=do_the_swap)
    # each frame: if t.update(dt): t = None   ; and  t.draw(renderer)
"""

from __future__ import annotations

import random
from typing import Callable, List, Optional, Tuple


class Transition:
    def __init__(self, kind: str = "fade", duration: float = 0.5,
                 color: Tuple[int, int, int] = (0, 0, 0), cell: int = 8,
                 on_cover: Optional[Callable] = None) -> None:
        self.kind = kind
        self.duration = max(0.02, duration)
        self.color = tuple(color)
        self.cell = max(1, cell)
        self.on_cover = on_cover
        self.t = 0.0
        self._covered = False
        self.done = False
        self._order: Optional[List[int]] = None  # cell reveal order (pixel kind)

    @property
    def covering(self) -> bool:
        """True until the swap point (lets the caller freeze the world)."""
        return not self.done

    def update(self, dt: float) -> bool:
        self.t += dt
        half = self.duration / 2
        if not self._covered and self.t >= half:
            self._covered = True
            if self.on_cover:
                self.on_cover()  # swap map/scene exactly when fully covered
        if self.t >= self.duration:
            self.done = True
        return self.done

    def _coverage(self) -> float:
        half = self.duration / 2
        if self.t < half:
            return self.t / half          # 0 -> 1 (cover)
        return max(0.0, 1.0 - (self.t - half) / half)  # 1 -> 0 (reveal)

    def draw(self, renderer) -> None:
        bw, bh = renderer.base_size
        c = self._coverage()
        if c <= 0:
            return
        if self.kind == "wipe":
            renderer.draw_rect((0, 0, int(bw * c), bh), self.color,
                               layer="overlay", world=False)
        elif self.kind == "pixel":
            self._draw_pixel(renderer, bw, bh, c)
        else:  # fade (default)
            renderer.draw_rect((0, 0, bw, bh), (*self.color, int(255 * c)),
                               layer="overlay", world=False)

    def _draw_pixel(self, renderer, bw, bh, c) -> None:
        cols = bw // self.cell + 1
        rows = bh // self.cell + 1
        n = cols * rows
        if self._order is None:
            self._order = list(range(n))
            random.Random(1337).shuffle(self._order)  # fixed order: cover/reveal symmetric
        count = int(n * c)
        for idx in self._order[:count]:
            cx = (idx % cols) * self.cell
            cy = (idx // cols) * self.cell
            renderer.draw_rect((cx, cy, self.cell, self.cell), self.color,
                               layer="overlay", world=False)
