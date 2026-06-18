"""Abilities + status effects wired into turn-based combat."""

import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.abilities.ability import AbilityDatabase, StatusDatabase  # noqa: E402
from engine.combat.combat_system import Combatant  # noqa: E402
from engine.combat.turn_based import TurnBasedCombat  # noqa: E402
from engine.settings import Settings  # noqa: E402


def _setup():
    s = Settings.load("config/config.json")
    adb = AbilityDatabase(); adb.load_dir("data/abilities")
    sdb = StatusDatabase(); sdb.load_dir("data/statuses")
    hero = Combatant("Hero", 24, 24, 6, 2, is_player=True, mp=12, max_mp=12,
                     abilities=["power_strike", "heal", "poison_dart", "guard"])
    enemy = Combatant("Slime", 16, 16, 4, 1, xp_reward=8)
    combat = TurnBasedCombat(s, [hero], [enemy], rng=random.Random(1),
                             ability_db=adb, status_db=sdb)
    return hero, enemy, combat


def test_poison_dot():
    hero, enemy, c = _setup()
    c.player_use_ability("poison_dart")
    assert hero.mp == 9
    assert any(st["id"] == "poison" for st in enemy.statuses)
    hp = enemy.hp
    c.player_attack()  # poison ticks again
    assert enemy.hp < hp


def test_guard_buff():
    hero, _enemy, c = _setup()
    c.player_use_ability("guard")
    assert hero.effective_defense == 6  # 2 + 4


def test_heal_and_mp_gate():
    hero, _enemy, c = _setup()
    hero.hp = 8
    c.player_use_ability("heal")
    assert hero.hp > 8 and hero.mp == 8
    hero.mp = 1
    assert "Not enough MP" in c.player_use_ability("heal")[0]


if __name__ == "__main__":
    test_poison_dot()
    test_guard_buff()
    test_heal_and_mp_gate()
    print("abilities + statuses: OK")
