"""
game.scenes.title_scene
=====================
The main menu. Demonstrates the scene system and reuses the Menu widget. New
Game creates a fresh GameState; Continue loads slot 1; Quit exits.
"""

from __future__ import annotations

from engine.core.scene import Scene
from engine.ui.menu import Menu, MenuItem
from game.state import GameState


class TitleScene(Scene):
    def on_enter(self, **kwargs) -> None:
        g = self.game
        self.style = g.style
        has_save = any(meta for _, meta in g.saves.list_slots())

        self.menu = Menu([
            MenuItem("New Game", "new"),
            MenuItem("Continue", "continue", enabled=has_save),
            MenuItem("Quit", "quit"),
        ], self.style)

    def update(self, dt: float) -> None:
        inp = self.game.input
        if inp.just_pressed("up"):
            self.menu.move(-1)
        if inp.just_pressed("down"):
            self.menu.move(1)
        if inp.just_pressed("confirm") or inp.just_pressed("interact"):
            self._activate(self.menu.selected.value)

    def _activate(self, choice: str) -> None:
        g = self.game
        if choice == "quit":
            g.quit()
            return
        # Build a fresh shared state, then either start clean or load slot 1.
        g.state = GameState(g.settings, g.item_db)
        if choice == "continue":
            data = g.saves.load(1)
            if data:
                g.state.from_data(data)
            g.scenes.switch_to("overworld", load_existing=True)
        else:
            g.state.new_game()
            g.scenes.switch_to("overworld", load_existing=False)

    def draw(self, renderer) -> None:
        s = self.style
        bw, bh = renderer.base_size
        title = self.game.settings.get("game.title", "RPG")
        renderer.draw_text(title, bw // 2, bh // 3, s.title_font, s.highlight_color,
                           layer="ui", world=False, anchor="center")
        renderer.draw_text("a data-driven RPG engine demo", bw // 2, bh // 3 + 16,
                           s.font, s.text_color, layer="ui", world=False, anchor="center")
        self.menu.draw(renderer, bw // 2 - 28, bh // 2 + 8)
        renderer.draw_text("Arrows: move    Confirm: select", bw // 2, bh - 14,
                           s.font, s.disabled_color, layer="ui", world=False, anchor="center")
