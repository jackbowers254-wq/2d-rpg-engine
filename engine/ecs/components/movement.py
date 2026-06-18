"""
Movement state for an entity.

Supports both movement styles the brief asks to be configurable:
- ``"smooth"``: velocity-based, free movement with wall sliding.
- ``"grid"``  : tile-by-tile stepping (classic JRPG), tweened over ``move_time``.

Controllers (player input, AI) only set the *intent* (``input_dx/input_dy`` for
grid, or ``vx/vy`` for smooth); the MovementSystem turns intent into collision-
resolved motion. This separation means the same MovementSystem drives the player
and every NPC/enemy.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.ecs.component import Component, component


@component("movement")
@dataclass
class MovementComponent(Component):
    style: str = "smooth"        # "smooth" | "grid"
    speed: float = 60.0          # px/sec (smooth) -- grid uses move_time instead
    run_multiplier: float = 1.0  # applied when the "run" intent is set
    move_time: float = 0.15      # seconds per tile (grid)

    # --- runtime intent (written by controllers/AI each frame) ---
    vx: float = 0.0              # desired velocity (smooth)
    vy: float = 0.0
    input_dx: int = 0            # desired step direction (grid): -1/0/1
    input_dy: int = 0
    running: bool = False

    # --- runtime flags ---
    moving: bool = False         # set by MovementSystem if the entity moved this frame

    # --- runtime grid-tween state (managed by MovementSystem) ---
    is_moving: bool = False
    _t: float = 0.0              # tween progress in seconds
    _sx: float = 0.0             # tween start
    _sy: float = 0.0
    _tx: float = 0.0             # tween target
    _ty: float = 0.0
