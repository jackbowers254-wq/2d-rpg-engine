"""
main.py - demo game entry point.
================================
Bootstrapping a game on this engine is small and declarative:

  1. create the Game (loads config + spins up every engine service),
  2. attach the game-specific services (item DB, UI style, entity factory, world
     map registry, save manager) onto the game object,
  3. register the scenes by name,
  4. run.

Run with:   python main.py
Override config:  RPG_CONFIG=path/to/config.json python main.py

Everything tunable lives in config/config.json; everything content-y lives in
data/. This file just wires the demo together.
"""

from __future__ import annotations

import os

from engine.core.game import Game
from engine.inventory.item import ItemDatabase
from engine.map.world_map import WorldMap
from engine.save.save_manager import SaveManager
from engine.ui.style import UIStyle
from game.factories.entity_factory import EntityFactory
from game.migrations import register_all
from game.scenes.battle_scene import BattleScene
from game.scenes.dialogue_scene import DialogueScene
from game.scenes.inventory_scene import InventoryScene
from game.scenes.overworld_scene import OverworldScene
from game.scenes.pause_scene import PauseScene
from game.scenes.title_scene import TitleScene


def build_services(game: Game) -> None:
    """Attach demo-specific services onto the engine Game object.

    The engine Game is content-agnostic; a game augments it with whatever shared
    services its scenes need. Scenes read these as ``self.game.<name>``.
    """
    s = game.settings
    data_path = s.get("game.data_path", "data")

    game.item_db = ItemDatabase()
    game.item_db.load_dir(s.get("inventory.items_path", os.path.join(data_path, "items")))

    game.style = UIStyle(s, game.assets)
    game.factory = EntityFactory(game.assets, s, os.path.join(data_path, "entities"))

    game.world_map = WorldMap(s, game.assets)
    game.world_map.discover(s.get("world.maps_path", os.path.join(data_path, "maps")))

    game.saves = SaveManager(s)
    register_all(game.saves)  # save-file migrations (old saves upgrade on load)
    game.world = None  # set by the overworld scene when active


def register_scenes(game: Game) -> None:
    game.scenes.register("title", TitleScene)
    game.scenes.register("overworld", OverworldScene)
    game.scenes.register("dialogue", DialogueScene)
    game.scenes.register("battle", BattleScene)
    game.scenes.register("pause", PauseScene)
    game.scenes.register("inventory", InventoryScene)


def main() -> None:
    config = os.environ.get("RPG_CONFIG", "config/config.json")
    game = Game(config)
    build_services(game)
    register_scenes(game)
    game.run()


if __name__ == "__main__":
    main()
