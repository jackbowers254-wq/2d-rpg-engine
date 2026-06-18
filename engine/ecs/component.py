"""
engine.ecs.component
====================
Base class + name registry for components.

Components are plain *data* (no behaviour) -- mostly dataclasses. Each is
registered under a short string name so:

1. the entity factory can build it from JSON (``"sprite": {...}`` -> SpriteComponent),
2. the save system can serialize/restore it generically.

Register a component with the ``@component("name")`` decorator. Implement
``from_data(cls, data)`` if the JSON shape differs from the constructor, and
``to_data(self)`` if it needs custom serialization (defaults handle dataclasses).
"""

from __future__ import annotations

import dataclasses
from typing import Any, Callable, Dict, Type

COMPONENT_REGISTRY: Dict[str, Type["Component"]] = {}


def component(name: str) -> Callable[[Type["Component"]], Type["Component"]]:
    """Class decorator: register a component under ``name`` for data-driven use."""
    def _register(cls: Type["Component"]) -> Type["Component"]:
        cls.type_name = name
        COMPONENT_REGISTRY[name] = cls
        return cls
    return _register


class Component:
    """Base for all components. ``type_name`` is set by the decorator."""

    type_name: str = "component"

    # -- (de)serialization ---------------------------------------------------
    @classmethod
    def from_data(cls, data: Dict[str, Any]) -> "Component":
        """Build from a JSON-ish dict. Default: pass keys as constructor kwargs.

        Override for components whose stored shape differs from their fields.
        """
        return cls(**data)  # type: ignore[arg-type]

    def to_data(self) -> Dict[str, Any]:
        """Serialize to a JSON-ish dict. Default handles dataclasses."""
        if dataclasses.is_dataclass(self):
            return {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}
        # Fallback: shallow public attributes.
        return {k: v for k, v in vars(self).items() if not k.startswith("_")}
