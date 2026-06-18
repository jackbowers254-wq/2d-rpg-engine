"""
engine.ui.text
=============
Text helpers: word-wrapping and a convenience block drawer. Kept separate so any
widget (or a scene) can lay out wrapped text the same way.
"""

from __future__ import annotations

from typing import List


def wrap_text(font, text: str, max_width: int) -> List[str]:
    """Greedy word-wrap ``text`` to fit ``max_width`` logical pixels.

    Respects explicit newlines in the source string.
    """
    lines: List[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            trial = word if not current else current + " " + word
            if font.size(trial)[0] <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def draw_text(renderer, text: str, x: float, y: float, font, color,
              *, layer: str = "ui", max_width: int = 0, line_spacing: int = 1) -> int:
    """Draw text (optionally wrapped). Returns the height drawn, in pixels."""
    if max_width > 0:
        lines = wrap_text(font, text, max_width)
    else:
        lines = text.split("\n")
    lh = font.get_height() + line_spacing
    for i, line in enumerate(lines):
        renderer.draw_text(line, x, y + i * lh, font, color, layer=layer, world=False)
    return len(lines) * lh
