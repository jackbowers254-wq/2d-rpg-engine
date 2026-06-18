"""
engine.abilities
==============
Data-defined abilities (skills) and status effects, wired into combat.

- Abilities (``data/abilities/*.json``): an attack/heal/buff a combatant can spend
  MP on, optionally applying a status to the target.
- Statuses (``data/statuses/*.json``): timed effects -- damage-over-time, or
  attack/defense modifiers -- that tick down each combat round.

The combat system reads these through :class:`AbilityDatabase` /
:class:`StatusDatabase`; combatants carry known ability ids + active statuses, so
adding a new skill or ailment is pure data.
"""

from engine.abilities.ability import (
    AbilityDatabase,
    AbilityDef,
    StatusDatabase,
    StatusDef,
)

__all__ = ["AbilityDef", "AbilityDatabase", "StatusDef", "StatusDatabase"]
