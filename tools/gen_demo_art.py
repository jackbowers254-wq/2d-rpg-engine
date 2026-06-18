"""
tools/gen_demo_art.py
====================
Generates the demo's placeholder pixel art in **Aseprite export format** (a PNG
sheet + a matching JSON with frame tags and per-frame durations), so the engine's
Aseprite import path is exercised by real files.

In a real project you would make this art in Aseprite and export it the same way;
this script just stands in for that so the repo needs no binary art authored by
hand. Re-run with:  python tools/gen_demo_art.py

Outputs:
  assets/sprites/hero.png  + hero.json   (4-direction idle/walk)
  assets/sprites/slime.png + slime.json  (idle/walk/hit, non-directional)
"""

import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((8, 8))

F = 16  # frame size


def aseprite_json(image, frame_count, tags, durations):
    frames = {}
    for i in range(frame_count):
        frames[f"{image} {i}"] = {
            "frame": {"x": i * F, "y": 0, "w": F, "h": F},
            "rotated": False, "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": F, "h": F},
            "sourceSize": {"w": F, "h": F},
            "duration": durations[i],
        }
    return {
        "frames": frames,
        "meta": {
            "app": "tools/gen_demo_art.py", "version": "1.0",
            "image": f"{image}.png", "format": "RGBA8888",
            "size": {"w": F * frame_count, "h": F}, "scale": "1",
            "frameTags": tags, "slices": [],
        },
    }


def new_sheet(n):
    surf = pygame.Surface((F * n, F), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    return surf


def rect(surf, fi, color, x, y, w, h):
    pygame.draw.rect(surf, color, (fi * F + x, y, w, h))


# ---------------- HERO: 12 frames (idle+2 walk per direction) ----------------
def gen_hero():
    body = (70, 130, 235)
    body_d = (45, 95, 190)
    head = (235, 205, 150)
    eye = (30, 30, 45)
    n = 12
    sheet = new_sheet(n)
    # (direction, pose) per frame index
    layout = [
        ("down", "idle"), ("down", "w1"), ("down", "w2"),
        ("up", "idle"), ("up", "w1"), ("up", "w2"),
        ("left", "idle"), ("left", "w1"), ("left", "w2"),
        ("right", "idle"), ("right", "w1"), ("right", "w2"),
    ]
    for i, (d, pose) in enumerate(layout):
        # torso
        rect(sheet, i, body, 4, 5, 8, 8)
        rect(sheet, i, body_d, 4, 11, 8, 2)
        # head
        rect(sheet, i, head, 5, 1, 6, 5)
        # eyes by direction
        if d == "down":
            rect(sheet, i, eye, 6, 3, 1, 1); rect(sheet, i, eye, 9, 3, 1, 1)
        elif d == "up":
            rect(sheet, i, body_d, 5, 1, 6, 2)  # back of head
        elif d == "left":
            rect(sheet, i, eye, 6, 3, 1, 1)
        else:  # right
            rect(sheet, i, eye, 9, 3, 1, 1)
        # feet (animate on walk)
        if pose == "idle":
            lx, rx = 4, 9
        elif pose == "w1":
            lx, rx = 3, 10
        else:
            lx, rx = 5, 8
        rect(sheet, i, body_d, lx, 13, 3, 3)
        rect(sheet, i, body_d, rx, 13, 3, 3)

    pygame.image.save(sheet, "assets/sprites/hero.png")
    tags = [
        {"name": "idle_down", "from": 0, "to": 0, "direction": "forward"},
        {"name": "walk_down", "from": 1, "to": 2, "direction": "forward"},
        {"name": "idle_up", "from": 3, "to": 3, "direction": "forward"},
        {"name": "walk_up", "from": 4, "to": 5, "direction": "forward"},
        {"name": "idle_left", "from": 6, "to": 6, "direction": "forward"},
        {"name": "walk_left", "from": 7, "to": 8, "direction": "forward"},
        {"name": "idle_right", "from": 9, "to": 9, "direction": "forward"},
        {"name": "walk_right", "from": 10, "to": 11, "direction": "forward"},
    ]
    durations = [300, 130, 130, 300, 130, 130, 300, 130, 130, 300, 130, 130]
    with open("assets/sprites/hero.json", "w") as fh:
        json.dump(aseprite_json("hero", n, tags, durations), fh, indent=1)
    print("wrote hero.png + hero.json (12 frames)")


# ---------------- SLIME: 5 frames (idle x2, walk x2, hit x1) ----------------
def gen_slime():
    body = (110, 200, 120)
    body_d = (70, 150, 85)
    eye = (20, 40, 25)
    hit = (255, 255, 255)
    n = 5
    sheet = new_sheet(n)
    # idle 0: squashed, idle 1: taller (breathing)
    poses = [(2, 9, 12, 6), (2, 7, 12, 8), (1, 8, 14, 7), (3, 8, 10, 7), None]
    for i in range(n):
        if i == 4:  # hit frame: bright flash silhouette
            rect(sheet, i, hit, 2, 7, 12, 8)
            continue
        x, y, w, h = poses[i]
        rect(sheet, i, body, x, y, w, h)
        rect(sheet, i, body_d, x, y + h - 2, w, 2)
        rect(sheet, i, eye, x + 3, y + 2, 1, 1)
        rect(sheet, i, eye, x + w - 4, y + 2, 1, 1)
    pygame.image.save(sheet, "assets/sprites/slime.png")
    tags = [
        {"name": "idle", "from": 0, "to": 1, "direction": "forward"},
        {"name": "walk", "from": 2, "to": 3, "direction": "forward"},
        {"name": "hit", "from": 4, "to": 4, "direction": "forward", "repeat": "1"},
    ]
    durations = [350, 350, 160, 160, 120]
    with open("assets/sprites/slime.json", "w") as fh:
        json.dump(aseprite_json("slime", n, tags, durations), fh, indent=1)
    print("wrote slime.png + slime.json (5 frames)")


if __name__ == "__main__":
    os.makedirs("assets/sprites", exist_ok=True)
    gen_hero()
    gen_slime()
    print("done")
