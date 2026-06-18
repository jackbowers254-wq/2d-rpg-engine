"""
Quest system: start, event/flag-driven objective progress, completion rewards,
and persistence through save/load.
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.core.game import Game  # noqa: E402
import main as demo  # noqa: E402
from game.state import GameState  # noqa: E402


def test_quest_flow():
    game = Game("config/config.json")
    demo.build_services(game)
    demo.register_scenes(game)
    game.state = GameState(game.settings, game.item_db)
    game.state.new_game()
    game.scenes.switch_to("overworld", load_existing=False)

    q = game.quests
    q.start("clear_the_cave")
    assert q.is_active("clear_the_cave")

    ether0 = game.state.inventory.count("ether")
    cur0 = game.state.currency

    slime = game.factory.create("enemy_slime")
    game.events.publish("entity_died", entity=slime)
    game.events.publish("entity_died", entity=slime)
    game.state.flags["visited_cave"] = True
    q.update(0.05)

    assert q.is_done("clear_the_cave"), "quest did not complete"
    assert game.state.inventory.count("ether") == ether0 + 1, "item reward missing"
    assert game.state.currency == cur0 + 25, "currency reward missing"

    # Persistence.
    game.saves.save(game.saves.slots, game.state.to_data(), game.state.save_meta())
    try:
        st2 = GameState(game.settings, game.item_db)
        st2.from_data(game.saves.load(game.saves.slots))
        assert st2.quests["clear_the_cave"]["state"] == "done"
    finally:
        if game.saves.exists(game.saves.slots):
            os.remove(game.saves.path(game.saves.slots))
    game.shutdown()


if __name__ == "__main__":
    test_quest_flow()
    print("quests: OK")
