"""
engine.combat.combat_system
==========================
The combat *contract* every combat implementation honours, plus a registry so
the active system is chosen by config (``combat.system``).

A :class:`Combatant` is a thin, system-agnostic view of a fighter. It may be
backed by an ECS entity (``entity``); :meth:`sync_to_entity` writes its HP back
so damage/deaths taken in battle persist on the overworld entity afterwards.

A :class:`CombatSystem`:
- exposes ``combatants`` / ``enemies`` / ``allies`` for the UI to render,
- advances via ``update(dt)`` (matters for real-time; a no-op for pure turn-based),
- reports ``is_over`` and a ``result`` dict
  ``{outcome, xp, defeated_entity_ids, loot}``.

The concrete command surface (attack/use item/flee, target selection, etc.) is
intentionally left to each implementation, because real-time and turn-based need
very different inputs. The battle SCENE talks to the concrete system it created.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Type

COMBAT_REGISTRY: Dict[str, Type["CombatSystem"]] = {}


def combat_system(name: str) -> Callable[[Type["CombatSystem"]], Type["CombatSystem"]]:
    """Register a combat implementation under a config-selectable name."""
    def _reg(cls: Type["CombatSystem"]) -> Type["CombatSystem"]:
        COMBAT_REGISTRY[name] = cls
        return cls
    return _reg


def create_combat(settings, allies: List["Combatant"], enemies: List["Combatant"],
                  **kwargs) -> "CombatSystem":
    """Factory: build the combat system named by ``combat.system`` config."""
    name = settings.get("combat.system", "turn_based")
    cls = COMBAT_REGISTRY.get(name)
    if cls is None:
        raise KeyError(f"Unknown combat system '{name}'. Registered: {sorted(COMBAT_REGISTRY)}")
    return cls(settings, allies, enemies, **kwargs)


@dataclass
class Combatant:
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    is_player: bool = False
    entity_id: Optional[int] = None
    xp_reward: int = 0
    color: List[int] = field(default_factory=lambda: [220, 220, 220])
    entity: object = None  # optional backing ECS entity

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def fraction(self) -> float:
        return 0.0 if self.max_hp <= 0 else max(0.0, self.hp / self.max_hp)

    def sync_to_entity(self) -> None:
        """Write HP back to the backing entity's HealthComponent, if any."""
        if self.entity is not None and self.entity.has("health"):
            self.entity.get("health").hp = max(0, self.hp)

    @classmethod
    def from_entity(cls, entity, inventory=None) -> "Combatant":
        """Build a combatant from an entity's health/stats components."""
        health = entity.get("health")
        stats = entity.get("stats")
        sprite = entity.get("sprite")
        atk = (stats.attack if stats else 3)
        df = (stats.defense if stats else 0)
        if inventory is not None:
            atk += inventory.stat_bonus("attack")
            df += inventory.stat_bonus("defense")
        return cls(
            name=entity.name or entity.type or "Foe",
            hp=health.hp if health else 1,
            max_hp=health.max_hp if health else 1,
            attack=atk, defense=df,
            is_player=entity.has_tag("player"),
            entity_id=entity.id,
            xp_reward=(stats.xp_reward if stats else 0),
            color=(sprite.color if sprite and sprite.color else [220, 220, 220]),
            entity=entity,
        )


class CombatSystem(ABC):
    def __init__(self, settings, allies: List[Combatant], enemies: List[Combatant]) -> None:
        self.settings = settings
        self.allies = allies
        self.enemies = enemies

    @property
    def combatants(self) -> List[Combatant]:
        return self.allies + self.enemies

    def update(self, dt: float) -> None:
        """Advance time-based combat. No-op for pure turn-based systems."""

    @property
    @abstractmethod
    def is_over(self) -> bool: ...

    @property
    @abstractmethod
    def result(self) -> Dict: ...
