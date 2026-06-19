"""
engine.graphics.parallax
======================
Multi-layer parallax backgrounds with per-layer scroll speed (data-driven).

A background is a list of layers, each a dict in data; the layer's ``factor`` is
how fast it scrolls relative to the camera (0 = fixed sky, 1 = moves with the
world). Layer kinds (art-free, generated -- or supply an ``image``):

    {"kind": "fill",  "color": [...]}                      full-screen sky
    {"kind": "band",  "color": [...], "y": .., "height": ..} a horizontal band
    {"kind": "bumps", "color": [...], "y": .., "radius": .., "spacing": .., "factor": ..}
                                                            repeating hills/blobs
    {"kind": "dots",  "color": [...], "y": .., "y2": .., "size": .., "spacing": .., "factor": ..}
                                                            stars / specks
    {"kind": "image", "image": "sky.png", "y": .., "factor": .., "repeat": true}

Draw it on the ``background`` render layer (behind tiles): pass a scroll value
(camera x for a map, or time-based for a title screen). Visible wherever the world
above is transparent -- ideal for title screens, vistas, and side-scrollers.
"""

from __future__ import annotations

import random
from typing import List

import pygame


class ParallaxBackground:
    def __init__(self, layers: List[dict], assets=None) -> None:
        self.layers = layers or []
        self.assets = assets

    def draw(self, renderer, scroll_x: float, scroll_y: float = 0.0,
             layer: str = "background") -> None:
        bw, bh = renderer.base_size
        for L in self.layers:
            kind = L.get("kind", "fill")
            color = tuple(L.get("color", [0, 0, 0]))
            factor = L.get("factor", 0.0)
            off = scroll_x * factor

            if kind == "fill":
                renderer.draw_rect((0, 0, bw, bh), color, layer=layer, world=False)
            elif kind == "band":
                renderer.draw_rect((0, L.get("y", 0), bw, L.get("height", bh)), color,
                                   layer=layer, world=False)
            elif kind == "bumps":
                self._bumps(renderer, L, color, off, bw, bh, layer)
            elif kind == "dots":
                self._dots(renderer, L, color, off, bw, layer)
            elif kind == "image" and self.assets is not None:
                self._image(renderer, L, off, bw, layer)

    def _bumps(self, renderer, L, color, off, bw, bh, layer):
        spacing = L.get("spacing", 48)
        radius = L.get("radius", 24)
        y = L.get("y", bh - 20)
        start = -(off % spacing)
        x = start - spacing
        while x < bw + spacing:
            # A filled "hill" (half-blob): a square + circle reads as pixel-art.
            renderer.draw_rect((x, y, radius * 2, radius * 2), color, layer=layer, world=False)
            x += spacing

    def _dots(self, renderer, L, color, off, bw, layer):
        spacing = L.get("spacing", 20)
        size = L.get("size", 1)
        y1, y2 = L.get("y", 4), L.get("y2", 60)
        rnd = random.Random(L.get("seed", 1))
        start = -(off % spacing)
        x = start - spacing
        i = 0
        while x < bw + spacing:
            yy = y1 + (rnd.random() * (y2 - y1))
            renderer.draw_rect((x + (i * 7 % spacing), yy, size, size), color,
                               layer=layer, world=False)
            x += spacing
            i += 1

    def _image(self, renderer, L, off, bw, layer):
        img = self.assets.get_image(L["image"])
        iw = img.get_width()
        y = L.get("y", 0)
        start = -(off % iw)
        x = start - iw
        while x < bw + iw:
            renderer.draw_image(img, x, y, layer=layer, world=False)
            x += iw
