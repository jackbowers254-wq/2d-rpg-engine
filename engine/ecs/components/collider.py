"""
Axis-aligned collision box, offset from the entity transform.

Two independent flags model the two common needs:
- ``solid``  : blocks movement (walls, NPCs you bump into).
- ``trigger``: fires an interaction/overlap event instead of blocking (warp
  tiles, item pickups, damage zones). ``trigger_event`` names the event the
  scene/systems listen for.

Keeping the box separate from the sprite lets the *visual* be 16x16 while the
*hitbox* is a smaller 12x8 "feet" box -- which feels far better in a top-down RPG.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from engine.ecs.component import Component, component


@component("collider")
@dataclass
class ColliderComponent(Component):
    w: float = 16.0
    h: float = 16.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    solid: bool = True
    trigger: bool = False
    trigger_event: Optional[str] = None

    def rect(self, x: float, y: float):
        """Return (x, y, w, h) of this collider for a transform at (x, y)."""
        return (x + self.offset_x, y + self.offset_y, self.w, self.h)
