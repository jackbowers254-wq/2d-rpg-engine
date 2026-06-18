"""
engine.scripting.actions
=======================
Built-in script actions. Each handler takes ``(ctx, params)`` and returns either
None (instant) or a :class:`~engine.scripting.script.Task` (the runner waits on it).

Instant : set_flag, set_var, give_item, take_item, add_currency, face, teleport,
          spawn, remove_entity, play_music, play_sound, emit, lock_player,
          unlock_player, start_quest, advance_quest, complete_quest.
Blocking : wait, move_entity, dialogue, start_battle.

Add your own with ``@script_action("name")`` -- it's immediately usable from data.
Tile coordinates in params are converted to pixels using ``world.tile_size``.
"""

from __future__ import annotations

import math

from engine.scripting.script import Task, script_action
from engine.utils.geometry import Direction
from engine.utils.logger import get_logger

log = get_logger("script")


def _ts(ctx) -> int:
    return ctx.game.settings.get("world.tile_size", 16)


def _facing_from(name: str) -> Direction:
    return {"down": Direction.DOWN, "up": Direction.UP,
            "left": Direction.LEFT, "right": Direction.RIGHT}.get(name, Direction.DOWN)


# ----------------------------- instant actions -----------------------------
@script_action("set_flag")
def _set_flag(ctx, p):
    ctx.flags[p["flag"]] = p.get("value", True)


@script_action("set_var")
def _set_var(ctx, p):
    ctx.vars[p["var"]] = p.get("value")


@script_action("give_item")
def _give_item(ctx, p):
    ctx.game.state.inventory.add(p["item"], p.get("qty", 1))


@script_action("take_item")
def _take_item(ctx, p):
    ctx.game.state.inventory.remove(p["item"], p.get("qty", 1))


@script_action("add_currency")
def _add_currency(ctx, p):
    ctx.game.state.currency = max(0, ctx.game.state.currency + int(p.get("amount", 0)))


@script_action("face")
def _face(ctx, p):
    e = ctx.resolve(p.get("target", "player"))
    if e is None or not e.has("transform"):
        return
    if "toward" in p:
        other = ctx.resolve(p["toward"])
        if other is not None and other.has("transform"):
            et, ot = e.get("transform"), other.get("transform")
            e.get("transform").face(Direction.from_vector(
                ot.x - et.x, ot.y - et.y, et.direction))
    elif "dir" in p:
        e.get("transform").face(_facing_from(p["dir"]))


@script_action("teleport")
def _teleport(ctx, p):
    e = ctx.resolve(p.get("target", "player"))
    if e is None:
        return
    ts = _ts(ctx)
    tx, ty = p.get("to", [0, 0])
    if p.get("map") and e is ctx.world.player and hasattr(ctx.scene, "warp_player"):
        ctx.scene.warp_player(p["map"], tx, ty, p.get("facing", "down"))
        return
    t = e.get("transform")
    if t is not None:
        t.x, t.y = tx * ts, ty * ts
        if "facing" in p:
            t.facing = p["facing"]


@script_action("spawn")
def _spawn(ctx, p):
    ts = _ts(ctx)
    tx, ty = p.get("at", [0, 0])
    ent = ctx.game.factory.create(p["entity"], x=tx * ts, y=ty * ts)
    if p.get("name"):
        ent.name = p["name"]
    ctx.world.add_entity(ent)


@script_action("remove_entity")
def _remove_entity(ctx, p):
    e = ctx.resolve(p.get("target", ""))
    if e is not None:
        ctx.world.remove_entity(e.id)


@script_action("play_music")
def _play_music(ctx, p):
    music = getattr(ctx.game, "audio", None)
    if music is not None:
        music.play_music(p["track"], loop=p.get("loop", True))
    else:
        ctx.game.assets.play_music(p["track"], loop=p.get("loop", True))


@script_action("play_sound")
def _play_sound(ctx, p):
    music = getattr(ctx.game, "audio", None)
    if music is not None:
        music.play_sound(p["sound"])
    else:
        ctx.game.assets.play_sound(p["sound"])


@script_action("emit")
def _emit(ctx, p):
    payload = {k: v for k, v in p.items() if k not in ("action", "event")}
    ctx.game.events.publish(p["event"], **payload)


@script_action("lock_player")
def _lock_player(ctx, p):
    if hasattr(ctx.scene, "set_player_locked"):
        ctx.scene.set_player_locked(True)


