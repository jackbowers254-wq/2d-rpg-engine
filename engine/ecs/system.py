"""
engine.ecs.system
================
Base class for systems. A system is a pure behaviour unit that runs over the
entities matching the components it needs.

Subclasses override :meth:`update`. The :attr:`required` tuple lets the base
class hand you just the relevant entities via :meth:`World.with_components`, so
systems stay focused (a MovementSystem never sees a sign with no Movement).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Tuple

if TYPE_CHECKING:
    from engine.ecs.entity import Entity
    from engine.ecs.world import World


class System:
    #: Component names an entity must have for this system to process it.
    required: Tuple[str, ...] = ()
    #: Lower runs first. Lets you order e.g. AI (10) before Movement (20).
    priority: int = 100

    def entities(self, world: "World") -> Iterable["Entity"]:
        return world.with_components(*self.required)

    def update(self, world: "World", dt: float) -> None:  # pragma: no cover - abstract
        raise NotImplementedError
