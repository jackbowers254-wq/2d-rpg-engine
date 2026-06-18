"""
engine.abilities.ability
======================
Ability + status definitions and their databases.

AbilityDef:
- ``type``   : "attack" (damage = power + attacker.attack - defender.defense),
               "heal" (restore ``power`` HP), or "buff"/"debuff" (status only).
- ``power``  : magnitude (damage or heal).
- ``cost``   : MP spent.
- ``target`` : "enemy" or "self" (which side the ability acts on).
- ``status`` : optional status id to apply to the target.
- ``sound``  : optional SFX name.

StatusDef:
- ``duration``: rounds it lasts.
- ``dot``     : damage dealt to the bearer each round (poison/burn).
- ``attack`` / ``defense``: stat modifiers while active (buff/debuff).
"""

from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from engine.utils.logger import get_logger

log = get_logger("abilities")


@dataclass
class AbilityDef:
    id: str
    name: str
    description: str = ""
    type: str = "attack"
    power: int = 0
    cost: int = 0
    target: str = "enemy"     # "enemy" | "self"
    status: str = ""           # status id to apply to the target (optional)
    sound: str = ""


@dataclass
class StatusDef:
    id: str
    name: str
    description: str = ""
    duration: int = 3
    dot: int = 0               # damage per round
    attack: int = 0            # stat modifier while active
    defense: int = 0
    icon_color: Optional[List[int]] = None


def _load_dir(directory: str, cls):
    out: Dict[str, object] = {}
    for path in glob.glob(os.path.join(directory, "*.json")):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and "id" in data:
            entries = [data]
        elif isinstance(data, dict):
            entries = [{**v, "id": v.get("id", k)} for k, v in data.items()
                       if not k.startswith("_") and isinstance(v, dict)]
        else:
            entries = data
        for entry in entries:
            obj = cls(**entry)
            out[obj.id] = obj
    return out


class AbilityDatabase:
    def __init__(self) -> None:
        self._abilities: Dict[str, AbilityDef] = {}

    def load_dir(self, directory: str) -> None:
        self._abilities = _load_dir(directory, AbilityDef)  # type: ignore[assignment]
        log.info("Loaded %d abilities", len(self._abilities))

    def get(self, ability_id: str) -> Optional[AbilityDef]:
        return self._abilities.get(ability_id)


class StatusDatabase:
    def __init__(self) -> None:
        self._statuses: Dict[str, StatusDef] = {}

    def load_dir(self, directory: str) -> None:
        self._statuses = _load_dir(directory, StatusDef)  # type: ignore[assignment]
        log.info("Loaded %d status effects", len(self._statuses))

    def get(self, status_id: str) -> Optional[StatusDef]:
        return self._statuses.get(status_id)
