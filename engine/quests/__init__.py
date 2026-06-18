"""
engine.quests
===========
A data-driven quest / objective system layered on the event bus.

Quests live in ``data/quests/*.json``. Objectives auto-advance from world events
(an enemy dies, a flag is set, an item is held), so designers wire quests to the
world without code. The :class:`QuestManager` tracks state inside ``GameState.quests``
(so it is saved/loaded for free) and grants rewards + fires ``quest_started`` /
``quest_completed`` events on completion -- which the scripting system, UI toasts
and the quest-log scene react to.
"""

from engine.quests.quest import Objective, QuestDatabase, QuestDef
from engine.quests.manager import QuestManager

__all__ = ["Objective", "QuestDef", "QuestDatabase", "QuestManager"]
