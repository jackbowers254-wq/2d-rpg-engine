"""
EXTENSION HOOK: frame animation.

A minimal, optional component the render system understands: if present, it
advances through frames of a sprite sheet over time. The demo doesn't ship sheet
art, so it's wired but dormant -- it exists to show exactly where sprite-sheet
animation, per-direction frames, and animation-state machines slot in without
disturbing anything else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from engine.ecs.component import Component, component


@component("animation")
@dataclass
class AnimationComponent(Component):
    sheet: str = ""                 # path to a sprite sheet image
    frame_size: List[int] = field(default_factory=lambda: [16, 16])
    fps: float = 8.0
    # name -> list of frame indices, e.g. {"walk_down": [0,1,2,1]}
    clips: Dict[str, List[int]] = field(default_factory=dict)
    current: str = ""
    # runtime
    _time: float = 0.0
    _frame: int = 0
