"""
engine.inventory.inventory
=========================
A slot-based inventory plus equipment, decoupled from the item *definitions* (it
only stores ids + counts, looking up details in the ItemDatabase on demand).

Capabilities the brief asks for -- pick up / use / equip -- are all here:
- ``add`` / ``remove``           : stacking respected via the item's max_stack.
- ``use(item_id, target)``       : applies the item's ``effects`` (e.g. heal) to
  a target entity and consumes it if appropriate.
- ``equip`` / ``unequip``        : moves an item into/out of an equipment slot;
  ``stat_bonus`` aggregates equipped stat modifiers for the combat system.

It is fully serializable (``to_data`` / ``from_data``) so the save system can
snapshot it. Effects are applied through a small, overridable dispatcher so you
can add new effect kinds ("cure", "buff", "teleport") without touching callers.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from engine.inventory.item import ItemDatabase
from engine.utils.logger import get_logger

log = get_logger("inventory")


class Inventory:
    def __init__(self, database: ItemDatabase, max_slots: int = 20) -> None:
        self.db = database
        self.max_slots = max_slots
        # Each slot is [item_id, quantity]. Stackable items share a slot.
        self.slots: List[List] = []
        # slot_name -> item_id of currently equipped item.
        self.equipped: Dict[str, str] = {}

    # -- queries -------------------------------------------------------------
    def count(self, item_id: str) -> int:
        return sum(q for iid, q in self.slots if iid == item_id)

    def has(self, item_id: str, qty: int = 1) -> bool:
        return self.count(item_id) >= qty

    @property
    def is_full(self) -> bool:
        return len(self.slots) >= self.max_slots

    # -- mutation ------------------------------------------------------------
    def add(self, item_id: str, qty: int = 1) -> int:
        """Add items, honouring stack limits. Returns the amount that fit."""
        item = self.db.get(item_id)
        if item is None:
            return 0
        added = 0
        if item.stackable:
            for slot in self.slots:
                if slot[0] == item_id and slot[1] < item.max_stack:
                    space = item.max_stack - slot[1]
                    take = min(space, qty - added)
                    slot[1] += take
                    added += take
                    if added >= qty:
                        return added
        while added < qty and not self.is_full:
            take = min(item.max_stack if item.stackable else 1, qty - added)
            self.slots.append([item_id, take])
            added += take
        if added < qty:
            log.info("Inventory full: dropped %d x %s", qty - added, item_id)
        return added

    def remove(self, item_id: str, qty: int = 1) -> int:
        """Remove items. Returns amount actually removed."""
        removed = 0
        for slot in list(self.slots):
            if slot[0] != item_id:
                continue
            take = min(slot[1], qty - removed)
            slot[1] -= take
            removed += take
            if slot[1] <= 0:
                self.slots.remove(slot)
            if removed >= qty:
                break
        return removed

    # -- use -----------------------------------------------------------------
    def use(self, item_id: str, target=None) -> Tuple[bool, str]:
        """Use an item on a target entity. Returns (success, message)."""
        item = self.db.get(item_id)
        if item is None or not self.has(item_id):
            return False, "You don't have that."
        msg = self.apply_effects(item, target)
        if item.is_consumable:
            self.remove(item_id, 1)
        return True, msg

    def apply_effects(self, item, target) -> str:
        """Dispatch an item's effects onto a target entity.

        EXTENSION POINT: add new effect keys here (cure, revive, buff, ...).
        """
        messages = []
        for effect, amount in item.effects.items():
            if effect == "heal" and target is not None and target.has("health"):
                healed = target.get("health").heal(amount)
                messages.append(f"Restored {healed} HP")
            elif effect == "damage" and target is not None and target.has("health"):
                dealt = target.get("health").damage(amount)
                messages.append(f"Dealt {dealt} damage")
            else:
                messages.append(f"{effect}+{amount}")
        return f"Used {item.name}. " + (", ".join(messages) if messages else "")

    # -- equipment -----------------------------------------------------------
    def equip(self, item_id: str) -> bool:
        item = self.db.get(item_id)
        if item is None or not item.equip_slot or not self.has(item_id):
            return False
        self.unequip(item.equip_slot)
        self.equipped[item.equip_slot] = item_id
        return True

    def unequip(self, slot: str) -> None:
        self.equipped.pop(slot, None)

    def stat_bonus(self, stat: str) -> int:
        """Sum a stat across all equipped items (for the combat system)."""
        total = 0
        for item_id in self.equipped.values():
            item = self.db.get(item_id)
            if item:
                total += item.stats.get(stat, 0)
        return total

    # -- serialization -------------------------------------------------------
    def to_data(self) -> dict:
        return {"slots": [list(s) for s in self.slots], "equipped": dict(self.equipped)}

    def from_data(self, data: dict) -> None:
        self.slots = [list(s) for s in data.get("slots", [])]
        self.equipped = dict(data.get("equipped", {}))
