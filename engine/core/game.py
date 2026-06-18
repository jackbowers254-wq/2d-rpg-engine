"""
engine.core.game
================
The :class:`Game` object owns the window, the fixed-timestep loop and every
engine *service*. Scenes reach all services through ``self.game``:

    game.settings   -> Settings        (config access)
    game.renderer   -> Renderer        (all drawing)
    game.input      -> InputManager     (remappable actions)
    game.assets     -> AssetManager     (cached loading + placeholders)
    game.events     -> EventBus         (decoupled pub/sub)
    game.scenes     -> SceneManager      (push/pop/switch states)
    game.state      -> (game-defined)    (shared cross-scene game state)

The loop is the classic *read input -> update -> draw* with a delta time clamped
to avoid the "spiral of death" if a frame hangs. ``max_fps`` (and everything
else) comes from config -- nothing here is hardcoded.

Bootstrapping a game is three lines (see ``main.py``):

    game = Game("config/config.json")
    register_scenes(game)          # game-specific
    game.run()
"""

from __future__ import annotations

import os
from typing import Any, Optional

import pygame

from engine.assets.asset_manager import AssetManager
from engine.audio.audio_manager import AudioManager
from engine.core.debug import DebugOverlay
from engine.core.events import EventBus
from engine.core.scene_manager import SceneManager
from engine.graphics.renderer import PygameRenderer
from engine.input.input_manager import InputManager
from engine.settings import Settings
from engine.utils.logger import configure_logging, get_logger

log = get_logger("game")


class Game:
    def __init__(self, config_path: str = "config/config.json",
                 overrides: "str | dict | None" = None) -> None:
        # 1) Config first -- everything else reads from it.
        self.settings = Settings.load(config_path, overrides)
        configure_logging(self.settings.get("debug.log_level", "info"))
        log.info("Booting '%s' v%s",
                 self.settings.get("game.title"), self.settings.get("game.version"))

        # 2) Initialise pygame subsystems.
        pygame.init()
        self._init_audio()

        # 3) Core services.
        self.events = EventBus()
        self.renderer = PygameRenderer(self.settings)
        self.input = InputManager(self.settings, self.renderer)
        self.assets = AssetManager(self.settings)
        self.audio = AudioManager(self.settings, self.assets)
        self.scenes = SceneManager(self)

        # Generic slot for the game's shared state (party, inventory, flags...).
        # The engine doesn't dictate its shape; the demo stores a GameState here.
        self.state: Any = None

        self.clock = pygame.time.Clock()
        self.running = False
        self._max_fps = self.settings.get("display.max_fps", 60)
        self._show_fps = self.settings.get("display.show_fps", False)
        self._fps_font = self.assets.get_font(self.settings.get("ui.font_size", 8))

        # Runtime debug overlay (toggle with the 'debug_toggle' action / F1).
        self.debug = DebugOverlay(self)

    # -- audio ---------------------------------------------------------------
    def _init_audio(self) -> None:
        if not self.settings.get("audio.enabled", True):
            return
        try:
            pygame.mixer.pre_init(
                frequency=self.settings.get("audio.frequency", 44100),
                buffer=self.settings.get("audio.buffer", 512),
            )
            pygame.mixer.init()
        except pygame.error as exc:
            log.warning("Audio unavailable (%s); continuing muted", exc)

    # -- loop ----------------------------------------------------------------
    def run(self) -> None:
        """Enter the main loop. Switches to the configured start scene first."""
        start = self.settings.get("game.start_scene", "title")
        self.scenes.switch_to(start)
        self.running = True
        while self.running:
            dt = self.clock.tick(self._max_fps) / 1000.0
            # Clamp dt so a hitch (debugger pause, slow frame) can't teleport
            # entities through walls or blow up physics.
            dt = min(dt, 0.05)
            self._process_events()
            if not self.running:
                break
            self.debug.update()
            self.audio.update(dt)
            self.scenes.update(dt)
            if self.scenes.is_empty:  # last scene popped itself -> exit
                self.running = False
                break
            self._render()
        self.shutdown()

    def _process_events(self) -> None:
        self.input.begin_frame()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.VIDEORESIZE:
                self.renderer.handle_resize((event.w, event.h))
            self.input.process_event(event)
            self.scenes.handle_event(event)

    def _render(self) -> None:
        self.renderer.begin_frame()
        self.scenes.draw(self.renderer)
        if self._show_fps and not self.debug.visible:
            fps = f"{self.clock.get_fps():4.0f} fps"
            self.renderer.draw_text(fps, 2, 1, self._fps_font, (180, 255, 180),
                                    layer="overlay", world=False)
        self.debug.draw(self.renderer)
        self.renderer.end_frame()

    # -- shutdown ------------------------------------------------------------
    def quit(self) -> None:
        """Request a clean exit from anywhere (e.g. a 'Quit' menu item)."""
        self.running = False

    def shutdown(self) -> None:
        log.info("Shutting down")
        pygame.quit()
