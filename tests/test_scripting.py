"""
Tests the data-driven event/trigger/scripting system via the demo intro cutscene:
an 'enter' trigger starts a script that locks the player, moves an NPC, shows
dialogue, gifts an item and sets a flag, then unlocks.
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.core.game import Game  # noqa: E402
import main as demo  # noqa: E402
from game.state import GameState  # noqa: E402


def test_intro_cutscene():
    game = Game("config/config.json")
    demo.build_services(game)
    demo.register_scenes(game)
    game.state = GameState(game.settings, game.item_db)
    game.state.new_game()
    game.scenes.switch_to("overworld", load_existing=False)
    ow = game.scenes.current

    def tick(dt=0.05, press=None):
        game.input.begin_frame()
        if press:
            game.input._pressed.add(next(iter(game.input.bindings[press])))
        game.scenes.update(dt)

    potions0 = game.state.inventory.count("potion")
    villager = next(e for e in ow.world.entities if e.type == "npc_villager")
    vy0 = villager.get("transform").y

    # Step into the trigger zone.
    pt = ow.player.get("transform")
    pt.x, pt.y = 11.5 * 16, 12.5 * 16
    tick()
    assert ow.script is not None and ow._player_locked, "cutscene did not start"

    moved = False
    for _ in range(240):
        if game.scenes.current.__class__.__name__ == "DialogueScene":
            tick(press="confirm")
        else:
            tick()
        if abs(villager.get("transform").y - vy0) > 8:
            moved = True
        if ow.script is None and not ow._player_locked and game.state.flags.get("met_villager"):
            break

    assert moved, "NPC was not moved by the script"
    assert game.state.flags.get("met_villager") is True, "flag not set"
    assert game.state.inventory.count("potion") == potions0 + 1, "item not gifted"
    assert ow.script is None and not ow._player_locked, "cutscene did not end / unlock"
    game.shutdown()


if __name__ == "__main__":
    test_intro_cutscene()
    print("scripting/cutscene: OK")
