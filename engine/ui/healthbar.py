"""
engine.ui.healthbar
=================
A simple fraction bar (HP/MP/XP/cast progress -- anything 0..1). Draw it in
SCREEN space for a HUD, or in WORLD space above an entity (pass ``world=True``).
Colours come from the UIStyle so it matches the rest of the UI.
"""

from __future__ import annotations


class HealthBar:
    def __init__(self, style, *, width: int = 48, height: int = 5,
                 layer: str = "ui") -> None:
        self.style = style
        self.width = width
        self.height = height
        self.layer = layer

    def draw(self, renderer, x: float, y: float, fraction: float,
             *, world: bool = False, label: str = "") -> None:
        s = self.style
        fraction = max(0.0, min(1.0, fraction))
        bg = (x, y, self.width, self.height)
        fg = (x, y, self.width * fraction, self.height)
        renderer.draw_rect(bg, s.hp_bg, layer=self.layer, world=world)
        if fraction > 0:
            renderer.draw_rect(fg, s.hp_fg, layer=self.layer, world=world)
        if s.border_width > 0:
            renderer.draw_rect(bg, s.border_color, layer=self.layer, world=world,
                               width=s.border_width)
        if label:
            renderer.draw_text(label, x, y - s.line_height, s.font, s.text_color,
                               layer=self.layer, world=world)
