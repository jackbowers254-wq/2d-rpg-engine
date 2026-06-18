"""
game.factories.entity_factory
============================
Builds entities from DATA. Given an archetype name it loads
``data/entities/<name>.json`` (a list of components), instantiates each component
via the engine's component registry, and returns a ready Entity. This is the
bridge that makes "add a new enemy/NPC/item = add a JSON file" true.

Two extra conveniences:
- ``create(name, x, y, overrides=...)`` deep-merges per-instance overrides onto
  the archetype before building (so one archetype yields many variants).
- ``create_from_spawn(obj, tile_size)`` reads a Tiled spawn object and maps its
  common properties (``entity``, ``facing``, ``item``, ``dialogue``, ``ai``,
  ``name``) onto the right components -- this is how maps place entities.
"""

from __future__ import annotations

import copy
import os
from typing import Dict, Optional

from engine.ecs.component import COMPONENT_REGISTRY
from engine.ecs.entity import Entity
from engine.settings import deep_merge
from engine.utils.logger import get_logger

log = get_logger("factory")

# Maps a flat spawn-object property -> (component, field[, subkey]) it overrides.
# Lets level designers tweak instances in Tiled without knowing component shapes.
_SPAWN_PROP_MAP = {
    "facing": ("transform", "facing"),
    "dialogue": ("interactable", "params", "dialogue"),
    "item": ("pickup", "item_id"),
    "quantity": ("pickup", "quantity"),
    "ai": ("ai", "behavior"),
    "hp": ("health", "hp"),
}


class EntityFactory:
    def __init__(self, assets, settings, entities_dir: str = "data/entities") -> None:
        self.assets = assets
        self.settings = settings
        self.entities_dir = entities_dir
        self._archetypes: Dict[str, dict] = {}

    # -- archetype loading ---------------------------------------------------
    def _archetype(self, name: str) -> dict:
        if name not in self._archetypes:
            path = os.path.join(self.entities_dir, f"{name}.json")
            data = self.assets.load_json(path)
            data = {k: v for k, v in data.items() if not k.startswith("_")}
            self._archetypes[name] = data
        return self._archetypes[name]

    # -- creation ------------------------------------------------------------
    def create(self, name: str, x: Optional[float] = None, y: Optional[float] = None,
               overrides: Optional[dict] = None) -> Entity:
        data = copy.deepcopy(self._archetype(name))
        if overrides:
            data["components"] = deep_merge(data.get("components", {}),
                                            overrides.get("components", overrides))

        entity = Entity(name=data.get("name", name), type_name=data.get("type", name))
        for tag in data.get("tags", []):
            entity.add_tag(tag)

        for comp_name, comp_data in data.get("components", {}).items():
            cls = COMPONENT_REGISTRY.get(comp_name)
            if cls is None:
                log.warning("Archetype '%s' uses unknown component '%s'", name, comp_name)
                continue
            entity.add(cls.from_data(comp_data or {}))

        if x is not None or y is not None:
            t = entity.get("transform")
            if t is not None:
                if x is not None:
                    t.x = x
                if y is not None:
                    t.y = y
        return entity

    def create_from_spawn(self, obj, tile_size: int) -> Optional[Entity]:
        """Instantiate from a Tiled spawn MapObject (type 'spawn')."""
        archetype = obj.properties.get("entity")
        if not archetype:
            log.warning("Spawn '%s' has no 'entity' property", obj.name)
            return None
        # Tiled rectangle x/y is top-left in pixels; place the entity there.
        entity = self.create(archetype, x=obj.x, y=obj.y)
        if obj.name:
            entity.name = obj.name if archetype != "item_pickup" else entity.name

        # Apply known property overrides onto the freshly-built components.
        for prop, value in obj.properties.items():
            mapping = _SPAWN_PROP_MAP.get(prop)
            if not mapping:
                continue
            comp = entity.get(mapping[0])
            if comp is None:
                continue
            if len(mapping) == 2:
                setattr(comp, mapping[1], value)
            else:  # nested dict field, e.g. interactable.params['dialogue']
                getattr(comp, mapping[1])[mapping[2]] = value
        return entity
