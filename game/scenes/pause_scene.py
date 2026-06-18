"""
game.scenes.pause_scene
=====================
An OVERLAY menu. ``transparent`` keeps the overworld drawn beneath it and
``blocks_update`` freezes that world while paused -- exactly the behaviour the
stack-based SceneManager is built for. Offers Resume / Items / Save / Load /
Title. (The overworld syncs the live player into GameState in ``on_pause`` so a
Save here captures the current position.)
"""

from __future__ import annotations

from engine.core.scene import Scene
from engine.ui.menu import Menu, MenuItem
from engine.ui.panel import Panel


class PauseScene(Scene):
    transparent = True     # draw the overworld underneath
    blocks_update = True    # but freeze it

    def on_enter(self, **kwargs) -> None:
        g = self.game
        self.style = g.style
        self._toast = ""
        has_save = any(meta for _, meta in g.saves.list_slots())
        self.menu = Menu([
            MenuItem("Resume", "resume"),
            MenuItem("Items", "items"),
            MenuItem("Quests", "quests"),
            MenuItem("Options", "options"),
            MenuItem("Save", "save"),
            MenuItem("Load", "load", enabled=has_save),
            MenuItem("Quit to Title", "title"),
        ], self.style, title="Paused")

    def on_resume(self) -> None:
        # Returning from the inventory overlay: refresh save availability.
        pass

    def update(self, dt: float) -> None:
        inp = self.game.input
        if inp.just_pressed("up"):
            self.menu.move(-1)
        if inp.just_pressed("down"):
            self.menu.move(1)
        if inp.just_pressed("menu") or inp.just_pressed("cancel"):
            self.game.scenes.pop()
            return
        if inp.just_pressed("confirm") or inp.just_pressed("interact"):
            self._activate(self.menu.selected.value)

    def _activate(self, choice: str) -> None:
        g = self.game
        if choice == "resume":
            g.scenes.pop()
        elif choice == "items":
            g.scenes.push("inventory")
        elif choice == "quests":
            g.scenes.push("quest_log")
        elif choice == "options":
            g.scenes.push("options")
        elif choice == "save":
            g.saves.save(1, g.state.to_data(), g.state.save_meta())
            self._toast = "Game saved."
            self.menu.items[3].enabled = True  # Load now available
        elif choice == "load":
            data = g.saves.load(1)
            if data:
                g.state.from_data(data)
                g.scenes.switch_to("overworld", load_existing=True)
        elif choice == "title":
            g.scenes.switch_to("title")

    def draw(self, renderer) -> None:
        s = self.style
        bw, bh = renderer.base_size
        # Dim the world behind the menu (translucent black).
        renderer.draw_rect((0, 0, bw, bh), (0, 0, 0, 150), layer="ui", world=False)
        panel = Panel(bw // 2 - 50, bh // 2 - 48, 100, 96, s)
        panel.draw(renderer)
        self.menu.draw(renderer, panel.inner_x, panel.inner_y)
        if self._toast:
            renderer.draw_text(self._toast, bw // 2, bh - 12, s.font, s.highlight_color,
                               layer="ui", world=False, anchor="center")
