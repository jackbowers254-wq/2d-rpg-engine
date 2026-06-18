"""
engine.save.save_manager
======================
Slot-based save files. The manager is content-agnostic: it persists a ``data``
payload (any JSON-serializable dict, supplied by the game's GameState) wrapped
with a ``version`` and a small ``meta`` block (location, level, timestamp,
playtime) used to populate a load menu without parsing the whole save.

Config (``save.*``): directory, number of slots, current save version. Versioning
gives you a hook to migrate old saves: compare ``payload["version"]`` on load.
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, List, Optional, Tuple

from engine.utils.logger import get_logger

log = get_logger("save")


class SaveManager:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.directory = settings.get("save.directory", "saves")
        self.slots = settings.get("save.slots", 3)
        self.version = settings.get("save.version", 1)
        os.makedirs(self.directory, exist_ok=True)

    def path(self, slot: int) -> str:
        return os.path.join(self.directory, f"slot{slot}.json")

    def exists(self, slot: int) -> bool:
        return os.path.isfile(self.path(slot))

    # -- write/read ----------------------------------------------------------
    def save(self, slot: int, data: dict, meta: Optional[dict] = None) -> None:
        payload = {
            "version": self.version,
            "saved_at": time.time(),
            "meta": meta or {},
            "data": data,
        }
        tmp = self.path(slot) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, self.path(slot))  # atomic: never leave a half-written save
        log.info("Saved to slot %d", slot)

    def load(self, slot: int) -> Optional[dict]:
        if not self.exists(slot):
            return None
        with open(self.path(slot), "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if payload.get("version") != self.version:
            log.warning("Save slot %d version %s != current %s (migrate if needed)",
                        slot, payload.get("version"), self.version)
        return payload.get("data")

    def slot_meta(self, slot: int) -> Optional[dict]:
        """Lightweight metadata for a save-select menu (or None if empty)."""
        if not self.exists(slot):
            return None
        try:
            with open(self.path(slot), "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            meta = dict(payload.get("meta", {}))
            meta["saved_at"] = payload.get("saved_at")
            return meta
        except (OSError, json.JSONDecodeError):
            return None

    def list_slots(self) -> List[Tuple[int, Optional[dict]]]:
        return [(s, self.slot_meta(s)) for s in range(1, self.slots + 1)]

    def delete(self, slot: int) -> None:
        if self.exists(slot):
            os.remove(self.path(slot))
