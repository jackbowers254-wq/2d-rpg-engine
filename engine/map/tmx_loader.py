"""
engine.map.tmx_loader
====================
Loads maps in the **Tiled** editor's JSON format (``.tmj`` / ``.json``) into a
:class:`~engine.map.tilemap.TileMap`. Tiled (https://www.mapeditor.org) is a free
visual map editor; designing maps there and exporting JSON means you build worlds
by drawing, not by editing arrays.

What it understands
-------------------
- Orthogonal maps of ANY size; tile size is read from the file.
- Multiple tile layers. A layer is drawn on the engine render layer named by its
  ``render_layer`` custom property, else by its own name if that matches a
  configured render layer, else "ground".
- Collision from either (a) a layer with a ``collision=true`` property (any
  non-empty tile is solid) or (b) per-tile ``solid=true`` properties in the
  tileset.
- Tile appearance from a tileset image atlas (sliced by id) OR -- so the demo
  needs no art -- a per-tile ``color`` property rendering a coloured square.
- Object groups: rectangles/points with arbitrary properties, used for spawns,
  portals, triggers, NPC/item placement, etc. (read by the game scene).
- Embedded tilesets and external JSON tilesets (``source`` -> ``.tsj``/``.json``).

TMX-XML (``.tmx``) is intentionally not parsed here to avoid an XML dependency;
add a sibling loader if you prefer XML -- it returns the same TileMap, so nothing
downstream changes.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Set, Tuple

import pygame

from engine.map.tilemap import MapObject, TileDef, TileLayer, TileMap
from engine.utils.logger import get_logger

log = get_logger("map")

# Tiled stores flip/rotation in the top 3 bits of a global tile id.
_GID_FLAGS = 0xE0000000
_GID_MASK = ~_GID_FLAGS & 0xFFFFFFFF


def _props_to_dict(props) -> Dict:
    """Tiled stores custom properties as a list of {name,type,value}."""
    out: Dict = {}
    for p in props or []:
        out[p["name"]] = p["value"]
    return out


def _parse_color(value: str) -> Optional[Tuple[int, int, int]]:
    """Parse a Tiled colour ('#AARRGGBB' or '#RRGGBB') into (r, g, b)."""
    if not isinstance(value, str):
        return None
    s = value.lstrip("#")
    try:
        if len(s) == 8:   # AARRGGBB
            return (int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16))
        if len(s) == 6:   # RRGGBB
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        return None
    return None


def _load_tileset(ts_entry: dict, base_dir: str) -> dict:
    """Return a fully-resolved tileset dict, loading external sources if needed."""
    if "source" in ts_entry:
        src = os.path.join(base_dir, ts_entry["source"])
        if src.lower().endswith((".json", ".tsj")):
            with open(src, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            data["firstgid"] = ts_entry["firstgid"]
            data["_dir"] = os.path.dirname(src)
            return data
        log.warning("Unsupported external tileset '%s' (use .tsj/.json)", src)
        return {"firstgid": ts_entry["firstgid"], "tiles": []}
    ts_entry = dict(ts_entry)
    ts_entry["_dir"] = base_dir
    return ts_entry


def _build_catalog(tilesets: List[dict], assets) -> Dict[int, TileDef]:
    """Map every global tile id to a TileDef (look + solidity)."""
    catalog: Dict[int, TileDef] = {0: TileDef()}
    for ts in tilesets:
        firstgid = ts.get("firstgid", 1)
        tw = ts.get("tilewidth", 16)
        th = ts.get("tileheight", 16)
        columns = ts.get("columns", 0)
        atlas: Optional[pygame.Surface] = None
        if ts.get("image") and assets is not None:
            img_path = os.path.join(ts.get("_dir", ""), ts["image"])
            atlas = assets.get_image(img_path)

        # Per-tile overrides (properties, individual images).
        per_tile: Dict[int, dict] = {t["id"]: t for t in ts.get("tiles", [])}

        count = ts.get("tilecount", len(per_tile))
        for local_id in range(count):
            gid = firstgid + local_id
            tdef = TileDef()
            tile_entry = per_tile.get(local_id, {})
            props = _props_to_dict(tile_entry.get("properties"))
            tdef.solid = bool(props.get("solid", False))
            color = _parse_color(props.get("color")) if "color" in props else None
            if color:
                tdef.color = color
            # Image: per-tile image, else a slice of the atlas.
            if tile_entry.get("image") and assets is not None:
                tdef.image = assets.get_image(
                    os.path.join(ts.get("_dir", ""), tile_entry["image"]))
            elif atlas is not None and columns:
                col = local_id % columns
                row = local_id // columns
                tdef.image = atlas.subsurface(pygame.Rect(col * tw, row * th, tw, th))
            catalog[gid] = tdef
    return catalog


def load_tiled_map(path: str, settings, assets=None) -> TileMap:
    """Load a Tiled JSON map file into a TileMap and finalize collision."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    base_dir = os.path.dirname(path)
    name = os.path.splitext(os.path.basename(path))[0]

    tile_size = data.get("tilewidth", settings.get("world.tile_size", 16))
    tmap = TileMap(name, data["width"], data["height"], tile_size)
    tmap.properties = _props_to_dict(data.get("properties"))
    tmap.edge_solid = bool(tmap.properties.get("edge_solid", True))

    # Tilesets -> catalog.
    tilesets = [_load_tileset(ts, base_dir) for ts in data.get("tilesets", [])]
    tmap.catalog = _build_catalog(tilesets, assets)

    known_layers: Set[str] = set(settings.get("render.layers", []))

    for layer in data.get("layers", []):
        ltype = layer.get("type")
        if ltype == "tilelayer":
            props = _props_to_dict(layer.get("properties"))
            # Mask Tiled flip flags out of every gid.
            raw = layer.get("data", [])
            clean = [(g & _GID_MASK) for g in raw]
            lname = layer.get("name", "ground")
            render_layer = props.get("render_layer") or (lname if lname in known_layers else "ground")
            tmap.layers.append(TileLayer(
                name=lname,
                width=layer.get("width", tmap.width),
                height=layer.get("height", tmap.height),
                data=clean,
                render_layer=render_layer,
                visible=layer.get("visible", True),
                collision=bool(props.get("collision", lname == "collision")),
                properties=props,
            ))
        elif ltype == "objectgroup":
            objs: List[MapObject] = []
            for o in layer.get("objects", []):
                objs.append(MapObject(
                    name=o.get("name", ""),
                    # Tiled 1.9 renamed "type" -> "class"; accept both.
                    type=o.get("type", o.get("class", "")),
                    x=o.get("x", 0.0),
                    y=o.get("y", 0.0),
                    width=o.get("width", 0.0),
                    height=o.get("height", 0.0),
                    properties=_props_to_dict(o.get("properties")),
                ))
            tmap.object_groups[layer.get("name", "objects")] = objs

    tmap.finalize()
    log.info("Loaded map '%s' (%dx%d tiles @ %dpx)", name, tmap.width, tmap.height, tile_size)
    return tmap
