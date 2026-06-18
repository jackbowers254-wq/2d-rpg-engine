"""
engine.ui.menu
============
A vertical selectable menu (title screen, pause menu, inventory list, battle
command list -- all the same widget). The scene feeds it navigation
(``move(+/-1)``) and reads ``selected`` on confirm; the widget owns drawing the
cursor and highlight. Items can be disabled (skipped by navigation).
"""

from __future__ import annotations

from typing import Callable, List, Optional


class MenuItem:
    def __init__(self, label: str, value=None, enabled: bool = True,
                 action: Optional[Callable] = None) -> None:
        self.label = label
        self.value = value if value is not None else label
        self.enabled = enabled
        self.action = action


class Menu:
    def __init__(self, items: List, style, *, title: str = "",
                 layer: str = "ui") -> None:
        self.items: List[MenuItem] = [
            i if isinstance(i, MenuItem) else MenuItem(str(i), i) for i in items
        ]
        self.style = style
        self.title = title
        self.layer = layer
        self.index = 0
        self._ensure_enabled(1)

    # -- navigation ----------------------------------------------------------
    def _ensure_enabled(self, direction: int) -> None:
        n = len(self.items)
        for _ in range(n):
            if self.items and self.items[self.index].enabled:
                return
            self.index = (self.index + direction) % n

    def move(self, delta: int) -> None:
        if not self.items:
            return
        n = len(self.items)
        self.index = (self.index + delta) % n
        # skip disabled entries in the same direction
        for _ in range(n):
            if self.items[self.index].enabled:
                break
            self.index = (self.index + (1 if delta >= 0 else -1)) % n

    @property
    def selected(self) -> Optional[MenuItem]:
        return self.items[self.index] if self.items else None

    def confirm(self):
        item = self.selected
        if item and item.enabled and item.action:
            item.action()
        return item

    def set_items(self, items: List) -> None:
        self.items = [i if isinstance(i, MenuItem) else MenuItem(str(i), i) for i in items]
        self.index = 0
        self._ensure_enabled(1)

    # -- drawing -------------------------------------------------------------
    def draw(self, renderer, x: float, y: float, line_height: Optional[int] = None) -> None:
        s = self.style
        font = s.font
        lh = line_height or (s.line_height + 2)
        cy = y
        if self.title:
            renderer.draw_text(self.title, x, cy, s.title_font, s.highlight_color,
                               layer=self.layer, world=False)
            cy += s.title_font.get_height() + 4
        for i, item in enumerate(self.items):
            selected = (i == self.index)
            if not item.enabled:
                color = s.disabled_color
            elif selected:
                color = s.highlight_color
            else:
                color = s.text_color
            prefix = (s.cursor + " ") if selected else "  "
            renderer.draw_text(prefix + item.label, x, cy, font, color,
                               layer=self.layer, world=False)
            cy += lh
