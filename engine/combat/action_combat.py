"""
engine.combat.action_combat
==========================
Real-time, action-style combat (Zelda-like) -- the second combat *style*, proving
the system is pluggable. Unlike the turn-based ``encounter`` style (which pushes a
BattleScene), this runs entirely in the overworld as an ECS system: you press the
attack key to swing a melee hitbox in front of you, and enemies hurt you on
contact. Selected via ``combat.style = "action"``; ``"encounter"`` keeps Gen 1's
turn-based flow. Both read the same Health/Stats components, so entities don't
change.

It stays engine-decoupled by taking callbacks instead of the game object:
``on_enemy_defeated(entity)`` and ``on_player_death()`` are supplied by the scene
(to grant XP / consume spawns / trigger game-over). It publishes ``entity_damaged``
and ``entity_died`` events so polish effects (hit-flash, particles, shake) can react
without this system knowing about them.
"""

from __future__ import annotations

from typing import Callable, Dict

from engine.ecs.system import System
from engine.utils.geometry import aabb_overlap


class ActionCombatSystem(System):
    required = ()  # we query by tag, not a fixed component set
    priority = 55  # after movement (positions current), before render

    def __init__(self, input_manager, events, settings,
                 on_enemy_defeated: Callable, on_player_death: Callable) -> None:
        self.input = input_manager
        self.events = events
        self.on_enemy_defeated = on_enemy_defeated
        self.on_player_death = on_player_death

        self.attack_cooldown = settings.get("combat.attack_cooldown", 0.35)
        self.attack_range = settings.get("combat.attack_range", 14)
        self.enemy_cooldown = settings.get("combat.enemy_attack_cooldown", 1.0)
        self.invuln_time = settings.get("combat.player_invuln", 0.8)

        self._atk_timer = 0.0
        self._invuln = 0.0
        self._enemy_timers: Dict[int, float] = {}

    # -- frame ---------------------------------------------------------------
    def update(self, world, dt: float) -> None:
        self._atk_timer = max(0.0, self._atk_timer - dt)
        self._invuln = max(0.0, self._invuln - dt)
        for k in list(self._enemy_timers):
            self._enemy_timers[k] = max(0.0, self._enemy_timers[k] - dt)

        player = world.player
        if player is None or not player.has("transform"):
            return

        if self.input.just_pressed("attack") and self._atk_timer <= 0:
            self._player_attack(world, player)
            self._atk_timer = self.attack_cooldown

        self._enemy_contact(world, player)

        hp = player.get("health")
        if hp is not None and hp.hp <= 0:
            self.on_player_death()

    # -- player melee --------------------------------------------------------
    def _player_attack(self, world, player) -> None:
        t = player.get("transform")
        d = t.direction
        ts = self.attack_range
        # A hitbox one "reach" in front of the player, centred on its body.
        cx, cy = t.x + 8, t.y + 8
        hx = cx - ts / 2 + d.dx * ts
        hy = cy - ts / 2 + d.dy * ts
        hitbox = (hx, hy, ts, ts)

        anim = player.get("animation")
        if anim is not None:
            anim.play_once(f"attack_{t.facing}")  # falls back if no attack clip

        stats = player.get("stats")
        atk = stats.attack if stats else 4
        for enemy in world.with_tag("enemy"):
            if not enemy.has("transform") or not enemy.has("health"):
                continue
            col = enemy.get("collider")
            et = enemy.get("transform")
            erect = col.rect(et.x, et.y) if col else (et.x, et.y, 16, 16)
            if aabb_overlap(*hitbox, *erect):
                self._damage(enemy, max(1, atk - self._defense(enemy)), source=player)

    # -- enemy melee ---------------------------------------------------------
    def _enemy_contact(self, world, player) -> None:
        if self._invuln > 0:
            return
        pcol = player.get("collider")
        pt = player.get("transform")
        prect = pcol.rect(pt.x, pt.y) if pcol else (pt.x, pt.y, 16, 16)
        for enemy in world.with_tag("enemy"):
            if not enemy.has("transform"):
                continue
            if self._enemy_timers.get(enemy.id, 0.0) > 0:
                continue
            col = enemy.get("collider")
            et = enemy.get("transform")
            erect = col.rect(et.x, et.y) if col else (et.x, et.y, 16, 16)
            if aabb_overlap(*prect, *erect):
                stats = enemy.get("stats")
                dmg = max(1, (stats.attack if stats else 3) - self._defense(player))
                self._damage(player, dmg, source=enemy)
                self._enemy_timers[enemy.id] = self.enemy_cooldown
                self._invuln = self.invuln_time
                return

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _defense(entity) -> int:
        stats = entity.get("stats")
        return stats.defense if stats else 0

    def _damage(self, entity, amount: int, source) -> None:
        hp = entity.get("health")
        dealt = hp.damage(amount)
        self.events.publish("entity_damaged", entity=entity, amount=dealt, source=source)
        anim = entity.get("animation")
        if anim is not None:
            anim.play_once("hit")
        if not hp.alive:
            self.events.publish("entity_died", entity=entity, source=source)
            if entity.has_tag("enemy"):
                self.on_enemy_defeated(entity)
