"""
engine.inventory.item
====================
Items are DATA. An item type is defined once in JSON (``data/items/*.json``) and
referenced everywhere by its id. To add an item you edit data, never code.

ItemDef fields (all optional except id/name):
- ``type``       : "consumable" | "equipment" | "key" | "material" (free-form;
                   only used by your game logic / UI grouping).
- ``stackable``  : whether copies stack into one inventory slot.
- ``max_stack``  : stack cap when stackable.
- ``value``      : shop/sell value.
- ``icon_color`` : placeholder swatch colour (the demo's "icon" art).
- ``icon``       : optional image path (overrides icon_color).
- ``effects``    : dict applied on use, e.g. {"heal": 10}. Extend ``apply_effects``.
- ``equip_slot`` : slot name for equipment ("weapon", "armor", ...).
- ``stats``      : stat modifiers granted while equipped, e.g. {"attack": 3}.
- ``consumable`` : whether 'use' consumes one (defaults True for type consumable).
"""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from engine.utils.logger import get_logger

log = get_logger("items")


@dataclass
class ItemDef:
    id: str
    name: str
    description: str = ""
    type: str = "material"
    stackable: bool = True
    max_stack: int = 99
    value: int = 0
    icon_color: List[int] = field(default_factory=lambda: [200, 200, 200])
    icon: Optional[str] = None
    effects: Dict[str, int] = field(default_factory=dict)
    equip_slot: Optional[str] = None
    stats: Dict[str, int] = field(default_factory=dict)
    consumable: Optional[bool] = None

    @property
    def is_consumable(self) -> bool:
        return self.consumable if self.consumable is not None else (self.type == "consumable")


class ItemDatabase:
    """Loads and indexes every item definition by id."""

    def __init__(self) -> None:
        self._items: Dict[str, ItemDef] = {}

    def load_dir(self, directory: str) -> None:
        """Load every ``*.json`` file of item definitions in a directory.

        Each file may be a single ``{id: {...}}`` mapping or a list of objects
        with an ``id`` field.
        """
        for path in glob.glob(os.path.join(directory, "*.json")):
            import json
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                # {id: {...}} mapping; skip documentation keys like "_comment".
                pairs = [(k, v) for k, v in data.items()
                         if not k.startswith("_") and isinstance(v, dict)]
            else:
                pairs = [(e.get("id"), e) for e in data]
            for key, entry in pairs:
                entry = dict(entry)
                entry.setdefault("id", key)
                self._items[entry["id"]] = ItemDef(**entry)
        log.info("Loaded %d item definitions", len(self._items))

    def get(self, item_id: str) -> Optional[ItemDef]:
        item = self._items.get(item_id)
        if item is None:
            log.warning("Unknown item id '%s'", item_id)
        return item

    def __contains__(self, item_id: str) -> bool:
        return item_id in self._items

    @property
    def all(self) -> List[ItemDef]:
        return list(self._items.values())
