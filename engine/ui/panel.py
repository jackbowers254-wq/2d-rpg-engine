"""
engine.ui.panel
=============
A bordered, filled box -- the base "window" every other UI element sits in.
Draws on the configured ``ui`` layer in logical pixels, so it scales with the
display like everything else.
"""

from __future__ import annotations


class Panel:
    def __init__(self, x: float, y: float, w: float, h: float, style,
                 *, layer: str = "ui") -> None:
        self.x, self.y, self.w, self.h = x, y, w, h
        self.style = style
        self.layer = layer

    @property
    def rect(self):
        return (self.x, self.y, self.w, self.h)

    @property
    def inner_x(self) -> float:
        return self.x + self.style.padding

    @property
    def inner_y(self) -> float:
        return self.y + self.style.padding

    @property
    def inner_width(self) -> float:
        return self.w - 2 * self.style.padding

    def draw(self, renderer) -> None:
        s = self.style
        renderer.draw_rect(self.rect, s.box_color, layer=self.layer, world=False)
        if s.border_width > 0:
            renderer.draw_rect(self.rect, s.border_color, layer=self.layer,
                               world=False, width=s.border_width)
