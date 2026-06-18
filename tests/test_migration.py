"""
Backward-compatibility test: a Gen 1 (v1) save must still load after Gen 2.

Writes a hand-crafted v1 payload (no currency/quests fields), loads it through
the migrating SaveManager, and asserts every old field survives while the new
fields are defaulted.
"""

import json
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.core.game import Game  # noqa: E402
import main as demo  # noqa: E402
from game.state import GameState  # noqa: E402

GEN1_SAVE = {
    "version": 1, "saved_at": time.time(), "meta": {"location": "overworld"},
    "data": {
        "current_map": "cave",
        "player": {"hp": 18, "max_hp": 24, "attack": 6, "defense": 2, "level": 2, "xp": 5},
        "spawn_position": [128, 144, "down"],
        "inventory": {"slots": [["potion", 2], ["wood_sword", 1]], "equipped": {"weapon": "wood_sword"}},
        "flags": {"knows_cave": True, "visited_cave": True},
        "consumed": ["overworld/slime"],
    },
}


def test_gen1_save_migrates():
    game = Game("config/config.json")
    demo.build_services(game)

    slot = game.saves.slots  # use the last slot to avoid clobbering a real save
    with open(game.saves.path(slot), "w", encoding="utf-8") as fh:
        json.dump(GEN1_SAVE, fh)
    try:
        data = game.saves.load(slot)
        st = GameState(game.settings, game.item_db)
        st.from_data(data)

        # Preserved Gen 1 fields.
        assert st.current_map == "cave"
        assert st.player["level"] == 2
        assert st.inventory.count("potion") == 2
        assert st.inventory.equipped.get("weapon") == "wood_sword"
        assert st.flags.get("visited_cave") is True
        assert "overworld/slime" in st.consumed
        # New Gen 2 fields defaulted by the migration.
        assert st.currency == 0
        assert st.quests == {}
    finally:
        if game.saves.exists(slot):
            os.remove(game.saves.path(slot))
        game.shutdown()


if __name__ == "__main__":
    test_gen1_save_migrates()
    print("gen1 save migration: OK")
