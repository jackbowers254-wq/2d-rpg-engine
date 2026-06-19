"""
Visual representation of an entity.

Keeps it data-driven and art-optional: a sprite is either an image (``image``
path, resolved + cached by the AssetManager) OR a solid colour box (``color`` +
``size``). The demo uses colour boxes exclusively, so it runs with no art files.

``layer`` selects which configured draw layer the sprite goes on; ``offset``
nudges the visual relative to the transform (e.g. to centre a 12x14 body on a
16px tile). The render system caches the resolved surface on the component.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from engine.ecs.component import Component, component


@component("sprite")
@dataclass
class SpriteComponent(Component):
    # One of these two describes the look:
    image: Optional[str] = None              # path relative to assets/sprites
    color: Optional[List[int]] = None        # RGBA/RGB fallback box colour
    size: List[int] = field(default_factory=lambda: [16, 16])  # w,h in logical px

    layer: Optional[str] = None              # None -> renderer's default layer
    offset: List[int] = field(default_factory=lambda: [0, 0])  # draw offset (px)
    visible: bool = True
    y_sort: bool = True                      # sort by feet within y-sort layers
    palette: Optional[str] = None            # runtime palette-swap id (recolour)

    def __post_init__(self) -> None:
        # Runtime-only cache of the resolved pygame surface (not serialized).
        self._surface = None

    def to_data(self) -> dict:
        return {
            "image": self.image, "color": self.color, "size": self.size,
            "layer": self.layer, "offset": self.offset,
            "visible": self.visible, "y_sort": self.y_sort, "palette": self.palette,
        }
