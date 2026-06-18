"""Hit points. Combat and overworld hazards read/write this; UI draws it."""

from __future__ import annotations

from dataclasses import dataclass

from engine.ecs.component import Component, component


@component("health")
@dataclass
class HealthComponent(Component):
    hp: int = 10
    max_hp: int = 10

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def fraction(self) -> float:
        return 0.0 if self.max_hp <= 0 else max(0.0, self.hp / self.max_hp)

    def damage(self, amount: int) -> int:
        amount = max(0, amount)
        self.hp = max(0, self.hp - amount)
        return amount

    def heal(self, amount: int) -> int:
        before = self.hp
        self.hp = min(self.max_hp, self.hp + max(0, amount))
        return self.hp - before
