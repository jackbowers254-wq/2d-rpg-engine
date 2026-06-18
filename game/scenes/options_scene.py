"""
game.scenes.options_scene
======================
A small settings overlay for audio volumes (Master / Music / SFX). Up/Down select
a row, Left/Right adjust by 10%. Changes apply live through the AudioManager and
update the in-memory settings.
"""

from __future__ import annotations

from engine.core.scene import Scene
from engine.ui.panel import Panel


class OptionsScene(Scene):
    transparent = True
    blocks_update = True

    KINDS = [("master", "Master"), ("music", "Music"), ("sfx", "SFX")]

    def on_enter(self, **kwargs) -> None:
        self.style = self.game.style
        self.row = 0

    def update(self, dt: float) -> None:
        inp = self.game.input
        if inp.just_pressed("cancel") or inp.just_pressed("menu"):
            self.game.scenes.pop()
            return
        if inp.just_pressed("up"):
            self.row = (self.row - 1) % len(self.KINDS)
        if inp.just_pressed("down"):
            self.row = (self.row + 1) % len(self.KINDS)
        kind = self.KINDS[self.row][0]
        if inp.just_pressed("right"):
            self.game.audio.set_volume(kind, self.game.audio.get_volume(kind) + 0.1)
            self.game.audio.play_sound("confirm.wav")
        if inp.just_pressed("left"):
            self.game.audio.set_volume(kind, self.game.audio.get_volume(kind) - 0.1)

    def draw(self, renderer) -> None:
        s = self.style
        bw, bh = renderer.base_size
        renderer.draw_rect((0, 0, bw, bh), (0, 0, 0, 160), layer="ui", world=False)
        panel = Panel(bw // 2 - 70, bh // 2 - 40, 140, 80, s)
        panel.draw(renderer)
        x, y = panel.inner_x, panel.inner_y
        renderer.draw_text("Audio", x, y, s.title_font, s.highlight_color, layer="ui", world=False)
        y += s.title_font.get_height() + 4
        for i, (kind, label) in enumerate(self.KINDS):
            sel = (i == self.row)
            color = s.highlight_color if sel else s.text_color
            renderer.draw_text((s.cursor + " " if sel else "  ") + label, x, y, s.font,
                               color, layer="ui", world=False)
            # volume bar
            vol = self.game.audio.get_volume(kind)
            bx, bw_ = x + 60, 64
            renderer.draw_rect((bx, y + 1, bw_, 5), s.hp_bg, layer="ui", world=False)
            renderer.draw_rect((bx, y + 1, int(bw_ * vol), 5), s.highlight_color,
                               layer="ui", world=False)
            y += s.line_height + 2
        renderer.draw_text("Left/Right adjust   Esc close", bw // 2, bh - 14, s.font,
                           s.disabled_color, layer="ui", world=False, anchor="center")
