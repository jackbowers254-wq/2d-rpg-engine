"""
engine.assets.asset_manager
===========================
One place that loads and *caches* everything external: images, fonts, sounds and
JSON data. Subsystems ask the manager rather than touching the filesystem, so:

- assets are loaded once and reused (no duplicate decodes),
- a missing asset never crashes -- it returns a bright magenta "missing texture"
  placeholder and logs a warning, so the demo runs with NO art files at all,
- art can ship at multiple scales (``assets.scale_set``: "1x", "2x", ...). Bump
  the config value and the manager prefers the higher-fidelity folder, falling
  back to the base folder. This is how you raise art fidelity later without
  touching code.

Placeholder helpers (``solid_tile``, ``placeholder``) generate coloured squares
on the fly -- the demo's "art" is entirely generated this way.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional, Tuple

import pygame

from engine.utils.logger import get_logger

log = get_logger("assets")


class AssetManager:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.sprites_root = settings.get("assets.sprites", "assets/sprites")
        self.audio_root = settings.get("assets.audio", "assets/audio")
        self.fonts_root = settings.get("assets.fonts", "assets/fonts")
        self.scale_set = settings.get("assets.scale_set", "1x")
        self.missing_color = tuple(settings.get("assets.missing_texture_color", [255, 0, 220]))
        self.audio_enabled = settings.get("audio.enabled", True)

        # Caches.
        self._images: Dict[str, pygame.Surface] = {}
        self._fonts: Dict[Tuple[Optional[str], int], pygame.font.Font] = {}
        self._sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self._json: Dict[str, dict] = {}
        self._generated: Dict[Tuple, pygame.Surface] = {}

    # -- path resolution -----------------------------------------------------
    def _resolve_sprite(self, rel_path: str) -> Optional[str]:
        """Find a sprite, preferring the configured scale set folder."""
        candidates = [
            os.path.join(self.sprites_root, self.scale_set, rel_path),
            os.path.join(self.sprites_root, rel_path),
            rel_path,  # allow absolute / project-relative paths too
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        return None

    # -- images --------------------------------------------------------------
    def get_image(self, rel_path: str, *, convert_alpha: bool = True) -> pygame.Surface:
        """Load (and cache) an image. Returns a placeholder if not found."""
        if rel_path in self._images:
            return self._images[rel_path]

        path = self._resolve_sprite(rel_path)
        if path is None:
            log.warning("Missing image '%s' -> using placeholder", rel_path)
            surf = self.placeholder(self.settings.get("world.tile_size", 16),
                                    self.settings.get("world.tile_size", 16),
                                    self.missing_color)
        else:
            surf = pygame.image.load(path)
            surf = surf.convert_alpha() if convert_alpha else surf.convert()
        self._images[rel_path] = surf
        return surf

    def placeholder(self, w: int, h: int, color, border: Optional[Tuple] = None) -> pygame.Surface:
        """A solid coloured rectangle surface (cached). The engine's default art."""
        key = ("rect", w, h, tuple(color), border)
        if key in self._generated:
            return self._generated[key]
        surf = pygame.Surface((int(w), int(h)), pygame.SRCALPHA)
        surf.fill(tuple(color))
        if border:
            pygame.draw.rect(surf, tuple(border), surf.get_rect(), 1)
        self._generated[key] = surf
        return surf

    def solid_tile(self, color) -> pygame.Surface:
        """A placeholder sprite exactly one tile in size (in base-res pixels)."""
        ts = self.settings.get("world.tile_size", 16)
        return self.placeholder(ts, ts, color)

    # -- fonts ---------------------------------------------------------------
    def get_font(self, size: int, path: Optional[str] = None) -> pygame.font.Font:
        path = path if path is not None else self.settings.get("ui.font_path", None)
        key = (path, size)
        if key in self._fonts:
            return self._fonts[key]
        if path:
            full = path if os.path.isfile(path) else os.path.join(self.fonts_root, path)
            try:
                font = pygame.font.Font(full, size)
            except (FileNotFoundError, pygame.error):
                log.warning("Missing font '%s' -> using default", path)
                font = pygame.font.Font(None, size)
        else:
            font = pygame.font.Font(None, size)  # pygame's built-in default font
        self._fonts[key] = font
        return font

    # -- audio ---------------------------------------------------------------
    def get_sound(self, rel_path: str) -> Optional[pygame.mixer.Sound]:
        if not self.audio_enabled or not pygame.mixer.get_init():
            return None
        if rel_path in self._sounds:
            return self._sounds[rel_path]
        path = os.path.join(self.audio_root, rel_path)
        sound = None
        if os.path.isfile(path):
            try:
                sound = pygame.mixer.Sound(path)
                sound.set_volume(self.settings.get("audio.sfx_volume", 1.0))
            except pygame.error:
                log.warning("Failed to load sound '%s'", rel_path)
        else:
            log.debug("Sound '%s' not found (skipping)", rel_path)
        self._sounds[rel_path] = sound
        return sound

    def play_sound(self, rel_path: str) -> None:
        sound = self.get_sound(rel_path)
        if sound:
            sound.play()

    def play_music(self, rel_path: str, loop: bool = True) -> None:
        if not self.audio_enabled or not pygame.mixer.get_init():
            return
        path = os.path.join(self.audio_root, rel_path)
        if not os.path.isfile(path):
            log.debug("Music '%s' not found (skipping)", rel_path)
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.settings.get("audio.music_volume", 1.0))
            pygame.mixer.music.play(-1 if loop else 0)
        except pygame.error:
            log.warning("Failed to play music '%s'", rel_path)

    # -- data ----------------------------------------------------------------
    def load_json(self, path: str, *, cache: bool = True) -> dict:
        """Load a JSON data file (cached). Raises if the file is missing -- data
        is content, and a missing content file is a real authoring error."""
        if cache and path in self._json:
            return self._json[path]
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if cache:
            self._json[path] = data
        return data

    def clear(self) -> None:
        """Drop all caches (e.g. when switching to a higher scale set)."""
        self._images.clear()
        self._fonts.clear()
        self._sounds.clear()
        self._json.clear()
        self._generated.clear()
