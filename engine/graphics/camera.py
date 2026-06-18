"""
engine.graphics.camera
======================
A 2D camera that converts world space to the renderer's base-surface space.

It works entirely in logical (base-resolution) pixels, so it is automatically
resolution-independent: the renderer scales the whole base surface to the window
afterwards. The camera:

- follows a target (usually the player) with optional smoothing (``camera.smoothing``),
- clamps to the current map's bounds so you never see past the edges
  (``camera.clamp_to_map``) -- unless the map is smaller than the view, in which
  case it is centred,
- exposes ``offset`` (the top-left world coordinate of the view) which the
  renderer subtracts from world draws.

A ``deadzone`` (config ``camera.deadzone``) lets the target move within a central
box before the camera reacts -- handy to reduce jitter.
"""

from __future__ import annotations

from typing import Optional, Tuple

from engine.utils.geometry import clamp, lerp


class Camera:
    def __init__(self, view_w: int, view_h: int, settings) -> None:
        self.view_w = view_w
        self.view_h = view_h
        # Top-left of the camera in world coordinates.
        self.x = 0.0
        self.y = 0.0
        # World bounds (set per-map). None => unbounded.
        self.bounds: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)

        self.follow = settings.get("camera.follow", True)
        self.smoothing = settings.get("camera.smoothing", 0.0)
        self.clamp = settings.get("camera.clamp_to_map", True)
        dz = settings.get("camera.deadzone", [0, 0])
        self.deadzone = (dz[0], dz[1])
        # Pixel-snap renders the camera at whole-pixel offsets so scrolling pixel
        # art doesn't shimmer/jitter. The internal x/y stay float (so smoothing
        # accumulates correctly); only the *render offset* is rounded.
        self.pixel_snap = settings.get("camera.pixel_snap", True)

    # -- configuration -------------------------------------------------------
    def set_bounds(self, x: int, y: int, w: int, h: int) -> None:
        """Constrain the camera to a world rectangle (typically the map size)."""
        self.bounds = (x, y, w, h)

    def set_view_size(self, w: int, h: int) -> None:
        self.view_w, self.view_h = w, h

    @property
    def offset(self) -> Tuple[float, float]:
        """The value the renderer subtracts from world positions.

        When ``pixel_snap`` is on this is rounded to whole pixels so the world
        grid stays aligned to the screen grid (no shimmer). World/UI logic still
        uses the float position via ``center`` etc.
        """
        if self.pixel_snap:
            return (round(self.x), round(self.y))
        return (self.x, self.y)

    @property
    def center(self) -> Tuple[float, float]:
        return (self.x + self.view_w / 2.0, self.y + self.view_h / 2.0)

    # -- update --------------------------------------------------------------
    def snap_to(self, world_x: float, world_y: float) -> None:
        """Instantly centre the camera on a world point (no smoothing)."""
        self.x = world_x - self.view_w / 2.0
        self.y = world_y - self.view_h / 2.0
        self._clamp()

    def update(self, target_x: float, target_y: float, dt: float) -> None:
        """Move toward centring on ``(target_x, target_y)`` this frame."""
        if not self.follow:
            self._clamp()
            return

        desired_x = target_x - self.view_w / 2.0
        desired_y = target_y - self.view_h / 2.0

        # Deadzone: only chase once the target leaves a central box.
        dzx, dzy = self.deadzone
        if dzx > 0 and abs(desired_x - self.x) < dzx:
            desired_x = self.x
        if dzy > 0 and abs(desired_y - self.y) < dzy:
            desired_y = self.y

        if self.smoothing and self.smoothing > 0:
            # Frame-rate independent smoothing factor.
            t = 1.0 - pow(1.0 - clamp(self.smoothing, 0.0, 1.0), dt * 60.0)
            self.x = lerp(self.x, desired_x, t)
            self.y = lerp(self.y, desired_y, t)
        else:
            self.x, self.y = desired_x, desired_y

        self._clamp()

    def _clamp(self) -> None:
        if not (self.clamp and self.bounds):
            return
        bx, by, bw, bh = self.bounds
        # If the map is smaller than the view, centre it; else clamp to edges.
        if bw <= self.view_w:
            self.x = bx - (self.view_w - bw) / 2.0
        else:
            self.x = clamp(self.x, bx, bx + bw - self.view_w)
        if bh <= self.view_h:
            self.y = by - (self.view_h - bh) / 2.0
        else:
            self.y = clamp(self.y, by, by + bh - self.view_h)

    # -- coordinate conversion ----------------------------------------------
    def world_to_screen(self, wx: float, wy: float) -> Tuple[float, float]:
        return (wx - self.x, wy - self.y)

    def screen_to_world(self, sx: float, sy: float) -> Tuple[float, float]:
        return (sx + self.x, sy + self.y)
