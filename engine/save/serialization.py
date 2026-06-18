"""
engine.save.serialization
========================
Generic ECS (de)serialization, built on the component name registry.

Because every component registers under a name and implements ``to_data`` /
``from_data``, ANY entity -- built-in or your own -- round-trips to JSON with no
per-type code. This is the mechanism a game uses if it wants a full-world
snapshot. (The demo's GameState keeps a leaner save: rebuild entities from the
map + a "consumed spawns" set + the saved player, which is smaller and avoids
duplicating static map content. Both approaches use these helpers.)
"""

from __future__ import annotations

from typing import Dict, List

from engine.ecs.component import COMPONENT_REGISTRY
from engine.ecs.entity import Entity
from engine.utils.logger import get_logger

log = get_logger("save")


def serialize_entity(entity: Entity) -> dict:
    return {
        "name": entity.name,
        "type": entity.type,
        "tags": sorted(entity.tags),
        "components": {name: comp.to_data() for name, comp in entity.components.items()},
    }


def deserialize_entity(data: dict) -> Entity:
    entity = Entity(name=data.get("name", ""), type_name=data.get("type", ""))
    for tag in data.get("tags", []):
        entity.add_tag(tag)
    for name, comp_data in data.get("components", {}).items():
        cls = COMPONENT_REGISTRY.get(name)
        if cls is None:
            log.warning("Skipping unknown component '%s' during load", name)
            continue
        entity.add(cls.from_data(comp_data))
    return entity


def serialize_entities(world, *, only_tagged: str = "") -> List[dict]:
    """Serialize all (or only tagged) live entities in a world."""
    out: List[dict] = []
    for e in world.entities:
        if not e.alive:
            continue
        if only_tagged and not e.has_tag(only_tagged):
            continue
        out.append(serialize_entity(e))
    return out
