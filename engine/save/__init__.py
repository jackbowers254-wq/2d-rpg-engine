"""Full game-state serialization."""

from engine.save.save_manager import SaveManager
from engine.save.serialization import (
    deserialize_entity,
    serialize_entities,
    serialize_entity,
)

__all__ = ["SaveManager", "serialize_entity", "deserialize_entity", "serialize_entities"]
