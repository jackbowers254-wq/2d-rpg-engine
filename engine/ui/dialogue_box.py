"""
engine.ui.dialogue_box
=====================
A self-contained dialogue widget that drives a
:class:`~engine.dialogue.dialogue_system.DialogueSystem` and renders it: a
bottom text panel with speaker name, a typewriter text reveal, and a choice list.

The owning scene only has to forward input:
- ``confirm()``      : reveal-all if still typing, else pick the highlighted
  choice / advance to the next node.
- ``move_choice(±1)``: change the highlighted choice.
and call ``update(dt)`` + ``draw(renderer)`` each frame. When
``dialogue.finished`` becomes true the scene pops itself.

Because it works purely through the renderer in logical pixels, it scales with
the display and re-skins from ``ui.*`` config like every other widget.
"""

from __future__ import annotations

from engine.ui.panel import Panel
from engine.ui.text import wrap_text


class DialogueBox:
    def __init__(self, dialogue, style, *, height: int = 56, margin: int = 6) -> None:
        self.dialogue = dialogue
        self.style = style
        self.height = height
        self.margin = margin
        self._revealed = 0.0
        self._choice = 0
        self._synced_id = object()  # sentinel so first sync always fires

    # -- state sync ----------------------------------------------------------
    def _sync(self) -> None:
        """Reset typewriter/choice state when the dialogue moves to a new node."""
        if self.dialogue.current_id != self._synced_id:
            self._synced_id = self.dialogue.current_id
            self._revealed = 0.0
            self._choice = 0

    # -- update --------------------------------------------------------------
    def update(self, dt: float) -> None:
        self._sync()
        node = self.dialogue.current
        if node is None:
            return
        self._revealed = min(len(node.text), self._revealed + self.style.text_speed * dt)

    @property
    def fully_revealed(self) -> bool:
        node = self.dialogue.current
        return node is not None and self._revealed >= len(node.text)

    # -- input ---------------------------------------------------------------
    def confirm(self) -> None:
        node = self.dialogue.current
        if node is None:
            return
        if not self.fully_revealed:
            self._revealed = len(node.text)  # skip the typewriter
            return
        if node.choices:
            self.dialogue.choose(self._choice)
        else:
            self.dialogue.advance()
        self._sync()

    def move_choice(self, delta: int) -> None:
        node = self.dialogue.current
        if node and node.choices and self.fully_revealed:
            self._choice = (self._choice + delta) % len(node.choices)

    # -- draw ----------------------------------------------------------------
    def draw(self, renderer) -> None:
        node = self.dialogue.current
        if node is None:
            return
        s = self.style
        base_w, base_h = renderer.base_size
        panel = Panel(self.margin, base_h - self.height - self.margin,
                      base_w - 2 * self.margin, self.height, s)
        panel.draw(renderer)

        x = panel.inner_x
        y = panel.inner_y
        # Speaker name (highlighted).
        if node.speaker:
            renderer.draw_text(node.speaker, x, y, s.font, s.highlight_color,
                               layer="ui", world=False)
            y += s.line_height + 1

        # Typewriter body text.
        shown = node.text[: int(self._revealed)]
        lines = wrap_text(s.font, shown, int(panel.inner_width))
        for line in lines:
            renderer.draw_text(line, x, y, s.font, s.text_color, layer="ui", world=False)
            y += s.line_height

        # Choices (only once text is fully revealed).
        if self.fully_revealed and node.choices:
            y += 1
            for i, choice in enumerate(node.choices):
                color = s.highlight_color if i == self._choice else s.text_color
                prefix = (s.cursor + " ") if i == self._choice else "  "
                renderer.draw_text(prefix + choice.text, x + 4, y, s.font, color,
                                   layer="ui", world=False)
                y += s.line_height
        elif self.fully_revealed:
            # A small "continue" hint.
            renderer.draw_text(s.cursor, base_w - self.margin - 10,
                               panel.y + self.height - s.line_height - 2,
                               s.font, s.highlight_color, layer="ui", world=False)
