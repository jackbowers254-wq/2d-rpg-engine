"""
engine.ecs.systems.ai_system
===========================
Drives entities with an AIComponent by writing *movement intent* (never moving
them directly -- the MovementSystem still does collision). Behaviours are looked
up by name in a registry, so adding a new one is a small, local change and
entities opt in purely through data (``"ai": {"behavior": "chase", ...}``).

Built-in behaviours
-------------------
- ``idle``  : do nothing.
- ``wander``: pick a random cardinal direction every ``interval`` seconds and
  drift; ``params``: interval, chance_to_move.
- ``chase`` : move toward the player when within ``range`` pixels; ``params``:
  range. (Whether contact starts a battle is decided by the scene, not here --
  keeps AI about movement only.)
"""

from __future__ import annotations

import math
import random
from typing import Callable, Dict

from engine.ai.pathfinding import find_path, has_line_of_sight
from engine.ecs.system import System
from engine.utils.geometry import Direction

# behaviour name -> handler(world, entity, ai, dt)
AI_BEHAVIORS: Dict[str, Callable] = {}


def ai_behavior(name: str):
    def _reg(fn):
        AI_BEHAVIORS[name] = fn
        return fn
    return _reg


def _apply_intent(entity, dx: float, dy: float, running: bool = False) -> None:
    """Write movement intent in whichever style the entity uses."""
    m = entity.get("movement")
    if m is None:
        return
    if m.style == "grid":
        m.input_dx = int(round(dx))
        m.input_dy = int(round(dy))
    else:
        m.vx, m.vy = dx, dy
    m.running = running


@ai_behavior("idle")
def _idle(world, entity, ai, dt):
    pass


@ai_behavior("wander")
def _wander(world, entity, ai, dt):
    st = ai.state
    interval = ai.params.get("interval", 1.5)
    st["timer"] = st.get("timer", 0.0) - dt
    if st["timer"] <= 0.0:
        st["timer"] = interval * random.uniform(0.6, 1.4)
        if random.random() < ai.params.get("chance_to_move", 0.7):
            d = random.choice(list(Direction))
            st["dir"] = (d.dx, d.dy)
        else:
            st["dir"] = (0, 0)
    dx, dy = st.get("dir", (0, 0))
    if dx or dy:
        _apply_intent(entity, dx, dy)


@ai_behavior("chase")
def _chase(world, entity, ai, dt):
    player = world.player
    if player is None:
        return
    pt = player.get("transform")
    t = entity.get("transform")
    rng = ai.params.get("range", 80.0)
    dx, dy = pt.x - t.x, pt.y - t.y
    dist = math.hypot(dx, dy)
    if 0 < dist <= rng:
        _apply_intent(entity, dx / dist, dy / dist, running=ai.params.get("run", False))


@ai_behavior("hunter")
def _hunter(world, entity, ai, dt):
    """Detection/aggro + A* pursuit. States: 'idle' (or wander) -> 'chase' (sees
    the player, paths around walls toward them) -> back to 'idle' when it loses
    the player for ``give_up`` seconds or they leave ``aggro_range`` * 1.5.

    params: aggro_range (tiles), give_up (s), repath (s), require_los (bool),
            run (bool), wander_when_idle (bool).
    """
    player = world.player
    tilemap = world.tilemap
    if player is None or tilemap is None:
        return
    st = ai.state
    ts = tilemap.tile_size
    t = entity.get("transform")
    pt = player.get("transform")

    def center_tile(tr):
        return (int((tr.x + 8) // ts), int((tr.y + 8) // ts))

    e_tile, p_tile = center_tile(t), center_tile(pt)
    dist_px = math.hypot(pt.x - t.x, pt.y - t.y)
    aggro_px = ai.params.get("aggro_range", 6) * ts
    require_los = ai.params.get("require_los", True)

    sees = dist_px <= aggro_px and (
        not require_los or has_line_of_sight(tilemap.is_solid_tile, e_tile, p_tile))

    mode = st.get("mode", "idle")
    if sees:
        mode = "chase"
        st["lost"] = 0.0
    elif mode == "chase":
        st["lost"] = st.get("lost", 0.0) + dt
        if dist_px > aggro_px * 1.6 or st["lost"] > ai.params.get("give_up", 2.5):
            mode = "idle"
            st["path"] = None

    if mode == "chase":
        st["repath"] = st.get("repath", 0.0) - dt
        if st["repath"] <= 0 or not st.get("path"):
            st["path"] = find_path(tilemap.is_solid_tile, e_tile, p_tile)
            st["repath"] = ai.params.get("repath", 0.35)
        path = st.get("path") or []
        if path:
            nx, ny = path[0]
            tx, ty = nx * ts + ts / 2, ny * ts + ts / 2
            dx, dy = tx - (t.x + 8), ty - (t.y + 8)
            d = math.hypot(dx, dy)
            if d < 3:
                path.pop(0)
            else:
                _apply_intent(entity, dx / d, dy / d, running=ai.params.get("run", False))
        else:
            # No path (e.g. adjacent): close in directly.
            dx, dy = pt.x - t.x, pt.y - t.y
            d = math.hypot(dx, dy) or 1
            _apply_intent(entity, dx / d, dy / d, running=ai.params.get("run", False))
    elif ai.params.get("wander_when_idle", True):
        _wander(world, entity, ai, dt)

    st["mode"] = mode


class AISystem(System):
    required = ("ai",)
    priority = 10  # before MovementSystem so intent is set this frame

    def update(self, world, dt: float) -> None:
        for e in self.entities(world):
            ai = e.get("ai")
            if not ai.enabled:
                continue
            handler = AI_BEHAVIORS.get(ai.behavior)
            if handler:
                handler(world, e, ai, dt)
