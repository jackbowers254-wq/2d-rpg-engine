"""
Animation component.

Points an entity at an AnimationSet (an Aseprite export via ``source``, or a grid
sheet via ``sheet``+``clips``) and tracks playback. The AnimationSystem advances
it each frame and hands the current frame to the renderer.

State selection is data-driven and, by default, automatic:
- ``auto_state``  : derive ``"walk"``/``"idle"`` from whether the entity is moving.
- ``directional`` : append the facing (``walk_down``) and fall back gracefully.
- ``state``       : the logical state when not auto-driven (or for non-movers),
  e.g. set to ``"attack"`` for a one-shot and the system plays it then reverts.

Backward compatible: an entity with no animation component just renders its static
Sprite, exactly as in Gen 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from engine.ecs.component import Component, component


@component("animation")
@dataclass
class AnimationComponent(Component):
    # Source of frames: an Aseprite ".json" export...
    source: str = ""
    # ...or a plain grid sheet (used if 'source' is empty):
    sheet: str = ""
    frame_size: List[int] = field(default_factory=lambda: [16, 16])
    clips: Dict[str, List[int]] = field(default_factory=dict)  # {clip: [indices]}
    fps: float = 8.0

    # Playback / selection.
    state: str = "idle"
    directional: bool = True
    auto_state: bool = True
    speed: float = 1.0
    # A one-shot clip (e.g. "attack") to play once, then revert to auto/state.
    oneshot: Optional[str] = None

    def __post_init__(self) -> None:
        # Runtime (not serialized): resolved set, timer, last clip, current frame.
        self._set = None
        self._time = 0.0
        self._clip = ""
        self._oneshot_active = False
        self.current_surface = None

    def play_once(self, clip: str) -> None:
        """Request a one-shot clip (attack swing, hit reaction, ...)."""
        self.oneshot = clip
        self._oneshot_active = False  # picked up by the system next frame

    def to_data(self) -> dict:
        return {
            "source": self.source, "sheet": self.sheet,
            "frame_size": self.frame_size, "clips": self.clips, "fps": self.fps,
            "state": self.state, "directional": self.directional,
            "auto_state": self.auto_state, "speed": self.speed,
        }
