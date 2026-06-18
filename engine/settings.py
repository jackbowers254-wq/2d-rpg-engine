"""
engine.settings
===============
Central configuration access for the entire engine.

DESIGN GOAL (from the project brief): *Nothing hardcoded that I might want to
change.* Every tunable value lives in ``config/config.json`` and is read through
this module. Code never hard-codes a resolution, tile size, speed, colour or key
binding -- it asks :class:`Settings` for it.

Usage
-----
    settings = Settings.load("config/config.json")
    tile = settings.get("world.tile_size")              # -> 16
    res  = settings.get("display.base_resolution")      # -> [320, 180]
    spd  = settings.get("player.move_speed", 60)        # default if missing

You may also layer a *user* override file/dict on top of the base config; only
the keys present in the override are replaced (deep merge), so a game can ship a
tiny override file instead of duplicating the whole config.

The class is intentionally tiny and dependency-free so the rest of the engine
can depend on it without pulling in anything else.
"""

from __future__ import annotations

import copy
import json
import os
from typing import Any, Mapping


def deep_merge(base: dict, override: Mapping) -> dict:
    """Recursively merge ``override`` into a copy of ``base`` and return it.

    Dictionaries are merged key-by-key; every other type (including lists) is
    replaced wholesale. This lets a user override config supply only the handful
    of keys it wants to change.
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, Mapping)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class Settings:
    """Read-only-ish view over the merged configuration tree.

    Access values with dotted paths (``"display.base_resolution"``). Missing
    paths return the supplied ``default`` (or ``None``) instead of raising, so a
    sparse config never crashes the engine -- you only override what you need.
    """

    def __init__(self, data: dict | None = None):
        self._data: dict = data or {}

    # -- construction --------------------------------------------------------
    @classmethod
    def load(cls, path: str, overrides: "str | Mapping | None" = None) -> "Settings":
        """Load a JSON config from ``path``.

        ``overrides`` may be a path to another JSON file or a dict; it is deep
        merged on top of the base config. This is the recommended way for an
        individual game to tweak the engine defaults without editing the engine.
        """
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        data = {k: v for k, v in data.items() if not k.startswith("_")}

        if overrides is not None:
            if isinstance(overrides, str):
                with open(overrides, "r", encoding="utf-8") as fh:
                    overrides = json.load(fh)
            data = deep_merge(data, overrides)

        return cls(data)

    # -- access --------------------------------------------------------------
    def get(self, path: str, default: Any = None) -> Any:
        """Return the value at a dotted ``path`` or ``default`` if absent."""
        node: Any = self._data
        for part in path.split("."):
            if isinstance(node, Mapping) and part in node:
                node = node[part]
            else:
                return default
        return node

    def section(self, path: str) -> dict:
        """Return a config sub-tree as a dict (empty dict if missing)."""
        value = self.get(path, {})
        return value if isinstance(value, dict) else {}

    def set(self, path: str, value: Any) -> None:
        """Set a value at runtime (e.g. live-remapping a key or toggling debug).

        This only changes the in-memory config; it is not persisted unless you
        call :meth:`save`.
        """
        node = self._data
        parts = path.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def save(self, path: str) -> None:
        """Persist the current (possibly runtime-modified) config to ``path``."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)

    @property
    def raw(self) -> dict:
        """The underlying merged dict (treat as read-only)."""
        return self._data

    # -- convenience typed getters ------------------------------------------
    # These exist purely for readability at call sites; they are thin wrappers.
    def vec2(self, path: str, default=(0, 0)):
        v = self.get(path, default)
        return (v[0], v[1])

    def color(self, path: str, default=(255, 255, 255)):
        v = self.get(path, default)
        return tuple(v)
