"""
engine.ecs.systems.movement_system
==================================
Turns movement *intent* into collision-resolved motion, for BOTH movement styles.

Controllers (player input, AI) never move entities directly; they only set intent
on the MovementComponent:
- smooth: ``vx``/``vy`` as a unit direction; the system scales by ``speed`` (and
  ``run_multiplier`` if ``running``) and resolves collisions per-axis.
- grid: ``input_dx``/``input_dy`` as a step direction; the system tweens one tile
  over ``move_time``, refusing to start a step into a solid tile/entity.

Because intent and resolution are separated, the same system drives the player
and every NPC/enemy, and you switch a whole game between grid and smooth movement
with one config value (``player.movement_style`` for the player; per-entity via
the component's ``style`` for others).
"""

from __future__ import annotations

import math

from engine.ecs.system import System
from engine.ecs.systems.collision import is_blocked
from engine.utils.geometry import Direction, clamp, lerp


class MovementSystem(System):
    required = ("transform", "movement")
    priority = 50  # after AI/input (which set intent), before rendering

    def update(self, world, dt: float) -> None:
        tilemap = world.tilemap
        # Snapshot solid entity colliders once per frame (id, rect).
        solids = []
        for e in world.with_components("transform", "collider"):
            col = e.get("collider")
            if col.solid:
                t = e.get("transform")
                solids.append((e.id, col.rect(t.x, t.y)))

        for e in self.entities(world):
            m = e.get("movement")
            t = e.get("transform")
            col = e.get("collider")
            if m.style == "grid":
                self._update_grid(world, e, t, m, col, tilemap, solids, dt)
            else:
                self._update_smooth(e, t, m, col, tilemap, solids, dt)

    # -- smooth --------------------------------------------------------------
    def _update_smooth(self, e, t, m, col, tilemap, solids, dt) -> None:
        vx, vy = m.vx, m.vy
        mag = math.hypot(vx, vy)
        m.moving = False
        if mag > 0:
            vx, vy = vx / mag, vy / mag  # normalise intent so diagonals aren't faster
            t.face(Direction.from_vector(vx, vy, t.direction))
            speed = m.speed * (m.run_multiplier if m.running else 1.0)
            dx, dy = vx * speed * dt, vy * speed * dt
            before = (t.x, t.y)
            self._move_resolved(e, t, col, dx, dy, tilemap, solids)
            m.moving = (t.x, t.y) != before  # False if fully blocked by a wall
        # Intent is consumed each frame; controllers re-set it next frame.
        m.vx = m.vy = 0.0
        m.running = False

    def _move_resolved(self, e, t, col, dx, dy, tilemap, solids) -> None:
        if col is None:  # no hitbox -> move freely (decorative/ghost entities)
            t.x += dx
            t.y += dy
            return
        # X axis
        t.x += dx
        if is_blocked(col.rect(t.x, t.y), tilemap, solids, e.id):
            t.x -= dx
        # Y axis (independent -> wall sliding)
        t.y += dy
        if is_blocked(col.rect(t.x, t.y), tilemap, solids, e.id):
            t.y -= dy

    # -- grid ----------------------------------------------------------------
    def _update_grid(self, world, e, t, m, col, tilemap, solids, dt) -> None:
        m.moving = m.is_moving
        if m.is_moving:
            move_time = m.move_time / (m.run_multiplier if m.running else 1.0)
            m._t += dt
            frac = clamp(m._t / move_time, 0.0, 1.0)
            t.x = lerp(m._sx, m._tx, frac)
            t.y = lerp(m._sy, m._ty, frac)
            if frac >= 1.0:
                t.x, t.y = m._tx, m._ty
                m.is_moving = False
            return

        dx, dy = m.input_dx, m.input_dy
        if dx == 0 and dy == 0:
            return
        # Step one tile in the dominant axis (no diagonal grid steps).
        if dx != 0 and dy != 0:
            dy = 0
        t.face(Direction.from_vector(dx, dy, t.direction))  # turn even if blocked
        ts = tilemap.tile_size if tilemap else 16
        target_x = t.x + dx * ts
        target_y = t.y + dy * ts
        rect = col.rect(target_x, target_y) if col else (target_x, target_y, ts, ts)
        if not is_blocked(rect, tilemap, solids, e.id):
            m._sx, m._sy = t.x, t.y
            m._tx, m._ty = target_x, target_y
            m._t = 0.0
            m.is_moving = True
        # Intent consumed; controller re-sets next frame.
        m.input_dx = m.input_dy = 0
