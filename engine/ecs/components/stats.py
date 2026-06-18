"""Combat/RPG stats. Kept separate from Health so non-combat entities can have
HP (e.g. a breakable pot) without carrying attack/defense, and vice versa."""

from __future__ import annotations

from dataclasses import dataclass

from engine.ecs.component import Component, component


@component("stats")
@dataclass
class StatsComponent(Component):
    attack: int = 4
    defense: int = 1
    level: int = 1
    xp: int = 0
    xp_reward: int = 5   # xp granted to the victor when this entity is defeated
