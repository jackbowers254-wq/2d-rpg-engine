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
