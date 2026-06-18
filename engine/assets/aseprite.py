"""
engine.assets.aseprite
=====================
Import an **Aseprite** sprite-sheet export (the ``.json`` + ``.png`` Aseprite
produces) into an :class:`~engine.graphics.animation.AnimationSet`, complete with
per-frame timings, animation tags and slices.

This is the recommended "bring in good art" path: draw/animate in Aseprite, export
"Sheet type: by frame" with JSON data + frame tags, drop both files in
``assets/sprites/``, and reference the ``.json`` from an entity's ``animation``
component. Frame durations and tag directions (forward / reverse / pingpong) come
through automatically, so animations are ready to play.

Both JSON layouts are supported:
- **hash**  : ``"frames": { "name 0": {...}, ... }``
- **array** : ``"frames": [ {"filename": "...", ...}, ... ]``

Slices (e.g. a named hitbox or anchor) are captured into ``AnimationSet.slices``
for game code to use.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List

from engine.graphics.animation import AnimationClip, AnimationSet
from engine.graphics.spritesheet import SpriteSheet
from engine.utils.logger import get_logger

log = get_logger("aseprite")


def _ordered_frames(frames) -> List[dict]:
    """Normalise Aseprite 'frames' (hash or array) into an ordered list."""
    if isinstance(frames, list):
        return frames
    # Hash: JSON preserves insertion order, which Aseprite writes in frame order.
    return list(frames.values())


def _tag_sequence(from_i: int, to_i: int, direction: str) -> List[int]:
    fwd = list(range(from_i, to_i + 1))
    if direction == "reverse":
        return list(reversed(fwd))
    if direction == "pingpong":
        return fwd + list(reversed(fwd[1:-1])) if len(fwd) > 2 else fwd
    return fwd


def load_aseprite(json_path: str, assets) -> AnimationSet:
    """Load an Aseprite JSON+sheet into an AnimationSet (durations + tags)."""
    with open(json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    base_dir = os.path.dirname(json_path)
    meta = data.get("meta", {})
    image_name = meta.get("image") or (os.path.splitext(os.path.basename(json_path))[0] + ".png")
    atlas = assets.get_image(os.path.join(base_dir, image_name))

    frames = _ordered_frames(data.get("frames", []))
    rects = []
    durations = []
    for fr in frames:
        f = fr["frame"]
        rects.append((f["x"], f["y"], f["w"], f["h"]))
        durations.append(max(1, fr.get("duration", 100)) / 1000.0)  # ms -> s
    sheet = SpriteSheet(atlas, rects)

    clips: Dict[str, AnimationClip] = {}
    tags = meta.get("frameTags", [])
    for tag in tags:
        name = tag.get("name", "clip")
        seq = _tag_sequence(tag.get("from", 0), tag.get("to", len(frames) - 1),
                            tag.get("direction", "forward"))
        steps = [(i, durations[i] if i < len(durations) else 0.1) for i in seq]
        # Aseprite's "repeat" field (1 = play once) maps to non-looping.
        loop = str(tag.get("repeat", "")) != "1"
        clips[name] = AnimationClip(name, steps, loop=loop)

    if not clips:  # no tags -> one clip over every frame
        steps = [(i, durations[i]) for i in range(len(frames))]
        clips["default"] = AnimationClip("default", steps, loop=True)

    anim_set = AnimationSet(sheet, clips)
    # Capture slices (hitboxes / anchors) for game code.
    anim_set.slices = {s.get("name"): s for s in meta.get("slices", [])}  # type: ignore[attr-defined]
    log.info("Loaded Aseprite '%s': %d frames, clips=%s",
             os.path.basename(json_path), len(frames), sorted(clips))
    return anim_set
