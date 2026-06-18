"""
Modular, swappable combat.

The brief asks combat to be *modular and swappable* -- a simple turn-based
example now, replaceable with real-time later WITHOUT touching the rest of the
engine. The seam is the :class:`CombatSystem` interface plus a name registry:
the battle scene asks ``create_combat(settings, ...)`` for whatever
``combat.system`` names in config. Implement the interface, register it, point
config at it -- done.
"""

from engine.combat.combat_system import (
    Combatant,
    CombatSystem,
    COMBAT_REGISTRY,
    combat_system,
    create_combat,
)
from engine.combat.turn_based import TurnBasedCombat
from engine.combat.action_combat import ActionCombatSystem

__all__ = [
    "Combatant",
    "CombatSystem",
    "COMBAT_REGISTRY",
    "combat_system",
    "create_combat",
    "TurnBasedCombat",
    "ActionCombatSystem",
]
