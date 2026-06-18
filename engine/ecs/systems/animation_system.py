"""
engine.ecs.systems.animation_system
==================================
Advances every entity's AnimationComponent and produces its current frame.

Responsibilities each frame:
1. Lazily resolve the entity's AnimationSet (Aseprite ``source`` or grid ``sheet``).
2. Choose the logical state:
   - a pending one-shot (e.g. "attack") plays fully, then reverts;
   - else, if ``auto_state`` and the entity has movement, "walk" when moving and
     "idle" otherwise;
   - else the component's ``state``.
3. Resolve that state + facing into a concrete clip (with fallbacks) and sample
   the frame at the elapsed time, storing it on ``anim.current_surface`` for the
   RenderSystem to draw.

Runs after MovementSystem (so the moving flag/facing are current) and before
rendering. Entities without an AnimationComponent are untouched (static sprites).
"""

from __future__ import annotations

from engine.ecs.system import System
from engine.utils.logger import get_logger

log = get_logger("animation")


class AnimationSystem(System):
    required = ("animation",)
    priority = 60  # after movement (50), before draw

    def __init__(self, assets) -> None:
        self.assets = assets

    def _resolve_set(self, anim):
        if anim._set is not None:
            return anim._set
        try:
            if anim.source:
                anim._set = self.assets.get_animation_set(anim.source)
            elif anim.sheet:
                anim._set = self.assets.make_grid_animation_set(
                    anim.sheet, anim.frame_size[0], anim.frame_size[1],
                    anim.clips, anim.fps)
        except Exception:  # noqa: BLE001 - a bad sheet shouldn't crash the loop
            log.exception("Failed to load animation set '%s'", anim.source or anim.sheet)
            anim._set = False  # sentinel: don't retry every frame
        return anim._set or None

    def update(self, world, dt: float) -> None:
        for e in self.entities(world):
            anim = e.get("animation")
            aset = self._resolve_set(anim)
            if aset is None:
                continue

            facing = e.get("transform").facing if e.has("transform") else "down"
            state = self._select_state(e, anim, aset)
            clip = aset.resolve(state, facing, anim.directional)

            if clip != anim._clip:
                anim._clip = clip
                anim._time = 0.0
            anim._time += dt * anim.speed

            anim.current_surface, _ = aset.surface_at(clip, anim._time)

            # End a finished one-shot and revert to normal state next frame.
            if anim._oneshot_active:
                c = aset.clips.get(clip)
                if c is not None and not c.loop and anim._time >= c.duration:
                    anim._oneshot_active = False
                    anim.oneshot = None

    def _select_state(self, e, anim, aset) -> str:
        # Begin a pending one-shot.
        if anim.oneshot and not anim._oneshot_active:
            anim._oneshot_active = True
            anim._time = 0.0
        if anim._oneshot_active and anim.oneshot:
            return anim.oneshot
        if anim.auto_state and e.has("movement"):
            return "walk" if e.get("movement").moving else "idle"
        return anim.state
