"""
Headless integration smoke test.

Boots the full game with dummy SDL drivers (no window/audio) and drives it
through every system: world/ECS update, rendering, item pickup, branching
dialogue, turn-based battle, a map transition through a portal, and save/load.

Run directly:   python tests/test_smoke.py
Or with pytest: pytest -q

It deliberately reaches into scene internals (teleporting the player, injecting
input edges) to make the flow deterministic -- this is a test harness, not a
demonstration of the public API.
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Allow running from the tests/ directory or the repo root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame  # noqa: E402

from engine.core.game import Game  # noqa: E402
import main as demo  # noqa: E402
from game.state import GameState  # noqa: E402


def inject(game, action):
    """Simulate a one-frame press of an action by adding a bound key code."""
    codes = game.input.bindings.get(action)
    if codes:
        game.input._pressed.add(next(iter(codes)))


def tick(game, dt=0.1, press=None):
    """Advance one frame the way the real loop does (minus pygame events)."""
    game.input.begin_frame()
    if press:
        inject(game, press)
    game.scenes.update(dt)
    game.renderer.begin_frame()
    game.scenes.draw(game.renderer)
    game.renderer.end_frame()


def new_game(game):
    game.state = GameState(game.settings, game.item_db)
    game.state.new_game()
    game.scenes.switch_to("overworld", load_existing=False)
    return game.scenes.current


def teleport(scene, x, y):
    t = scene.player.get("transform")
    t.x, t.y = x, y


def find(world, type_name):
    return next((e for e in world.entities if e.type == type_name), None)


def main():
    game = Game("config/config.json")
    demo.build_services(game)
    demo.register_scenes(game)

    # --- boot + ambient frames (exercises AI/movement/render across systems) ---
    ow = new_game(game)
    assert game.scenes.current.__class__.__name__ == "OverworldScene"
    for _ in range(30):
        tick(game)
    print("[ok] booted overworld and ran 30 ambient frames")

    # --- item auto-pickup ---
    potion_before = game.state.inventory.count("potion")
    item = find(ow.world, "item_pickup")
    assert item is not None, "no item spawn found"
    it = item.get("transform")
    teleport(ow, it.x, it.y)        # stand on the item
    tick(game)
    assert game.state.inventory.count("potion") == potion_before + 1, "item not picked up"
    print("[ok] walked over item -> picked up potion")

    # --- branching dialogue (interact with the villager) ---
    npc = find(ow.world, "npc_villager")
    nt = npc.get("transform")
    teleport(ow, nt.x, nt.y - 12)   # stand next to the villager
    tick(game, press="interact")    # opens dialogue overlay
    assert game.scenes.current.__class__.__name__ == "DialogueScene", "dialogue did not open"
    potion_pre_gift = game.state.inventory.count("potion")
    for _ in range(40):             # advance/skip until it finishes
        if game.scenes.current.__class__.__name__ != "DialogueScene":
            break
        tick(game, press="confirm")
    assert game.scenes.current is ow, "dialogue did not close"
    assert game.state.inventory.count("potion") >= potion_pre_gift + 1, "dialogue gift not granted"
    assert game.state.flags.get("knows_cave") is True, "dialogue flag not set"
    print("[ok] talked to villager -> branching dialogue ran, flag set, potion gifted")

    # --- turn-based battle (touch the slime) ---
    slime = find(ow.world, "enemy_slime")
    assert slime is not None
    slime_id = slime.id
    st = slime.get("transform")
    xp_before = game.state.player["xp"]
    teleport(ow, st.x, st.y)        # collide with the enemy
    tick(game)                      # enemy_touch -> push battle
    assert game.scenes.current.__class__.__name__ == "BattleScene", "battle did not start"
    for _ in range(80):             # mash confirm: attack / advance messages
        if game.scenes.current.__class__.__name__ != "BattleScene":
            break
        tick(game, press="confirm")
    assert game.scenes.current is ow, "battle did not end"
    tick(game)                      # let the overworld flush the removed enemy
    assert ow.world.get(slime_id) is None, "defeated enemy not removed"
    assert game.state.player["xp"] > xp_before or game.state.player["level"] > 1, "no xp gained"
    print("[ok] battle: attacked slime to victory, enemy removed, xp gained")

    # --- map transition through a portal ---
    # (a short post-battle cooldown suppresses triggers for a few frames)
    portal = ow.world.tilemap.find_objects("portal")[0]
    for _ in range(12):
        teleport(ow, portal.x, portal.y)
        tick(game)
        if game.state.current_map == "cave":
            break
    assert game.state.current_map == "cave", "portal did not change map"
    assert ow.world.tilemap.name == "cave"
    print("[ok] stepped on portal -> transitioned overworld -> cave")

    # --- save / load round-trip ---
    ow._sync_player_to_state()
    game.saves.save(1, game.state.to_data(), game.state.save_meta())
    assert game.saves.exists(1)
    snapshot_map = game.state.current_map
    snapshot_potions = game.state.inventory.count("potion")
    # Corrupt live state, then load and confirm it is restored.
    game.state.current_map = "overworld"
    game.state.inventory.remove("potion", 99)
    data = game.saves.load(1)
    game.state.from_data(data)
    assert game.state.current_map == snapshot_map, "map not restored"
    assert game.state.inventory.count("potion") == snapshot_potions, "inventory not restored"
    print("[ok] save/load round-trip restored map + inventory")

    # --- pause + inventory overlays open/close ---
    game.scenes.switch_to("overworld", load_existing=True)
    ow = game.scenes.current
    tick(game, press="menu")
    assert game.scenes.current.__class__.__name__ == "PauseScene"
    tick(game, press="cancel")
    assert game.scenes.current is ow
    tick(game, press="inventory")
    assert game.scenes.current.__class__.__name__ == "InventoryScene"
    tick(game, press="inventory")
    assert game.scenes.current is ow
    print("[ok] pause and inventory overlays open and close")

    game.shutdown()
    print("\nALL SMOKE TESTS PASSED")


def test_smoke():
    """pytest entry point."""
    main()


if __name__ == "__main__":
    main()
