"""
engine.ai.pathfinding
====================
Grid A* pathfinding + line-of-sight over a tilemap's solidity function.

Both take ``is_solid(tx, ty) -> bool`` (e.g. ``tilemap.is_solid_tile``) so they
work against any map-like object, including the chunk-streaming stub. 4-directional
movement keeps paths wall-hugging and cheap; the AI moves smoothly toward each
node centre. ``find_path`` is bounded by ``max_expansions`` so a hunt on a huge map
can never stall a frame.
"""

from __future__ import annotations

import heapq
from typing import Callable, List, Tuple

Tile = Tuple[int, int]
_NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _heuristic(a: Tile, b: Tile) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])  # Manhattan


def find_path(is_solid: Callable[[int, int], bool], start: Tile, goal: Tile,
              max_expansions: int = 1500) -> List[Tile]:
    """A* from ``start`` to ``goal`` (tiles). Returns the tiles AFTER start up to
    and including goal, or [] if unreachable / goal is solid."""
    if start == goal or is_solid(*goal):
        return []
    open_heap = [(_heuristic(start, goal), 0, start)]
    came = {start: None}
    gscore = {start: 0}
    expansions = 0
    while open_heap:
        _, g, cur = heapq.heappop(open_heap)
        if cur == goal:
            return _reconstruct(came, cur)
        expansions += 1
        if expansions > max_expansions:
            break
        for dx, dy in _NEIGHBOURS:
            nb = (cur[0] + dx, cur[1] + dy)
            if is_solid(nb[0], nb[1]):
                continue
            ng = g + 1
            if nb not in gscore or ng < gscore[nb]:
                gscore[nb] = ng
                came[nb] = cur
                heapq.heappush(open_heap, (ng + _heuristic(nb, goal), ng, nb))
    return []


def _reconstruct(came, cur) -> List[Tile]:
    path = []
    while came[cur] is not None:
        path.append(cur)
        cur = came[cur]
    path.reverse()
    return path


def has_line_of_sight(is_solid: Callable[[int, int], bool], a: Tile, b: Tile) -> bool:
    """True if no solid tile blocks the straight line between tiles a and b."""
    x0, y0 = a
    x1, y1 = b
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while (x0, y0) != (x1, y1):
        if (x0, y0) != a and is_solid(x0, y0):
            return False
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return True
