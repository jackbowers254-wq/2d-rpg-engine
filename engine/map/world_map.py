"""
engine.map.world_map
===================
A world is MANY maps connected by portals -- so the playable space can grow
arbitrarily large without any single map being huge.

WorldMap is a thin registry + cache:
- ``discover`` / ``register`` make map files available by name (drop a file in
  ``data/maps`` and it's part of the world -- fully data-driven),
- ``get`` loads + caches a map on demand,
- ``change_to`` sets the active map.

PORTALS connect maps. A portal is just a map object (in Tiled) with
``type = "portal"`` and properties ``target_map``, ``target_x``, ``target_y``
(destination in tiles) and optional ``facing``. The overworld scene watches for
the player overlapping a portal and calls :meth:`change_to`, then drops the
player at the destination. Because portals are data, you wire maps together in
the editor, not in code.

Tile maps are static, so caching them is safe; the per-map *entities* are rebuilt
by the scene each visit (and their saved state restored by the save system).
"""

from __future__ import annotations

import glob
import os
from typing import Dict, List, Optional

from engine.map.tilemap import TileMap
from engine.map.tmx_loader import load_tiled_map
from engine.utils.logger import get_logger

log = get_logger("world")


class WorldMap:
    def __init__(self, settings, assets) -> None:
        self.settings = settings
        self.assets = assets
        self._paths: Dict[str, str] = {}     # name -> file path
        self._cache: Dict[str, TileMap] = {}  # name -> loaded TileMap
        self.current: Optional[TileMap] = None
        self.current_name: str = ""

    # -- registration --------------------------------------------------------
    def register(self, name: str, path: str) -> None:
        self._paths[name] = path

    def discover(self, maps_dir: Optional[str] = None) -> None:
        """Auto-register every JSON/TMJ map in a directory by file stem."""
        maps_dir = maps_dir or self.settings.get("world.maps_path", "data/maps")
        for pattern in ("*.json", "*.tmj"):
            for path in glob.glob(os.path.join(maps_dir, pattern)):
                name = os.path.splitext(os.path.basename(path))[0]
                self._paths[name] = path
        log.info("Discovered maps: %s", sorted(self._paths))

    @property
    def map_names(self) -> List[str]:
        return sorted(self._paths)

    # -- access --------------------------------------------------------------
    def get(self, name: str) -> TileMap:
        if name in self._cache:
            return self._cache[name]
        if name not in self._paths:
            raise KeyError(f"No map named '{name}'. Known: {sorted(self._paths)}")
        tmap = load_tiled_map(self._paths[name], self.settings, self.assets)
        self._cache[name] = tmap
        return tmap

    def change_to(self, name: str) -> TileMap:
        self.current = self.get(name)
        self.current_name = name
        log.info("Active map -> '%s'", name)
        return self.current

    def portals(self, map_name: Optional[str] = None) -> List:
        tmap = self.get(map_name) if map_name else self.current
        if tmap is None:
            return []
        return tmap.find_objects("portal")
