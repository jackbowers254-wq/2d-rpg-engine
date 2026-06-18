"""
engine.ecs.world
===============
The container that ties entities and systems together for one active map/scene.

The World:
- stores entities and lets systems query them by component set,
- runs registered systems each frame in priority order,
- holds references systems commonly need: the active ``tilemap`` (for collision),
  the ``events`` bus and ``settings``. Systems read these off the world instead
  of taking a dozen constructor args.
- defers entity removal until the end of the frame so a system can kill an entity
  mid-iteration without corrupting the loop.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from engine.ecs.entity import Entity
from engine.ecs.system import System


class World:
    def __init__(self, settings=None, events=None) -> None:
        self.settings = settings
        self.events = events
        self._entities: Dict[int, Entity] = {}
        self._systems: List[System] = []
        self._pending_remove: List[int] = []

        # Set by the scene each time a map is loaded; systems use it for collision
        # and tile queries. Kept generic (duck-typed) so any TileMap-like works.
        self.tilemap = None

    # -- entities ------------------------------------------------------------
    def add_entity(self, entity: Entity) -> Entity:
        self._entities[entity.id] = entity
        return entity

    def remove_entity(self, entity_id: int) -> None:
        """Queue an entity for removal at the end of the current frame."""
        self._pending_remove.append(entity_id)

    def get(self, entity_id: int) -> Optional[Entity]:
        return self._entities.get(entity_id)

    @property
    def entities(self) -> Iterable[Entity]:
        return self._entities.values()

    def with_components(self, *names: str) -> List[Entity]:
        """Return all live entities that have every named component."""
        if not names:
            return list(self._entities.values())
        return [e for e in self._entities.values() if e.alive and e.has(*names)]

    def with_tag(self, tag: str) -> List[Entity]:
        return [e for e in self._entities.values() if e.alive and e.has_tag(tag)]

    def find_first(self, *names: str) -> Optional[Entity]:
        for e in self._entities.values():
            if e.alive and e.has(*names):
                return e
        return None

    @property
    def player(self) -> Optional[Entity]:
        """The (first) entity tagged 'player' -- a common lookup."""
        return next((e for e in self._entities.values() if e.has_tag("player")), None)

    def clear_entities(self) -> None:
        self._entities.clear()
        self._pending_remove.clear()

    # -- systems -------------------------------------------------------------
    def add_system(self, system: System) -> System:
        self._systems.append(system)
        self._systems.sort(key=lambda s: s.priority)
        return system

    def get_system(self, cls) -> Optional[System]:
        return next((s for s in self._systems if isinstance(s, cls)), None)

    # -- frame ---------------------------------------------------------------
    def update(self, dt: float) -> None:
        for system in self._systems:
            system.update(self, dt)
        self._flush_removals()

    def _flush_removals(self) -> None:
        for eid in self._pending_remove:
            self._entities.pop(eid, None)
        self._pending_remove.clear()
