"""Position + facing of an entity in world space (logical pixels)."""

from __future__ import annotations

from dataclasses import dataclass

from engine.ecs.component import Component, component
from engine.utils.geometry import Direction


@component("transform")
@dataclass
class TransformComponent(Component):
    x: float = 0.0
    y: float = 0.0
    facing: str = "down"  # "down" | "up" | "left" | "right" (string => serializable)

    @property
    def direction(self) -> Direction:
        return {
            "down": Direction.DOWN,
            "up": Direction.UP,
            "left": Direction.LEFT,
            "right": Direction.RIGHT,
        }.get(self.facing, Direction.DOWN)

    def face(self, direction: Direction) -> None:
        self.facing = direction.name.lower()
