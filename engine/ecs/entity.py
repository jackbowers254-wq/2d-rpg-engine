"""
engine.ecs.entity
================
An entity is an id + a typed bag of components + a set of tags.

It deliberately contains no game logic -- logic lives in systems. Components are
keyed by their ``type_name`` so lookups are O(1) and data-driven code can ask for
``entity.get("health")`` by string when needed.
"""

from __future__ import annotations

import itertools
from typing import Dict, Iterable, Optional, Set, Type, TypeVar

from engine.ecs.component import Component

C = TypeVar("C", bound=Component)

_id_counter = itertools.count(1)


class Entity:
    __slots__ = ("id", "name", "type", "tags", "components", "alive")

    def __init__(self, name: str = "", type_name: str = "", entity_id: Optional[int] = None):
        self.id: int = entity_id if entity_id is not None else next(_id_counter)
        self.name: str = name
        self.type: str = type_name  # the data archetype this was built from
        self.tags: Set[str] = set()
        self.components: Dict[str, Component] = {}
        self.alive: bool = True

    # -- component access ----------------------------------------------------
    def add(self, comp: Component) -> "Entity":
        self.components[comp.type_name] = comp
        return self  # chainable

    def remove(self, name: str) -> None:
        self.components.pop(name, None)

    def has(self, *names: str) -> bool:
        return all(n in self.components for n in names)

    def get(self, name: str) -> Optional[Component]:
        return self.components.get(name)

    def require(self, name: str) -> Component:
        """Get a component or raise -- use when its absence is a programming error."""
        comp = self.components.get(name)
        if comp is None:
            raise KeyError(f"Entity {self!r} has no '{name}' component")
        return comp

    # Typed convenience: get_as("health", HealthComponent) for editor/type help.
    def get_as(self, name: str, _cls: Type[C]) -> Optional[C]:
        return self.components.get(name)  # type: ignore[return-value]

    # -- tags ----------------------------------------------------------------
    def add_tag(self, tag: str) -> "Entity":
        self.tags.add(tag)
        return self

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def __repr__(self) -> str:
        comps = ",".join(self.components)
        return f"<Entity #{self.id} {self.type or self.name!r} [{comps}]>"
