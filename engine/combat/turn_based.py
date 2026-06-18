"""
engine.combat.turn_based
======================
A compact turn-based battle system -- the swappable *example* implementation.

Flow: the player picks one command (Attack / Item / Flee); it resolves, then
every living enemy takes a turn; control returns to the player. Each command
method returns the ordered list of log messages for that whole round, which the
battle scene displays one at a time -- so the UI never needs to know the rules.

Damage = max(1, attacker.attack - defender.defense) with a little randomness.
HP is written back to the backing entities after every change, so wounds and
deaths persist into the overworld. On the last enemy falling, ``result`` reports
``victory`` with summed XP and the defeated entity ids (the scene removes those
entities and awards XP).

Replace this entire file with a real-time system and register it under a new
``combat.system`` name; nothing else changes.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional

from engine.combat.combat_system import Combatant, CombatSystem, combat_system


@combat_system("turn_based")
class TurnBasedCombat(CombatSystem):
    def __init__(self, settings, allies: List[Combatant], enemies: List[Combatant],
                 *, rng: Optional[random.Random] = None) -> None:
        super().__init__(settings, allies, enemies)
        self.rng = rng or random.Random()
        self.flee_chance = settings.get("combat.flee_chance", 0.5)
        self._outcome: Optional[str] = None  # None | victory | defeat | fled
        self.log: List[str] = ["A wild encounter!"]

    # -- helpers -------------------------------------------------------------
    @property
    def hero(self) -> Combatant:
        return self.allies[0]

    @property
    def living_enemies(self) -> List[Combatant]:
        return [c for c in self.enemies if c.alive]

    def _resolve_attack(self, attacker: Combatant, defender: Combatant) -> str:
        base = attacker.attack - defender.defense
        dmg = max(1, base) + self.rng.randint(0, 1)
        defender.hp = max(0, defender.hp - dmg)
        defender.sync_to_entity()
        msg = f"{attacker.name} hits {defender.name} for {dmg}!"
        if not defender.alive:
            msg += f" {defender.name} is defeated!"
        return msg

    def _enemy_phase(self) -> List[str]:
        out: List[str] = []
        for enemy in self.living_enemies:
            out.append(self._resolve_attack(enemy, self.hero))
            if not self.hero.alive:
                self._outcome = "defeat"
                out.append(f"{self.hero.name} has fallen...")
                break
        self._check_victory()
        return out

    def _check_victory(self) -> None:
        if self._outcome is None and not self.living_enemies:
            self._outcome = "victory"

    # -- player commands (each returns the round's messages) ----------------
    def player_attack(self, target: Optional[Combatant] = None) -> List[str]:
        if self.is_over:
            return []
        target = target or (self.living_enemies[0] if self.living_enemies else None)
        if target is None:
            return []
        out = [self._resolve_attack(self.hero, target)]
        self._check_victory()
        if self._outcome is None:
            out += self._enemy_phase()
        self.log += out
        return out

    def player_use_item(self, item_id: str, inventory) -> List[str]:
        if self.is_over:
            return []
        ok, msg = inventory.use(item_id, self.hero.entity)
        # Re-read HP from the (possibly healed) backing entity.
        if self.hero.entity is not None and self.hero.entity.has("health"):
            self.hero.hp = self.hero.entity.get("health").hp
        out = [msg if ok else "It had no effect."]
        if self._outcome is None:
            out += self._enemy_phase()
        self.log += out
        return out

    def player_flee(self) -> List[str]:
        if self.is_over:
            return []
        if self.rng.random() < self.flee_chance:
            self._outcome = "fled"
            out = ["Got away safely!"]
        else:
            out = ["Couldn't escape!"]
            out += self._enemy_phase()
        self.log += out
        return out

    # -- CombatSystem interface ---------------------------------------------
    @property
    def is_over(self) -> bool:
        return self._outcome is not None

    @property
    def result(self) -> Dict:
        xp = sum(e.xp_reward for e in self.enemies if not e.alive)
        defeated = [e.entity_id for e in self.enemies if not e.alive and e.entity_id is not None]
        return {
            "outcome": self._outcome or "ongoing",
            "xp": xp if self._outcome == "victory" else 0,
            "defeated_entity_ids": defeated if self._outcome == "victory" else [],
            "loot": [],
        }
