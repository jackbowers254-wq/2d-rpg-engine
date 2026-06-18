"""
engine.quests.manager
===================
Runtime quest tracking. State lives in ``GameState.quests`` so it saves/loads with
everything else:

    quests[quest_id] = {"state": "active"|"done",
                        "objectives": {objective_id: progress_int}}

Objectives advance two ways:
- **event-driven**: ``defeat`` objectives subscribe to ``entity_died``.
- **polled** in :meth:`update`: ``flag`` and ``collect`` objectives read the
  flags dict / inventory each frame (cheap; few quests).

When all objectives of an active quest are met it auto-completes, granting
rewards (xp / currency / items) and firing ``quest_completed`` -- which scripts,
toasts and the quest log react to.
"""

from __future__ import annotations

from typing import List, Tuple

from engine.utils.logger import get_logger

log = get_logger("quests")


class QuestManager:
    def __init__(self, game, database) -> None:
        self.game = game
        self.db = database
        game.events.subscribe("entity_died", self._on_entity_died)

    @property
    def quests(self) -> dict:
        return self.game.state.quests  # persisted in GameState

    # -- control -------------------------------------------------------------
    def start(self, quest_id: str) -> None:
        qdef = self.db.get(quest_id)
        if qdef is None:
            log.warning("start: unknown quest '%s'", quest_id)
            return
        if quest_id in self.quests:
            return  # already started
        self.quests[quest_id] = {"state": "active",
                                 "objectives": {o.id: 0 for o in qdef.objectives}}
        log.info("Quest started: %s", quest_id)
        self.game.events.publish("quest_started", quest=quest_id)
        self._check_complete(quest_id)  # in case it's already satisfied

    def advance(self, quest_id: str, objective_id=None, amount: int = 1) -> None:
        q = self.quests.get(quest_id)
        qdef = self.db.get(quest_id)
        if not q or qdef is None or q["state"] != "active":
            return
        for o in qdef.objectives:
            if objective_id in (None, o.id):
                q["objectives"][o.id] = min(o.count, q["objectives"].get(o.id, 0) + amount)
        self._check_complete(quest_id)

    def complete(self, quest_id: str) -> None:
        q = self.quests.get(quest_id)
        if not q or q["state"] == "done":
            return
        q["state"] = "done"
        qdef = self.db.get(quest_id)
        rewards = qdef.rewards if qdef else {}
        if rewards.get("xp"):
            self.game.state.grant_xp(rewards["xp"])
        if rewards.get("currency"):
            self.game.state.currency += rewards["currency"]
        for item in rewards.get("items", []):
            self.game.state.inventory.add(item.get("id"), item.get("qty", 1))
        log.info("Quest completed: %s", quest_id)
        self.game.events.publish("quest_completed", quest=quest_id)

    # -- queries -------------------------------------------------------------
    def is_active(self, quest_id: str) -> bool:
        return self.quests.get(quest_id, {}).get("state") == "active"

    def is_done(self, quest_id: str) -> bool:
        return self.quests.get(quest_id, {}).get("state") == "done"

    def objective_lines(self, quest_id: str) -> List[Tuple[str, bool]]:
        """Return [(text, complete?)] for a quest's objectives (for the log UI)."""
        qdef = self.db.get(quest_id)
        q = self.quests.get(quest_id, {})
        out = []
        for o in (qdef.objectives if qdef else []):
            prog = q.get("objectives", {}).get(o.id, 0)
            label = o.description or o.id
            if o.count > 1:
                label = f"{label} ({min(prog, o.count)}/{o.count})"
            out.append((label, prog >= o.count))
        return out

    # -- progression ---------------------------------------------------------
    def update(self, dt: float) -> None:
        for quest_id, q in list(self.quests.items()):
            if q["state"] != "active":
                continue
            qdef = self.db.get(quest_id)
            if qdef is None:
                continue
            for o in qdef.objectives:
                if o.type == "flag":
                    q["objectives"][o.id] = o.count if self.game.state.flags.get(o.flag) else 0
                elif o.type == "collect":
                    q["objectives"][o.id] = min(o.count, self.game.state.inventory.count(o.item))
            self._check_complete(quest_id)

    def _on_entity_died(self, entity=None, **_kw) -> None:
        if entity is None:
            return
        for quest_id, q in list(self.quests.items()):
            if q["state"] != "active":
                continue
            qdef = self.db.get(quest_id)
            if qdef is None:
                continue
            for o in qdef.objectives:
                if o.type == "defeat" and (entity.type == o.target or entity.has_tag(o.target)):
                    q["objectives"][o.id] = min(o.count, q["objectives"].get(o.id, 0) + 1)
            self._check_complete(quest_id)

    def _check_complete(self, quest_id: str) -> None:
        q = self.quests.get(quest_id)
        qdef = self.db.get(quest_id)
        if not q or qdef is None or q["state"] != "active":
            return
        if all(q["objectives"].get(o.id, 0) >= o.count for o in qdef.objectives):
            self.complete(quest_id)
