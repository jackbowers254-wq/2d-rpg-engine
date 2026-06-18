"""
engine.data.schemas
==================
Schemas for the engine's built-in content types, used by the loaders to validate
data files and report friendly errors. Games can define their own schemas for
custom data and validate with :func:`engine.data.validate_or_raise`.

These are intentionally permissive about VOCABULARY (e.g. item ``type`` is any
string, so custom categories work) but strict about TYPES (the common bug class).
"""

# A colour is a list of 3-4 ints; we only check it's a list of ints here.
_COLOR = {"type": "list", "items": {"type": "int"}}
_INT_MAP = {"type": "dict", "values": {"type": "int"}}

ITEM_SCHEMA = {
    "type": "object",
    "allow_unknown": False,
    "fields": {
        "id": {"type": "str"},
        "name": {"type": "str", "required": True},
        "description": {"type": "str"},
        "type": {"type": "str"},
        "stackable": {"type": "bool"},
        "max_stack": {"type": "int"},
        "value": {"type": "int"},
        "icon_color": _COLOR,
        "icon": {"type": "str", "nullable": True},
        "effects": _INT_MAP,
        "equip_slot": {"type": "str", "nullable": True},
        "stats": _INT_MAP,
        "consumable": {"type": "bool", "nullable": True},
    },
}

_DIALOGUE_CHOICE = {
    "type": "object",
    "allow_unknown": False,
    "fields": {
        "text": {"type": "str", "required": True},
        "next": {"type": "str", "nullable": True},
        "set": {"type": "dict"},
        "requires": {"type": "any"},
        "hide_if": {"type": "str"},
    },
}

_DIALOGUE_NODE = {
    "type": "object",
    "allow_unknown": False,
    "fields": {
        "speaker": {"type": "str"},
        "text": {"type": "str", "required": True},
        "next": {"type": "str", "nullable": True},
        "choices": {"type": "list", "items": _DIALOGUE_CHOICE},
        "set": {"type": "dict"},
        "give": {"type": "any"},
        "event": {"type": "str"},
    },
}

DIALOGUE_SCHEMA = {
    "type": "object",
    "allow_unknown": False,
    "fields": {
        "version": {"type": "int"},
        "start": {"type": "str", "required": True},
        "nodes": {"type": "dict", "required": True, "values": _DIALOGUE_NODE},
    },
}

# Top-level entity archetype shape (component *fields* are validated separately by
# the factory using each component dataclass's real fields).
ENTITY_SCHEMA = {
    "type": "object",
    "allow_unknown": False,
    "fields": {
        "version": {"type": "int"},
        "name": {"type": "str"},
        "type": {"type": "str"},
        "tags": {"type": "list", "items": {"type": "str"}},
        "components": {"type": "dict", "required": True},
    },
}
