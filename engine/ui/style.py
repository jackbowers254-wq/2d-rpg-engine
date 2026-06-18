"""
engine.ui.style
==============
Central UI theme pulled from config (``ui.*``). Widgets take a UIStyle instead of
hardcoding colours/fonts, so the entire interface is re-skinnable from config and
consistent across every menu/box/bar.
"""

from __future__ import annotations


class UIStyle:
    def __init__(self, settings, assets) -> None:
        self.settings = settings
        self.assets = assets

        self.text_color = tuple(settings.get("ui.text_color", [235, 235, 245]))
        self.disabled_color = tuple(settings.get("ui.disabled_color", [120, 120, 140]))
        self.highlight_color = tuple(settings.get("ui.highlight_color", [250, 220, 90]))
        self.box_color = tuple(settings.get("ui.box_color", [20, 18, 40]))
        self.border_color = tuple(settings.get("ui.box_border_color", [120, 130, 200]))
        self.border_width = settings.get("ui.box_border_width", 1)
        self.padding = settings.get("ui.box_padding", 6)
        self.text_speed = settings.get("ui.text_speed", 36)
        self.cursor = settings.get("ui.cursor", ">")
        self.hp_bg = tuple(settings.get("ui.healthbar_bg", [60, 20, 30]))
        self.hp_fg = tuple(settings.get("ui.healthbar_fg", [210, 60, 70]))

        self._font_size = settings.get("ui.font_size", 8)
        self._title_size = settings.get("ui.title_font_size", 16)

    @property
    def font(self):
        return self.assets.get_font(self._font_size)

    @property
    def title_font(self):
        return self.assets.get_font(self._title_size)

    def font_of(self, size: int):
        return self.assets.get_font(size)

    @property
    def line_height(self) -> int:
        return self.font.get_height()
