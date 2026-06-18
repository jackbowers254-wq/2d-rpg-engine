"""
engine.core.scene
=================
Base class for every game *scene* / *state* (title screen, overworld, battle,
menu, dialogue, ...).

A Scene is the unit the :class:`~engine.core.scene_manager.SceneManager` pushes
and pops on a stack. Each scene implements four lifecycle/loop hooks:

- ``on_enter`` / ``on_exit`` : set-up & tear-down when (de)activated.
- ``handle_event``           : react to a single pygame event.
- ``update(dt)``             : advance simulation by ``dt`` seconds.
- ``draw(renderer)``         : enqueue draw calls (never blits directly).

OVERLAYS
--------
Set ``transparent = True`` to make a scene an *overlay* (e.g. a pause menu or a
dialogue box drawn on top of the overworld). The manager will keep drawing the
scene beneath it. Set ``blocks_update = True`` to freeze the scene below while
the overlay is active (typical for a pause menu); leave it False to let the
world keep simulating underneath (e.g. an ambient HUD).

Scenes receive the :class:`~engine.core.game.Game` instance as ``self.game`` and
reach every engine service through it (renderer, input, assets, audio, events,
scene manager, settings, save manager, game state).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid an import cycle; only needed for type checkers
    import pygame

    from engine.core.game import Game
    from engine.graphics.renderer import Renderer


class Scene:
    #: If True the scene below this one is still drawn (overlay scenes).
    transparent: bool = False
    #: If True the scene below this one is NOT updated while this one is on top.
    blocks_update: bool = True

    def __init__(self, game: "Game") -> None:
        self.game = game

    # -- lifecycle -----------------------------------------------------------
    def on_enter(self, **kwargs) -> None:
        """Called when this scene becomes (or returns to being) the active one.

        ``kwargs`` are forwarded from ``SceneManager.switch_to/push`` so scenes
        can be parameterised (e.g. which enemy to fight, which dialogue to run).
        """

    def on_exit(self) -> None:
        """Called when this scene is removed from the stack."""

    def on_pause(self) -> None:
        """Called when another scene is pushed on top of this one."""

    def on_resume(self) -> None:
        """Called when the scene above this one is popped and we are top again."""

    # -- per-frame hooks -----------------------------------------------------
    def handle_event(self, event: "pygame.event.Event") -> None:
        """Handle a single discrete pygame event (key down, quit, resize...)."""

    def update(self, dt: float) -> None:
        """Advance the scene by ``dt`` seconds (continuous logic)."""

    def draw(self, renderer: "Renderer") -> None:
        """Enqueue draw calls on the renderer. Do not present here."""
