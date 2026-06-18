"""
engine.save.migrations
=====================
A tiny, ordered migration framework for save files (and, reused, for data files).

Saves carry a ``version``. When the current version is newer than a file's, the
registered migration steps are applied IN ORDER (v1->v2->v3...) to bring the old
payload up to date. This is how Gen 1 saves keep loading after Gen 2 changes the
GameState shape: each step is a pure ``dict -> dict`` transform that adds/renames
fields with sensible defaults.

The mechanism is generic (engine); the *steps* are game-specific (they know the
GameState shape), so a game registers them on its SaveManager. See
``game/migrations.py`` for the demo's steps.
"""

from __future__ import annotations

from typing import Callable, Dict, Tuple

from engine.utils.logger import get_logger

log = get_logger("save")

MigrationStep = Callable[[dict], dict]


class Migrator:
    def __init__(self) -> None:
        # from_version -> step that upgrades a payload from N to N+1
        self._steps: Dict[int, MigrationStep] = {}

    def register(self, from_version: int) -> Callable[[MigrationStep], MigrationStep]:
        """Decorator: register the step that upgrades ``from_version`` -> +1."""
        def _deco(fn: MigrationStep) -> MigrationStep:
            self._steps[from_version] = fn
            return fn
        return _deco

    def add(self, from_version: int, fn: MigrationStep) -> None:
        self._steps[from_version] = fn

    def migrate(self, data: dict, from_version: int, to_version: int) -> Tuple[dict, int]:
        """Apply steps to raise ``data`` from ``from_version`` to ``to_version``."""
        v = from_version
        while v < to_version:
            step = self._steps.get(v)
            if step is None:
                log.warning("No save migration for v%d -> v%d; loading as-is", v, v + 1)
                break
            data = step(data)
            log.info("Migrated save v%d -> v%d", v, v + 1)
            v += 1
        return data, v
