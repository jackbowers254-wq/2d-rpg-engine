"""
engine.quests.quest
=================
Quest definitions (data) and their database.

A quest file:

    {
      "id": "clear_the_cave",
      "name": "Clear the Cave",
      "description": "The villager asked you to deal with the slimes.",
      "objectives": [
        {"id": "slimes", "type": "defeat", "target": "enemy_slime", "count": 2,
         "description": "Defeat slimes"},
        {"id": "explore", "type": "flag", "flag": "visited_cave",
         "description": "Explore the cave"}
      ],
      "rewards": {"xp": 15, "currency": 25, "items": [{"id": "ether", "qty": 1}]}
    }

Objective ``type``:
- ``defeat`` : ``target`` entity type/tag, ``count`` kills (advanced by entity_died).
- ``collect``: hold ``count`` of ``item`` (polled from inventory).
- ``flag``   : a ``flag`` becomes truthy (polled). Covers talk/reach/etc. via flags.
"""

from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from engine.utils.logger import get_logger

log = get_logger("quests")


@dataclass
class Objective:
    id: str
    type: str = "flag"
    description: str = ""
    target: str = ""      # for 'defeat'
    item: str = ""        # for 'collect'
    flag: str = ""        # for 'flag'
    count: int = 1


@dataclass
class QuestDef:
    id: str
    name: str
    description: str = ""
    objectives: List[Objective] = field(default_factory=list)
    rewards: Dict = field(default_factory=dict)


class QuestDatabase:
    def __init__(self) -> None:
        self._quests: Dict[str, QuestDef] = {}

    def load_dir(self, directory: str) -> None:
        for path in glob.glob(os.path.join(directory, "*.json")):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            data = {k: v for k, v in data.items() if not k.startswith("_")}
            data.setdefault("id", os.path.splitext(os.path.basename(path))[0])
            objectives = [Objective(**o) for o in data.pop("objectives", [])]
            self._quests[data["id"]] = QuestDef(objectives=objectives, **data)
        log.info("Loaded %d quest definitions", len(self._quests))

    def get(self, quest_id: str) -> Optional[QuestDef]:
        return self._quests.get(quest_id)

    @property
    def all(self) -> List[QuestDef]:
        return list(self._quests.values())
