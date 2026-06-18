"""
engine.core.scene_manager
==========================
A stack-based scene/state manager.

WHY A STACK (not just a single current state)?
----------------------------------------------
Overlays. A pause menu or dialogue box needs to sit *on top of* the overworld
while the overworld stays visible (and optionally frozen) beneath it. A stack
models this naturally:

    [overworld]                      -> playing
    [overworld, pause_menu]          -> paused, world still drawn underneath
    [overworld, dialogue]            -> talking, world drawn but not updated
    [title]                          -> switch_to() replaced the whole stack

Registration is data-friendly: scenes are registered by name (a string) against
a factory, so new scenes are added without touching the manager. The first
scene to run is chosen by ``game.start_scene`` in config.

Update / draw rules
-------------------
- ``update`` runs top-down and stops at the first scene whose successor set
  ``blocks_update = True`` (so a pause menu freezes the world; a HUD doesn't).
- ``draw`` runs bottom-up but only includes scenes from the lowest *opaque*
  scene upward (so we never waste time drawing fully-hidden scenes).
"""

from __future__ import annotations

from typing import Callable, Dict, List, TYPE_CHECKING

from engine.core.scene import Scene
from engine.utils.logger import get_logger

if TYPE_CHECKING:
    import pygame

    from engine.core.game import Game
    from engine.graphics.renderer import Renderer

log = get_logger("scenes")

SceneFactory = Callable[["Game"], Scene]


class SceneManager:
    def __init__(self, game: "Game") -> None:
        self.game = game
        self._factories: Dict[str, SceneFactory] = {}
        self._stack: List[Scene] = []

    # -- registration --------------------------------------------------------
    def register(self, name: str, factory: SceneFactory) -> None:
        """Register a scene factory under ``name``.

        ``factory`` is any callable taking the Game and returning a Scene -- a
        class works directly (``register("title", TitleScene))``.
        """
        self._factories[name] = factory
        log.debug("Registered scene '%s'", name)

    def _create(self, name: str) -> Scene:
        if name not in self._factories:
            raise KeyError(
                f"No scene registered as '{name}'. "
                f"Registered: {sorted(self._factories)}"
            )
        return self._factories[name](self.game)

    # -- stack operations ----------------------------------------------------
    def switch_to(self, name: str, **kwargs) -> None:
        """Replace the entire stack with a single fresh scene."""
        while self._stack:
            self._stack.pop().on_exit()
        scene = self._create(name)
        self._stack.append(scene)
        scene.on_enter(**kwargs)
        log.info("Switched to scene '%s'", name)

    def push(self, name: str, **kwargs) -> None:
        """Push a scene on top (e.g. open a menu/dialogue overlay)."""
        if self._stack:
            self._stack[-1].on_pause()
        scene = self._create(name)
        self._stack.append(scene)
        scene.on_enter(**kwargs)
        log.debug("Pushed scene '%s' (depth=%d)", name, len(self._stack))

    def pop(self) -> None:
        """Pop the top scene and resume the one beneath it."""
        if not self._stack:
            return
        self._stack.pop().on_exit()
        if self._stack:
            self._stack[-1].on_resume()
        log.debug("Popped scene (depth=%d)", len(self._stack))

    def replace_top(self, name: str, **kwargs) -> None:
        """Swap just the top scene (e.g. battle -> results)."""
        if self._stack:
            self._stack.pop().on_exit()
        self.push(name, **kwargs)

    # -- queries -------------------------------------------------------------
    @property
    def current(self) -> "Scene | None":
        return self._stack[-1] if self._stack else None

    @property
    def is_empty(self) -> bool:
        return not self._stack

    # -- frame dispatch ------------------------------------------------------
    def handle_event(self, event: "pygame.event.Event") -> None:
        """Only the top scene receives discrete input events."""
        if self._stack:
            self._stack[-1].handle_event(event)

    def update(self, dt: float) -> None:
        # Determine how deep updates may go. Walk down from the top; a scene
        # blocks everything below it if it declares blocks_update.
        start = len(self._stack) - 1
        while start > 0 and not self._stack[start].blocks_update:
            start -= 1
        for scene in self._stack[start:]:
            scene.update(dt)

    def draw(self, renderer: "Renderer") -> None:
        # Find the lowest scene we actually need to draw: the topmost opaque
        # scene (everything below it is fully hidden).
        start = len(self._stack) - 1
        while start > 0 and self._stack[start].transparent:
            start -= 1
        for scene in self._stack[start:]:
            scene.draw(renderer)
