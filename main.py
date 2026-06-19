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

from engine.abilities.ability import AbilityDatabase, StatusDatabase
from engine.core.game import Game
from engine.economy.shop import ShopDatabase
from engine.graphics.daynight import DayNightCycle
from engine.graphics.effects import LightingEffect, ParticleSystem
from engine.graphics.palette import PaletteManager
from engine.graphics.postprocess import PostProcessStack
from engine.inventory.item import ItemDatabase
from engine.map.world_map import WorldMap
from engine.quests.manager import QuestManager
from engine.quests.quest import QuestDatabase
from engine.save.save_manager import SaveManager
from engine.ui.style import UIStyle
from game.factories.entity_factory import EntityFactory
from game.migrations import register_all
from game.scenes.battle_scene import BattleScene
from game.scenes.dialogue_scene import DialogueScene
from game.scenes.inventory_scene import InventoryScene
from game.scenes.options_scene import OptionsScene
from game.scenes.overworld_scene import OverworldScene
from game.scenes.pause_scene import PauseScene
from game.scenes.quest_log_scene import QuestLogScene
from game.scenes.shop_scene import ShopScene
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

    game.ability_db = AbilityDatabase()
    game.ability_db.load_dir(s.get("combat.abilities_path", os.path.join(data_path, "abilities")))
    game.status_db = StatusDatabase()
    game.status_db.load_dir(s.get("combat.statuses_path", os.path.join(data_path, "statuses")))

    game.style = UIStyle(s, game.assets)
    game.factory = EntityFactory(game.assets, s, os.path.join(data_path, "entities"))

    game.world_map = WorldMap(s, game.assets)
    game.world_map.discover(s.get("world.maps_path", os.path.join(data_path, "maps")))

    game.saves = SaveManager(s)
    register_all(game.saves)  # save-file migrations (old saves upgrade on load)

    game.quest_db = QuestDatabase()
    game.quest_db.load_dir(s.get("quests.quests_path", os.path.join(data_path, "quests")))
    game.quests = QuestManager(game, game.quest_db)  # reads/writes GameState.quests

    game.shops = ShopDatabase()
    game.shops.load_dir(s.get("economy.shops_path", os.path.join(data_path, "shops")))

    game.palettes = PaletteManager()
    game.palettes.load_dir(s.get("assets.palettes_path", os.path.join(data_path, "palettes")))

    # Optional render effects (config-gated). Built once and registered on the
    # renderer; scenes drive lights / emit particles through these handles.
    game.lighting = None
    game.particles = None
    game.daynight = DayNightCycle(s)
    if s.get("render.effects_enabled", False):
        names = s.get("render.effects", [])
        if "lighting" in names:
            game.lighting = LightingEffect(
                after_layer_name=s.get("render.lighting_layer", "overhead"),
                bands=s.get("render.light_bands", 0))
            game.renderer.add_effect(game.lighting)
        if "particles" in names:
            game.particles = ParticleSystem(chunky=s.get("render.particle_size", 2))
            game.renderer.add_effect(game.particles)

    # Retro post-processing chain (registered last so it runs after lighting;
    # all effects default OFF -- toggle the CRT preset in-game with F2).
    game.postfx = PostProcessStack(s)
    game.renderer.add_effect(game.postfx)

    game.world = None  # set by the overworld scene when active


def register_scenes(game: Game) -> None:
    game.scenes.register("title", TitleScene)
    game.scenes.register("overworld", OverworldScene)
    game.scenes.register("dialogue", DialogueScene)
    game.scenes.register("battle", BattleScene)
    game.scenes.register("pause", PauseScene)
    game.scenes.register("inventory", InventoryScene)
    game.scenes.register("quest_log", QuestLogScene)
    game.scenes.register("options", OptionsScene)
    game.scenes.register("shop", ShopScene)


def main() -> None:
    config = os.environ.get("RPG_CONFIG", "config/config.json")
    game = Game(config)
    build_services(game)
    register_scenes(game)
    game.run()


if __name__ == "__main__":
    main()
