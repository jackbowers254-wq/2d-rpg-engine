"""
tools/preview.py
==============
A lightweight in-engine art previewer (NOT an editor). It loads an animation set
(an Aseprite ``.json`` export or any sprite), plays it under the REAL engine
renderer (so you see exactly how art will look in-game, pixel-perfect upscaled),
and lets you cycle animation states.

Run:
    python tools/preview.py                 # previews hero.json
    python tools/preview.py slime.json      # previews any sprites/<file>

Controls (reusing the engine's input bindings):
    LEFT / RIGHT  : previous / next animation clip
    UP / DOWN     : zoom out / in
    Confirm (E)   : pause / play
    Cancel (Esc)  : quit

Phase C extends this previewer with palette-swap and lighting/post-process
toggles; the hooks are marked below.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame  # noqa: E402

from engine.core.game import Game  # noqa: E402
from engine.core.scene import Scene  # noqa: E402


class PreviewScene(Scene):
    def on_enter(self, **kwargs) -> None:
        g = self.game
        # source is supplied by the factory (preset_source) or via switch kwargs.
        self.source = kwargs.get("source", getattr(self, "preset_source", "hero.json"))
        self.anim = g.assets.get_animation_set(self.source)
        self.clip_names = sorted(self.anim.clips)
        self.index = 0
        self.time = 0.0
        self.paused = False
        self.zoom = 6
        self.font = g.assets.get_font(8)

    @property
    def clip(self):
        return self.clip_names[self.index] if self.clip_names else ""

    def update(self, dt: float) -> None:
        inp = self.game.input
        if inp.just_pressed("cancel") or inp.just_pressed("menu"):
            self.game.quit()
        if inp.just_pressed("right"):
            self.index = (self.index + 1) % len(self.clip_names); self.time = 0
        if inp.just_pressed("left"):
            self.index = (self.index - 1) % len(self.clip_names); self.time = 0
        if inp.just_pressed("up"):
            self.zoom = max(1, self.zoom - 1)
        if inp.just_pressed("down"):
            self.zoom = min(16, self.zoom + 1)
        if inp.just_pressed("confirm"):
            self.paused = not self.paused
        if not self.paused:
            self.time += dt

    def draw(self, renderer) -> None:
        bw, bh = renderer.base_size
        # Checkerboard so transparency is visible.
        for y in range(0, bh, 8):
            for x in range(0, bw, 8):
                shade = 60 if (x // 8 + y // 8) % 2 else 48
                renderer.draw_rect((x, y, 8, 8), (shade, shade, shade + 8),
                                   layer="background", world=False)

        surf, frame_idx = self.anim.surface_at(self.clip, self.time)
        # EXTENSION HOOK (Phase C): apply a palette swap / lighting / post-fx to
        # `surf` here to preview art under those systems.
        big = pygame.transform.scale(
            surf, (surf.get_width() * self.zoom, surf.get_height() * self.zoom))
        renderer.draw_image(big, bw // 2 - big.get_width() // 2,
                            bh // 2 - big.get_height() // 2, layer="entities", world=False)

        info = [
            f"src: {self.source}",
            f"clip: {self.clip}  ({self.index + 1}/{len(self.clip_names)})",
            f"frame: {frame_idx}   zoom x{self.zoom}   {'PAUSED' if self.paused else 'playing'}",
            "LEFT/RIGHT clip  UP/DOWN zoom  E pause  Esc quit",
        ]
        y = 2
        for line in info:
            renderer.draw_text(line, 2, y, self.font, (235, 235, 245),
                               layer="ui", world=False)
            y += 9


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else "hero.json"
    game = Game("config/config.json", overrides={"game": {"start_scene": "preview"}})

    def factory(g):
        scene = PreviewScene(g)
        scene.preset_source = source  # picked up by on_enter
        return scene

    game.scenes.register("preview", factory)
    game.run()


if __name__ == "__main__":
    main()
