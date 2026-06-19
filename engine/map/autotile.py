"""
engine.map.autotile
=================
Autotiling: pick each tile's edges/corners automatically from its neighbours, so
terrain (water, paths, cliffs) shows correct shorelines/borders without the
designer placing every edge tile by hand.

A tile layer opts in with a custom property ``autotile: true`` (optionally
``edge_color: "#rrggbb"``). For each filled cell we compute the 4-neighbour mask
(which N/E/S/W neighbours are the SAME terrain in that layer) and render a variant
that draws an edge band on every OPEN side (a shoreline). 16 variants are cached
per terrain. This is the data-driven "blob/wang" idea, kept lightweight and
art-free (variants are generated from the tile's colour); for hand-drawn art the
same masks would index a 47-tile blob set in your tileset instead.

Collision is unaffected -- only the rendered surface is overridden, so a solid
water tile stays solid.
"""

from __future__ import annotations

from typing import Dict, Tuple

import pygame

# Neighbour bits.
_N, _E, _S, _W = 1, 2, 4, 8


def _lighten(color, amt=60):
    return tuple(min(255, c + amt) for c in color[:3])


def _variant(mask: int, base, edge, ts: int, cache: Dict) -> pygame.Surface:
    key = (mask, base, edge, ts)
    surf = cache.get(key)
    if surf is not None:
        return surf
    surf = pygame.Surface((ts, ts))
    surf.fill(base)
    band = max(2, ts // 6)
    # Draw an edge band on each OPEN side (no same-terrain neighbour there).
    if not mask & _N:
        surf.fill(edge, (0, 0, ts, band))
    if not mask & _S:
        surf.fill(edge, (0, ts - band, ts, band))
    if not mask & _W:
        surf.fill(edge, (0, 0, band, ts))
    if not mask & _E:
        surf.fill(edge, (ts - band, 0, band, ts))
    cache[key] = surf
    return surf


def apply_autotiling(tilemap) -> None:
    """Populate ``layer.overrides`` for every autotile layer in the map."""
    cache: Dict = {}
    ts = tilemap.tile_size
    for layer in tilemap.layers:
        if not layer.properties.get("autotile"):
            continue
        # Base colour from the first tile id used in this layer.
        base = (60, 110, 180)
        for gid in layer.data:
            if gid:
                tdef = tilemap.catalog.get(gid)
                if tdef and tdef.color:
                    base = tuple(tdef.color)
                break
        edge_prop = layer.properties.get("edge_color")
        edge = _parse(edge_prop) if edge_prop else _lighten(base, 70)

        for ty in range(layer.height):
            for tx in range(layer.width):
                if layer.gid_at(tx, ty) == 0:
                    continue
                mask = 0
                if layer.gid_at(tx, ty - 1):
                    mask |= _N
                if layer.gid_at(tx + 1, ty):
                    mask |= _E
                if layer.gid_at(tx, ty + 1):
                    mask |= _S
                if layer.gid_at(tx - 1, ty):
                    mask |= _W
                layer.overrides[(tx, ty)] = _variant(mask, base, edge, ts, cache)


def _parse(value):
    from engine.map.tmx_loader import _parse_color
    return _parse_color(value) or (255, 255, 255)
