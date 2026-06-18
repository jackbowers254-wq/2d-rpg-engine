"""
game.scenes.quest_log_scene
=========================
An overlay listing active and completed quests with their objectives and
progress, read live from the QuestManager. Opened with the ``quest_log`` action
or from the pause menu.
"""

from __future__ import annotations

from engine.core.scene import Scene
from engine.ui.panel import Panel
from engine.ui.text import wrap_text


class QuestLogScene(Scene):
    transparent = True
    blocks_update = True

    def on_enter(self, **kwargs) -> None:
        self.style = self.game.style

    def update(self, dt: float) -> None:
        inp = self.game.input
        if inp.just_pressed("quest_log") or inp.just_pressed("cancel") or inp.just_pressed("menu"):
            self.game.scenes.pop()

    def draw(self, renderer) -> None:
        s = self.style
        bw, bh = renderer.base_size
        renderer.draw_rect((0, 0, bw, bh), (0, 0, 0, 160), layer="ui", world=False)
        panel = Panel(10, 8, bw - 20, bh - 16, s)
        panel.draw(renderer)

        x, y = panel.inner_x, panel.inner_y
        renderer.draw_text("Quest Log", x, y, s.title_font, s.highlight_color,
                           layer="ui", world=False)
        y += s.title_font.get_height() + 2

        quests = self.game.quests
        state = self.game.state.quests
        active = [qid for qid, q in state.items() if q.get("state") == "active"]
        done = [qid for qid, q in state.items() if q.get("state") == "done"]

        if not active and not done:
            renderer.draw_text("No quests yet.", x, y, s.font, s.disabled_color,
                               layer="ui", world=False)

        for qid in active + done:
            qdef = quests.db.get(qid)
            if qdef is None:
                continue
            is_done = qid in done
            title = ("[Done] " if is_done else "") + qdef.name
            renderer.draw_text(title, x, y, s.font,
                               s.disabled_color if is_done else s.highlight_color,
                               layer="ui", world=False)
            y += s.line_height
            for line in wrap_text(s.font, qdef.description, int(panel.inner_width) - 6):
                renderer.draw_text(line, x + 4, y, s.font, s.text_color, layer="ui", world=False)
                y += s.line_height
            for text, complete in quests.objective_lines(qid):
                mark = "x" if complete else "-"
                color = s.disabled_color if complete else s.text_color
                renderer.draw_text(f"  [{mark}] {text}", x + 4, y, s.font, color,
                                   layer="ui", world=False)
                y += s.line_height
            y += 2

        renderer.draw_text("L / Esc: close", bw // 2, bh - 12, s.font, s.disabled_color,
                           layer="ui", world=False, anchor="center")
