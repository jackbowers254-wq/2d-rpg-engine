"""
engine.graphics.animation
========================
Backend-agnostic animation data: clips and sets.

- :class:`AnimationClip` is an ordered list of ``(sheet_frame_index, duration)``
  steps plus a loop flag. It can sample "which frame at time t".
- :class:`AnimationSet` bundles a :class:`SpriteSheet` with named clips and knows
  how to resolve a *logical state* + *facing* into a concrete clip name, with
  graceful fallbacks (``walk_left`` -> ``walk`` -> default).

Both are produced two ways (see the asset manager):
- from an **Aseprite** export (frame tags + per-frame timings), or
- from a **grid sheet** + a simple ``{clip: [frame indices]}`` map at a fixed FPS.

Nothing here touches pygame beyond holding surfaces, so it is easy to test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from engine.graphics.spritesheet import SpriteSheet

# A facing-aware clip lookup tries, in order: "<state>_<facing>", "<state>",
# then the set's default clip.
_FACINGS = ("down", "up", "left", "right")


@dataclass
class AnimationClip:
    name: str
    # each step: (frame index into the sheet, duration in seconds)
    steps: List[Tuple[int, float]]
    loop: bool = True

    @property
    def duration(self) -> float:
        return sum(d for _, d in self.steps) or 0.001

    def frame_at(self, t: float) -> int:
        """Return the sheet frame index shown at elapsed time ``t`` seconds."""
        if not self.steps:
            return 0
        if self.loop:
            t = t % self.duration
        elif t >= self.duration:
            return self.steps[-1][0]
        acc = 0.0
        for frame_index, dur in self.steps:
            acc += dur
            if t < acc:
                return frame_index
        return self.steps[-1][0]


class AnimationSet:
    def __init__(self, sheet: SpriteSheet, clips: Dict[str, AnimationClip],
                 default: Optional[str] = None) -> None:
        self.sheet = sheet
        self.clips = clips
        self.default = default or (next(iter(clips), "") if clips else "")

    def has(self, clip_name: str) -> bool:
        return clip_name in self.clips

    def resolve(self, state: str, facing: str = "", directional: bool = False) -> str:
        """Pick the best existing clip for a logical state + facing."""
        if directional and facing:
            cand = f"{state}_{facing}"
            if cand in self.clips:
                return cand
        if state in self.clips:
            return state
        # last resort: a same-state clip for any facing, else the default
        if directional:
            for f in _FACINGS:
                if f"{state}_{f}" in self.clips:
                    return f"{state}_{f}"
        return self.default

    def surface_at(self, clip_name: str, t: float):
        """Return (surface, frame_index) for a clip at elapsed time ``t``."""
        clip = self.clips.get(clip_name)
        if clip is None:
            return self.sheet.frame(0), 0
        idx = clip.frame_at(t)
        return self.sheet.frame(idx), idx


def build_grid_set(sheet: SpriteSheet, clips_by_index: Dict[str, List[int]],
                   fps: float = 8.0, *, loop: bool = True,
                   non_looping: Optional[List[str]] = None) -> AnimationSet:
    """Build an AnimationSet from a grid sheet + {clip: [frame indices]} at FPS."""
    non_looping = set(non_looping or [])
    dur = 1.0 / max(fps, 0.001)
    clips: Dict[str, AnimationClip] = {}
    for name, indices in clips_by_index.items():
        steps = [(i, dur) for i in indices]
        clips[name] = AnimationClip(name, steps, loop=name not in non_looping and loop)
    return AnimationSet(sheet, clips)