@script_action("unlock_player")
def _unlock_player(ctx, p):
    if hasattr(ctx.scene, "set_player_locked"):
        ctx.scene.set_player_locked(False)


# -- quest actions (no-op unless a QuestManager is present at game.quests) ---
@script_action("start_quest")
def _start_quest(ctx, p):
    q = getattr(ctx.game, "quests", None)
    if q:
        q.start(p["quest"])


@script_action("advance_quest")
def _advance_quest(ctx, p):
    q = getattr(ctx.game, "quests", None)
    if q:
        q.advance(p["quest"], p.get("objective"), p.get("amount", 1))


@script_action("complete_quest")
def _complete_quest(ctx, p):
    q = getattr(ctx.game, "quests", None)
    if q:
        q.complete(p["quest"])


# ----------------------------- blocking tasks ------------------------------
class WaitTask(Task):
    def __init__(self, seconds: float) -> None:
        self.t = seconds

    def update(self, dt: float) -> bool:
        self.t -= dt
        return self.t <= 0


@script_action("wait")
def _wait(ctx, p):
    return WaitTask(p.get("seconds", 0.5))


class MoveTask(Task):
    """Move an entity to a target tile. Uses movement intent (collision-aware) if
    the entity has a Movement component, else direct interpolation. Has a timeout
    so a blocked path can never hang a cutscene."""

    def __init__(self, entity, tx, ty, speed, timeout) -> None:
        self.e = entity
        self.tx, self.ty = tx, ty
        self.speed = speed
        self.timeout = timeout

    def update(self, dt: float) -> bool:
        self.timeout -= dt
        t = self.e.get("transform")
        if t is None:
            return True
        dx, dy = self.tx - t.x, self.ty - t.y
        dist = math.hypot(dx, dy)
        m = self.e.get("movement")
        if dist < 1.5 or self.timeout <= 0:
            t.x, t.y = self.tx, self.ty
            if m is not None:
                m.vx = m.vy = 0.0
                m.moving = False
            return True
        if m is not None:
            m.vx, m.vy = dx / dist, dy / dist
            if self.speed:
                m.speed = self.speed
        else:
            step = (self.speed or 40) * dt
            t.x += dx / dist * step
            t.y += dy / dist * step
            t.face(Direction.from_vector(dx, dy, t.direction))
        return False


@script_action("move_entity")
def _move_entity(ctx, p):
    e = ctx.resolve(p.get("target", "player"))
    if e is None or not e.has("transform"):
        return None
    ts = _ts(ctx)
    t = e.get("transform")
    if "by" in p:
        tx, ty = t.x + p["by"][0] * ts, t.y + p["by"][1] * ts
    else:
        to = p.get("to", [0, 0])
        tx, ty = to[0] * ts, to[1] * ts
    speed = p.get("speed", 50)
    dist = math.hypot(tx - t.x, ty - t.y)
    timeout = max(1.0, dist / max(1.0, speed) * 3.0)  # generous safety margin
    return MoveTask(e, tx, ty, speed, timeout)


class _EventWaitTask(Task):
    """Push a scene and wait until a named event fires (dialogue/battle close)."""

    def __init__(self, ctx, event_name, scene_name, **push_kwargs) -> None:
        self.finished = False
        self._unsub = ctx.game.events.subscribe(event_name, self._on_event)
        ctx.game.scenes.push(scene_name, **push_kwargs)

    def _on_event(self, **kwargs):
        self.finished = True

    def update(self, dt: float) -> bool:
        if self.finished:
            self._unsub()
            return True
        return False


@script_action("dialogue")
def _dialogue(ctx, p):
    return _EventWaitTask(ctx, "dialogue_finished", "dialogue",
                          dialogue=p.get("id") or p.get("dialogue", ""))


@script_action("start_battle")
def _start_battle(ctx, p):
    enemy_ids = []
    for item in p.get("enemies", []):
        ent = ctx.resolve(item)
        if ent is None:  # treat as an archetype to spawn next to the player
            ent = ctx.game.factory.create(item)
            pl = ctx.world.player
            if pl and pl.has("transform"):
                pt = pl.get("transform")
                ent.get("transform").x, ent.get("transform").y = pt.x + 24, pt.y
            ctx.world.add_entity(ent)
        enemy_ids.append(ent.id)
    if not enemy_ids:
        return None
    return _EventWaitTask(ctx, "battle_finished", "battle", enemy_ids=enemy_ids)
