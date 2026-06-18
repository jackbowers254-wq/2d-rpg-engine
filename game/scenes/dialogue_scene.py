"""
game.scenes.dialogue_scene
========================
An overlay that runs one conversation. It wires the data-driven DialogueSystem
to the DialogueBox widget and a DialogueContext (so dialogue can read/write story
flags, grant items, and fire events). Pops itself when the conversation ends.
"""

from __future__ import annotations

import os

from engine.core.scene import Scene
from engine.dialogue.dialogue_system import DialogueContext, DialogueSystem
from engine.ui.dialogue_box import DialogueBox


class DialogueScene(Scene):
    transparent = True
    blocks_update = True

    def on_enter(self, dialogue: str = "", **kwargs) -> None:
        g = self.game
        path = os.path.join(g.settings.get("dialogue.dialogue_path", "data/dialogue"),
                            f"{dialogue}.json")
        data = g.assets.load_json(path, cache=False)
        data = {k: v for k, v in data.items() if not k.startswith("_")}

        context = DialogueContext(flags=g.state.flags,
                                  inventory=g.state.inventory,
                                  events=g.events)
        self.system = DialogueSystem(data, context)
        self.system.start()
        self.box = DialogueBox(self.system, g.style)

    def update(self, dt: float) -> None:
        inp = self.game.input
        self.box.update(dt)
        if inp.just_pressed("up"):
            self.box.move_choice(-1)
        if inp.just_pressed("down"):
            self.box.move_choice(1)
        if inp.just_pressed("interact") or inp.just_pressed("confirm"):
            self.box.confirm()
        if inp.just_pressed("cancel") and not (self.system.current and self.system.current.choices):
            self.box.confirm()
        if self.system.finished:
            self.game.scenes.pop()

    def draw(self, renderer) -> None:
        self.box.draw(renderer)
