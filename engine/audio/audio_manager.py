"""
engine.audio.audio_manager
========================
Background music with crossfade, layered sound effects, and live volumes.

Music can't truly crossfade through ``pygame.mixer.music`` (one stream), so this
manager plays music as ``Sound`` objects on two reserved channels and ramps their
volumes in :meth:`update` -- fading the new track up while the old fades out.
Sound effects play on the remaining channels (auto-allocated, so they layer).

Volumes are three multiplied gains -- ``master`` x (``music`` | ``sfx``) -- all
adjustable at runtime (e.g. from an options menu) via :meth:`set_volume`. If no
audio device is available (headless/CI) the whole manager no-ops safely.

Call :meth:`update` once per frame (the Game does this) to advance fades.
"""

from __future__ import annotations

from typing import List, Optional

import pygame

from engine.utils.logger import get_logger

log = get_logger("audio")


class AudioManager:
    def __init__(self, settings, assets) -> None:
        self.settings = settings
        self.assets = assets
        self.master = settings.get("audio.master_volume", 0.8)
        self.music_vol = settings.get("audio.music_volume", 0.6)
        self.sfx_vol = settings.get("audio.sfx_volume", 0.8)
        self.crossfade = settings.get("audio.crossfade_ms", 700) / 1000.0

        self.enabled = settings.get("audio.enabled", True) and bool(pygame.mixer.get_init())
        self._music_channels: List[pygame.mixer.Channel] = []
        self._cur = 0
        self._track: Optional[str] = None
        # active fades: [channel, from_vol, to_vol, elapsed, duration, stop_after]
        self._fades: List[list] = []

        if self.enabled:
            try:
                pygame.mixer.set_reserved(2)  # keep channels 0,1 for music
                self._music_channels = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
            except pygame.error:
                self.enabled = False

    # -- music ---------------------------------------------------------------
    def play_music(self, track: str, loop: bool = True,
                   crossfade: Optional[float] = None) -> None:
        if not self.enabled or track == self._track:
            return
        sound = self.assets.get_sound(track)
        if sound is None:
            self._track = track  # remember intent even if the file is missing
            return
        cf = self.crossfade if crossfade is None else crossfade
        target = self.master * self.music_vol
        new_ch = self._music_channels[1 - self._cur]
        old_ch = self._music_channels[self._cur]

        new_ch.play(sound, loops=-1 if loop else 0)
        new_ch.set_volume(0.0)
        # Drop any in-flight fades on these channels, then schedule the crossfade.
        self._fades = [f for f in self._fades if f[0] not in (new_ch, old_ch)]
        self._fades.append([new_ch, 0.0, target, 0.0, max(0.01, cf), False])
        if old_ch.get_busy():
            self._fades.append([old_ch, old_ch.get_volume(), 0.0, 0.0, max(0.01, cf), True])

        self._cur = 1 - self._cur
        self._track = track

    def stop_music(self, fade: float = 0.5) -> None:
        if not self.enabled:
            return
        ch = self._music_channels[self._cur]
        if ch.get_busy():
            self._fades.append([ch, ch.get_volume(), 0.0, 0.0, max(0.01, fade), True])
        self._track = None

    # -- sfx -----------------------------------------------------------------
    def play_sound(self, name: str, volume: float = 1.0) -> None:
        if not self.enabled:
            return
        sound = self.assets.get_sound(name)
        if sound is not None:
            sound.set_volume(self.master * self.sfx_vol * volume)
            sound.play()  # auto-allocates a non-reserved channel -> SFX layer

    # -- volumes -------------------------------------------------------------
    def set_volume(self, kind: str, value: float) -> None:
        value = max(0.0, min(1.0, value))
        if kind == "master":
            self.master = value
        elif kind == "music":
            self.music_vol = value
        elif kind == "sfx":
            self.sfx_vol = value
        self.settings.set(f"audio.{kind}_volume" if kind != "master" else "audio.master_volume", value)
        # Apply immediately to the currently-playing music channel.
        if self.enabled and self._music_channels:
            ch = self._music_channels[self._cur]
            if ch.get_busy() and not any(f[0] is ch for f in self._fades):
                ch.set_volume(self.master * self.music_vol)

    def get_volume(self, kind: str) -> float:
        return {"master": self.master, "music": self.music_vol, "sfx": self.sfx_vol}.get(kind, 0.0)

    # -- frame ---------------------------------------------------------------
    def update(self, dt: float) -> None:
        if not self._fades:
            return
        for f in list(self._fades):
            ch, v0, v1, elapsed, dur, stop = f
            elapsed += dt
            f[3] = elapsed
            frac = min(1.0, elapsed / dur)
            ch.set_volume(v0 + (v1 - v0) * frac)
            if frac >= 1.0:
                if stop:
                    ch.stop()
                self._fades.remove(f)
