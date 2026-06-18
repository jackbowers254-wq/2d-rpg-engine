"""
engine.ecs.systems.collision
============================
Collision helpers shared by movement and triggers. Two collision sources:

- the tilemap's solid tiles (walls, water, cliffs) -- see ``rect_hits_tiles``,
- other entities' *solid* colliders (NPCs, pushable crates) -- see ``rect_hits_solids``.

Movement is resolved per-axis (move X, undo X if blocked; then move Y, undo Y if
blocked). Resolving axes independently is what gives smooth "wall sliding": when
you walk diagonally into a wall, the blocked axis cancels while the free axis
keeps moving. dt is clamped in the game loop, so at normal speeds nothing tunnels
through a tile; if you add very fast entities, swap this for a swept-AABB test
(the call sites won't change).
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

from engine.utils.geometry import aabb_overlap

Rect = Tuple[float, float, float, float]


def rect_hits_tiles(rect: Rect, tilemap) -> bool:
    """True if any solid tile overlaps ``rect`` (x, y, w, h in world px)."""
    if tilemap is None:
        return False
    x, y, w, h = rect
    ts = tilemap.tile_size
    left = int(math.floor(x / ts))
    right = int(math.floor((x + w - 1e-6) / ts))
    top = int(math.floor(y / ts))
    bottom = int(math.floor((y + h - 1e-6) / ts))
    for ty in range(top, bottom + 1):
        for tx in range(left, right + 1):
            if tilemap.is_solid_tile(tx, ty):
                return True
    return False


def rect_hits_solids(rect: Rect, solids: List[Tuple[int, Rect]], ignore_id: int) -> bool:
    """True if ``rect`` overlaps any solid collider in ``solids`` (id, rect)."""
    ax, ay, aw, ah = rect
    for eid, (bx, by, bw, bh) in solids:
        if eid == ignore_id:
            continue
        if aabb_overlap(ax, ay, aw, ah, bx, by, bw, bh):
            return True
    return False


def is_blocked(rect: Rect, tilemap, solids, ignore_id: int) -> bool:
    return rect_hits_tiles(rect, tilemap) or rect_hits_solids(rect, solids, ignore_id)
