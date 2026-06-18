"""
game.state
=========
The demo's shared, persistent game state -- the single source of truth that
survives across scenes and is what the save system snapshots.

It deliberately stores a LEAN save: the player's vitals, the inventory, story
flags, the current map, and the set of "consumed" spawns (enemies defeated, items
taken) so they don't reappear. Static map content is NOT duplicated into the save
-- maps are reloaded from data and entities re-spawned, minus consumed ones, with
the saved player dropped in. (For a full-world snapshot instead, use
``engine.save.serialization`` -- see its module docstring.)

``player`` mirrors the live player entity's health/stats so HP/XP persist between
overworld and battle; the overworld syncs it on save and on battle transitions.
"""

from __future__ import annotations

from typing import Optional, Set, Tuple

from engine.inventory.inventory import Inventory
from engine.inventory.item import ItemDatabase


class GameState:
    def __init__(self, settings, item_db: ItemDatabase) -> None:
        self.settings = settings
        self.item_db = item_db
        self.inventory = Inventory(item_db, settings.get("inventory.max_slots", 20))
        self.flags: dict = {}
        self.consumed: Set[str] = set()
        self.current_map: str = settings.get("world.default_map", "overworld")

        # Persistent player vitals (mirrors the live player entity).
        self.player = {
            "hp": settings.get("combat.player_hp", 24),
            "max_hp": settings.get("combat.player_hp", 24),
            "attack": settings.get("combat.player_attack", 6),
            "defense": settings.get("combat.player_defense", 2),
            "level": 1,
            "xp": 0,
        }
        # Where to drop the player on the next map load: (x, y, facing) in pixels,
        # or None to use the map's player_start object.
        self.spawn_position: Optional[Tuple[float, float, str]] = None

    # -- new game ------------------------------------------------------------
    def new_game(self) -> None:
        for entry in self.settings.get("inventory.starting_items", []):
            self.inventory.add(entry.get("id"), entry.get("qty", 1))

    # -- consumed spawns -----------------------------------------------------
    @staticmethod
    def spawn_id(map_name: str, obj_name: str) -> str:
        return f"{map_name}/{obj_name}"

    def consume(self, map_name: str, obj_name: str) -> None:
        self.consumed.add(self.spawn_id(map_name, obj_name))

    def is_consumed(self, map_name: str, obj_name: str) -> bool:
        return self.spawn_id(map_name, obj_name) in self.consumed

    # -- xp / leveling -------------------------------------------------------
    def grant_xp(self, amount: int) -> bool:
        """Add XP; return True if a level-up happened."""
        self.player["xp"] += amount
        leveled = False
        per = self.settings.get("combat.xp_per_level", 20)
        while self.player["xp"] >= per * self.player["level"]:
            self.player["xp"] -= per * self.player["level"]
            self.player["level"] += 1
            self.player["max_hp"] += 4
            self.player["hp"] = self.player["max_hp"]
            self.player["attack"] += 1
            self.player["defense"] += 1
            leveled = True
        return leveled

    # -- serialization -------------------------------------------------------
    def to_data(self) -> dict:
        return {
            "current_map": self.current_map,
            "player": dict(self.player),
            "spawn_position": self.spawn_position,
            "inventory": self.inventory.to_data(),
            "flags": dict(self.flags),
            "consumed": sorted(self.consumed),
        }

    def from_data(self, data: dict) -> None:
        self.current_map = data.get("current_map", self.current_map)
        self.player.update(data.get("player", {}))
        sp = data.get("spawn_position")
        self.spawn_position = tuple(sp) if sp else None
        self.inventory.from_data(data.get("inventory", {}))
        self.flags = dict(data.get("flags", {}))
        self.consumed = set(data.get("consumed", []))

    def save_meta(self) -> dict:
        return {
            "location": self.current_map,
            "level": self.player["level"],
            "hp": self.player["hp"],
            "max_hp": self.player["max_hp"],
        }
