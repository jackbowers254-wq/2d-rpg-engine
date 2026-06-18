"""
Reusable, resolution-aware UI toolkit.

Every widget draws in LOGICAL (base-resolution) pixels through the renderer, so
the whole UI scales with the window automatically -- there is no separate "UI
resolution" to manage. Colours, fonts, padding and spacing all come from the
``ui.*`` config via :class:`UIStyle`, so a game re-skins the UI by editing config.
"""

from engine.ui.style import UIStyle
from engine.ui.text import draw_text, wrap_text
from engine.ui.panel import Panel
from engine.ui.menu import Menu
from engine.ui.dialogue_box import DialogueBox
from engine.ui.healthbar import HealthBar

__all__ = ["UIStyle", "draw_text", "wrap_text", "Panel", "Menu", "DialogueBox", "HealthBar"]
