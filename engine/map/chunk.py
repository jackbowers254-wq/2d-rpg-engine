"""
engine.map.chunk
===============
EXTENSION HOOK / STUB: chunked, streamed map loading for VERY large worlds.

The demo loads each map whole (fine for hand-made maps up to thousands of tiles,
since rendering is view-culled). For an effectively endless world you instead
keep only the chunks near the player resident and stream the rest in/out.

This module defines the *seam* so you can add that later without disturbing the
rest of the engine: a streamer exposes the SAME ``is_solid_tile`` /
tile-query / ``draw`` surface that :class:`~engine.map.tilemap.TileMap` does, so
movement, collision and rendering keep working against the interface. Config
lives under ``map_streaming`` (enabled, chunk_size, load_radius).

What a full implementation would add:
- a chunk = a TileMap-shaped slice of fixed ``chunk_size`` tiles,
- a provider that loads a chunk from disk / generates it procedurally on demand,
- an LRU of resident chunks around the player (``load_radius``),
- background loading so streaming never stalls the frame.

Below is a working *single-source* skeleton that satisfies the interface by
delegating to an already-loaded TileMap. Swap the provider for a real
disk/procedural one to go infinite.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

from engine.map.tilemap import TileMap


class ChunkProvider:
    """Supplies a TileMap chunk for a given chunk coordinate. Override ``load``."""

    def load(self, cx: int, cy: int) -> Optional[TileMap]:  # pragma: no cover - stub
        raise NotImplementedError


class StreamedWorld:
    """Interface-compatible stand-in for a TileMap, backed by streamed chunks.

    Only the surface other systems rely on is sketched here. The included
    behaviour simply forwards to a single base map, proving the seam; replace the
    provider + resident-set logic to actually stream.
    """

    def __init__(self, settings, provider: ChunkProvider, base: Optional[TileMap] = None) -> None:
        cs = settings.get("map_streaming.chunk_size", [32, 32])
        self.chunk_w, self.chunk_h = cs
        self.load_radius = settings.get("map_streaming.load_radius", 1)
        self.tile_size = settings.get("world.tile_size", 16)
        self._provider = provider
        self._resident: Dict[Tuple[int, int], TileMap] = {}
        self._base = base  # skeleton fallback

    # -- the TileMap-shaped surface other systems use ------------------------
    def update_streaming(self, player_tile_x: int, player_tile_y: int) -> None:
        """Load chunks within ``load_radius`` of the player; evict the rest."""
        # TODO: compute needed chunk coords, call provider.load, drop far chunks.
        ...

    def is_solid_tile(self, tx: int, ty: int) -> bool:
        if self._base is not None:
            return self._base.is_solid_tile(tx, ty)
        chunk, lx, ly = self._chunk_for(tx, ty)
        return chunk.is_solid_tile(lx, ly) if chunk else True

    def _chunk_for(self, tx: int, ty: int):
        cx, cy = tx // self.chunk_w, ty // self.chunk_h
        chunk = self._resident.get((cx, cy))
        return chunk, tx - cx * self.chunk_w, ty - cy * self.chunk_h

    def draw(self, renderer, camera) -> None:
        if self._base is not None:
            self._base.draw(renderer, camera)
        # TODO: draw each resident chunk offset to its world position.
