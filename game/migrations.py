"""
game.migrations
==============
Demo-specific save migrations. These know the GameState shape and upgrade old
payloads field-by-field. Registered on the SaveManager in ``main.build_services``.

Add a step each time you change the save schema and bump ``save.version`` in
config: implement ``vN -> vN+1`` and old saves will chain through automatically.
"""

from __future__ import annotations


def v1_to_v2(data: dict) -> dict:
    """Gen 1 (v1) -> Gen 2 (v2): introduce currency + quest tracking."""
    data.setdefault("currency", 0)
    data.setdefault("quests", {})
    return data


def register_all(save_manager) -> None:
    save_manager.register_migration(1, v1_to_v2)
