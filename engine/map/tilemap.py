"""
engine.map.tilemap
=================
In-memory representation of a single map plus its rendering and collision.

A map is:
- a stack of TILE LAYERS (each a flat array of tile ids), drawn bottom-to-top on
  the engine's configured render layers,
- a set of OBJECT GROUPS holding rectangles/points with arbitrary properties
  (spawns, portals, triggers, item placements, NPC markers...),
- a TILE CATALOG mapping each tile id to its look (a colour box or an image
  region) and whether it blocks movement.

NO DIMENSIONS ARE HARDCODED: width/height/tile size all come from the map data,
so maps can be any size. Collision is precomputed into a boolean grid for O(1)
lookups during movement. Rendering is view-culled, so map size doesn't affect
per-frame cost (only what's on screen is drawn) -- which is what makes large
maps, and later chunk streaming, cheap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pygame


@dataclass
class TileDef:
    """How one tile id looks and behaves."""
    solid: bool = False
    color: Optional[Tuple[int, int, int]] = None       # placeholder box colour
    image: Optional[pygame.Surface] = None             # or a real tile image


@dataclass
class TileLayer:
    name: str
    width: int
    height: int
    data: List[int]                                    # flat row-major tile ids (0 = empty)
    render_layer: str = "ground"                       # which engine draw layer
    visible: bool = True
    collision: bool = False                            # whole layer marks solidity
    properties: Dict = field(default_factory=dict)

    def gid_at(self, tx: int, ty: int) -> int:
        if 0 <= tx < self.width and 0 <= ty < self.height:
            return self.data[ty * self.width + tx]
        return 0


@dataclass
class MapObject:
    name: str
    type: str
    x: float            # pixels (top-left for rectangles)
    y: float
    width: float
    height: float
    properties: Dict = field(default_factory=dict)

    @property
    def center(self) -> Tuple[float, float]:
        return (self.x + self.width / 2.0, self.y + self.height / 2.0)


class TileMap:
    def __init__(self, name: str, width: int, height: int, tile_size: int) -> None:
        self.name = name
        self.width = width        # in tiles
        self.height = height
        self.tile_size = tile_size
        self.layers: List[TileLayer] = []
        self.object_groups: Dict[str, List[MapObject]] = {}
        self.catalog: Dict[int, TileDef] = {0: TileDef()}
        self.properties: Dict = {}
        # If True, the area outside the map blocks movement (so you can't walk off
        # the edge except through a portal). Configurable per map.
        self.edge_solid: bool = True
        # Precomputed solidity grid (filled by finalize()).
        self._solid: List[bool] = []
        # Lazily-built colour-tile surfaces for fast blitting.
        self._tile_surfaces: Dict[int, pygame.Surface] = {}

    # -- dimensions ----------------------------------------------------------
    @property
    def pixel_width(self) -> int:
        return self.width * self.tile_size

    @property
    def pixel_height(self) -> int:
        return self.height * self.tile_size

    # -- build ---------------------------------------------------------------
    def finalize(self) -> None:
        """Precompute the collision grid from collision layers + tile solidity."""
        n = self.width * self.height
        solid = [False] * n
        for layer in self.layers:
            for ty in range(self.height):
                for tx in range(self.width):
                    gid = layer.gid_at(tx, ty)
                    if gid == 0:
                        continue
                    idx = ty * self.width + tx
                    if layer.collision or self.catalog.get(gid, TileDef()).solid:
                        solid[idx] = True
        self._solid = solid

    # -- collision -----------------------------------------------------------
    def is_solid_tile(self, tx: int, ty: int) -> bool:
        if not (0 <= tx < self.width and 0 <= ty < self.height):
            return self.edge_solid
        return self._solid[ty * self.width + tx]

    # -- objects -------------------------------------------------------------
    def objects(self, group: Optional[str] = None) -> List[MapObject]:
        if group is not None:
            return self.object_groups.get(group, [])
        result: List[MapObject] = []
        for objs in self.object_groups.values():
            result.extend(objs)
        return result

    def find_objects(self, type_name: str) -> List[MapObject]:
        return [o for o in self.objects() if o.type == type_name]

    def find_object(self, name: str) -> Optional[MapObject]:
        for o in self.objects():
            if o.name == name:
                return o
        return None

    # -- rendering -----------------------------------------------------------
    def _tile_surface(self, gid: int) -> Optional[pygame.Surface]:
        if gid in self._tile_surfaces:
            return self._tile_surfaces[gid]
        tdef = self.catalog.get(gid)
        if tdef is None:
            return None
        if tdef.image is not None:
            surf = tdef.image
        elif tdef.color is not None:
            surf = pygame.Surface((self.tile_size, self.tile_size))
            surf.fill(tdef.color)
        else:
            return None
        self._tile_surfaces[gid] = surf
        return surf

    def draw(self, renderer, camera) -> None:
        """Enqueue the visible portion of every tile layer (view-culled)."""
        ts = self.tile_size
        ox, oy = camera.offset
        view_w, view_h = renderer.base_size
        start_tx = max(0, int(ox // ts))
        start_ty = max(0, int(oy // ts))
        end_tx = min(self.width, int((ox + view_w) // ts) + 2)
        end_ty = min(self.height, int((oy + view_h) // ts) + 2)

        for layer in self.layers:
            if not layer.visible:
                continue
            for ty in range(start_ty, end_ty):
                row = ty * layer.width
                for tx in range(start_tx, end_tx):
                    gid = layer.data[row + tx]
                    if gid == 0:
                        continue
                    surf = self._tile_surface(gid)
                    if surf is not None:
                        renderer.draw_image(surf, tx * ts, ty * ts,
                                            layer=layer.render_layer, world=True,
                                            sort_y=ty * ts)  # tiles sort by row
