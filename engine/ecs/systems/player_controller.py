"""
engine.ecs.systems.player_controller
====================================
Translates abstract input actions into movement *intent* for any entity carrying
a PlayerControlledComponent. It runs before the MovementSystem (lower priority),
which then turns intent into collision-resolved motion -- so the player obeys the
exact same physics as NPCs.

It reads ACTIONS ("move_up", "run", ...), never raw keys, so rebinding in config
just works. It honours the entity's movement ``style`` (grid vs smooth), which is
itself set from ``player.movement_style`` config when the player is built.
"""

from __future__ import annotations

from engine.ecs.system import System


class PlayerControllerSystem(System):
    required = ("transform", "movement", "player_controlled")
    priority = 5  # before AI/Movement so the player's intent is set first

    def __init__(self, input_manager) -> None:
        self.input = input_manager

    def update(self, world, dt: float) -> None:
        dx = self.input.axis("move_left", "move_right")
        dy = self.input.axis("move_up", "move_down")
        running = self.input.is_down("run")
        for e in self.entities(world):
            if not e.get("player_controlled").enabled:
                continue
            m = e.get("movement")
            if m.style == "grid":
                m.input_dx, m.input_dy = dx, dy
            else:
                m.vx, m.vy = float(dx), float(dy)
            m.running = running
