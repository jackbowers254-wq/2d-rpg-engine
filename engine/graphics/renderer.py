"""
engine.graphics.renderer
========================
The renderer is the single choke-point through which *everything* visible is
drawn. The rest of the engine talks to the abstract :class:`Renderer` interface
and never touches pygame's display directly. That indirection buys three things
the brief explicitly asks for:

1. RESOLUTION INDEPENDENCE
   All drawing happens onto a fixed-size *base surface* (``display.base_resolution``,
   e.g. 320x180 logical pixels). Once per frame that base surface is scaled to
   fit the actual window (any size, windowed or fullscreen, any aspect ratio via
   letter/pillar-boxing, optional crisp integer scaling). Game code, the camera
   and the UI all work in logical pixels and never care about the window size.
   Raise ``base_resolution`` (or the window) and nothing else changes.

2. A LAYERED, CONFIGURABLE DRAW ORDER
   Draw calls are queued against named layers (``render.layers`` in config:
   background -> ground -> ... -> entities -> ... -> ui -> overlay). Layers flush
   in config order; "y-sort" layers (``render.y_sort_layers``) additionally sort
   their sprites by world Y so characters lower on screen overlap those behind
   them. Add a layer = edit config; no code change.

3. EXTENSION HOOKS FOR ADVANCED GRAPHICS
   Post-processing / effect objects (see ``engine.graphics.effects``) can be
   registered and are invoked at clearly marked points each frame -- the seam
   where you would later bolt on dynamic lighting, particles, shaders or
   screen-space post-processing WITHOUT touching any of the code above.

To support a totally different backend (e.g. moderngl/OpenGL, or a web canvas),
implement the :class:`Renderer` interface and swap it in ``Game``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Sequence, Tuple

import pygame

from engine.utils.logger import get_logger

if TYPE_CHECKING:
    from engine.graphics.camera import Camera
    from engine.graphics.effects import RenderEffect
    from engine.settings import Settings

log = get_logger("renderer")

Color = Tuple[int, int, int]
ColorA = Sequence[int]


@dataclass
class _DrawCmd:
    """One queued primitive. We queue rather than blit immediately so layers can
    be flushed in order and y-sorted. Screen coordinates are pre-computed at
    enqueue time using the active camera."""

    execute: Callable[[pygame.Surface], None]
    sort_y: float = 0.0  # used only within y-sorted layers


class Renderer(ABC):
    """Abstract drawing interface used by all scenes, systems and UI.

    Coordinate spaces
    -----------------
    - **World space**: logical pixels in the map. Pass ``world=True`` (default
      for sprites/tiles) and the active camera offset is applied.
    - **Screen space**: logical pixels on the base surface, origin top-left. Use
      ``world=False`` for UI/HUD that should not scroll with the camera.
    """

    # The current camera, set by the scene each frame before world draws.
    camera: "Optional[Camera]" = None

    # -- per-frame boundaries -----------------------------------------------
    @abstractmethod
    def begin_frame(self) -> None: ...

    @abstractmethod
    def end_frame(self) -> None: ...

    # -- queue primitives ----------------------------------------------------
    @abstractmethod
    def draw_image(self, image: pygame.Surface, x: float, y: float, *,
                   layer: Optional[str] = None, world: bool = True,
                   sort_y: Optional[float] = None) -> None: ...

    @abstractmethod
    def draw_rect(self, rect: Sequence[float], color: ColorA, *,
                  layer: Optional[str] = None, world: bool = True,
                  width: int = 0, sort_y: Optional[float] = None) -> None: ...

    @abstractmethod
    def draw_line(self, start: Sequence[float], end: Sequence[float], color: ColorA, *,
                  layer: Optional[str] = None, world: bool = True, width: int = 1) -> None: ...

    @abstractmethod
    def draw_text(self, text: str, x: float, y: float, font: pygame.font.Font, color: ColorA, *,
                  layer: Optional[str] = None, world: bool = False,
                  anchor: str = "topleft") -> None: ...

    # -- effect hooks --------------------------------------------------------
    @abstractmethod
    def add_effect(self, effect: "RenderEffect") -> None: ...

    # -- geometry helpers ----------------------------------------------------
    @property
    @abstractmethod
    def base_size(self) -> Tuple[int, int]: ...

    @abstractmethod
    def window_to_base(self, pos: Sequence[float]) -> Tuple[float, float]: ...


class PygameRenderer(Renderer):
    """The default software renderer: draws onto a base surface, then scales it
    to the window. Simple on purpose -- the seams (layers + effects) are where
    fidelity gets added later."""

    def __init__(self, settings: "Settings") -> None:
        self.settings = settings
        d = settings

        self._base_w, self._base_h = d.get("display.base_resolution", [320, 180])
        self._clear_color: Color = tuple(d.get("display.clear_color", [0, 0, 0]))
        self._letterbox_color: Color = tuple(d.get("display.letterbox_color", [0, 0, 0]))

        # Scaling mode resolves from the modern key, falling back to the Gen 1
        # boolean keys so existing configs keep working unchanged:
        #   "integer" -> nearest-neighbour, whole-number scale (pixel perfect)
        #   "fit"     -> nearest-neighbour, fractional scale, keep aspect (letterbox)
        #   "stretch" -> fill the window, ignore aspect ratio
        self._pixel_perfect: bool = d.get("display.pixel_perfect", False)
        self._scaling_mode: str = self._resolve_scaling_mode(d)
        self._maintain_aspect: bool = self._scaling_mode != "stretch"
        self._integer_scaling: bool = self._scaling_mode == "integer"
        # Smooth (linear) scaling is incompatible with pixel-perfect output.
        self._smooth: bool = d.get("display.smooth_scaling", False) and not self._pixel_perfect

        # Window flags from config.
        flags = 0
        if d.get("display.resizable", True):
            flags |= pygame.RESIZABLE
        self._fullscreen = d.get("display.fullscreen", False)
        if self._fullscreen:
            flags |= pygame.FULLSCREEN
        win_size = tuple(d.get("display.window_size", [self._base_w, self._base_h]))
        vsync = 1 if d.get("display.vsync", True) else 0
        try:
            self.window = pygame.display.set_mode(win_size, flags, vsync=vsync)
        except pygame.error:
            # vsync can be unsupported on some drivers/headless; retry without it.
            self.window = pygame.display.set_mode(win_size, flags)
        pygame.display.set_caption(d.get("game.title", "Game"))

        # The fixed logical canvas everything is drawn onto.
        self.base = pygame.Surface((self._base_w, self._base_h)).convert()

        # Layered draw queue: name -> list of commands, plus config-driven order.
        self._layer_order: List[str] = list(d.get("render.layers", ["entities"]))
        self._y_sort: set = set(d.get("render.y_sort_layers", []))
        self._default_layer: str = d.get("render.default_entity_layer", self._layer_order[-1])
        self._queues: Dict[str, List[_DrawCmd]] = {name: [] for name in self._layer_order}

        # Registered post/while-rendering effects (extension hook).
        self._effects: List["RenderEffect"] = []

        # Cached scaling geometry (recomputed on resize).
        self._dest_rect = pygame.Rect(0, 0, *win_size)
        self._recompute_scale(win_size)

    @staticmethod
    def _resolve_scaling_mode(d) -> str:
        """Pick a scaling mode, honouring the modern key then the Gen 1 booleans."""
        mode = d.get("display.scaling_mode")
        if mode in ("integer", "fit", "stretch"):
            return mode
        if d.get("display.pixel_perfect", False):
            return "integer"
        if not d.get("display.maintain_aspect_ratio", True):
            return "stretch"
        return "integer" if d.get("display.integer_scaling", False) else "fit"

    # -- window / scaling ----------------------------------------------------
    def handle_resize(self, size: Sequence[int]) -> None:
        """Re-create the window surface after a user resize and recompute scale."""
        flags = self.window.get_flags()
        self.window = pygame.display.set_mode(tuple(size), flags)
        self._recompute_scale(size)

    def toggle_fullscreen(self) -> None:
        """Extension-friendly fullscreen toggle (bind to a key if you like)."""
        self._fullscreen = not self._fullscreen
        pygame.display.toggle_fullscreen()
        self._recompute_scale(self.window.get_size())

    def _recompute_scale(self, win_size: Sequence[int]) -> None:
        ww, wh = win_size
        bw, bh = self._base_w, self._base_h
        if self._maintain_aspect:
            scale = min(ww / bw, wh / bh)
            if self._integer_scaling and scale >= 1:
                scale = max(1, int(scale))
            dw, dh = int(bw * scale), int(bh * scale)
        else:
            dw, dh = ww, wh  # stretch to fill, ignoring aspect ratio
        self._dest_rect = pygame.Rect((ww - dw) // 2, (wh - dh) // 2, dw, dh)

    @property
    def base_size(self) -> Tuple[int, int]:
        return (self._base_w, self._base_h)

    def window_to_base(self, pos: Sequence[float]) -> Tuple[float, float]:
        """Map a window-space point (e.g. mouse) into base-surface coordinates,
        accounting for letterboxing and scale. Returns logical pixels."""
        x, y = pos
        if self._dest_rect.width == 0 or self._dest_rect.height == 0:
            return (0.0, 0.0)
        bx = (x - self._dest_rect.x) * self._base_w / self._dest_rect.width
        by = (y - self._dest_rect.y) * self._base_h / self._dest_rect.height
        return (bx, by)

    # -- camera offset helper ------------------------------------------------
    def _offset(self, world: bool) -> Tuple[float, float]:
        if world and self.camera is not None:
            return self.camera.offset
        return (0.0, 0.0)

    def _layer(self, name: Optional[str]) -> List[_DrawCmd]:
        name = name or self._default_layer
        q = self._queues.get(name)
        if q is None:  # unknown layer -> create lazily and warn once
            log.warning("Unknown draw layer '%s'; appending to order", name)
            self._layer_order.append(name)
            if name not in self._y_sort:
                pass
            q = self._queues[name] = []
        return q

    # -- frame boundaries ----------------------------------------------------
    def begin_frame(self) -> None:
        self.base.fill(self._clear_color)
        for q in self._queues.values():
            q.clear()

    def end_frame(self) -> None:
        # 1) Flush layered draw queue in configured order.
        for name in self._layer_order:
            q = self._queues.get(name)
            if not q:
                continue
            if name in self._y_sort:
                q.sort(key=lambda c: c.sort_y)
            for cmd in q:
                cmd.execute(self.base)
            # EXTENSION HOOK: per-layer effects (e.g. lighting applied above
            # the world but below the UI) run here.
            for effect in self._effects:
                effect.after_layer(name, self.base, self)

        # 2) EXTENSION HOOK: full-frame post-processing (bloom, color grading,
        #    CRT/scanline shaders, screen shake offset, ...). Effects mutate the
        #    base surface in place before it is scaled to the window.
        for effect in self._effects:
            effect.post_process(self.base, self)

        # 3) Scale the logical canvas to the window (resolution independence).
        self.window.fill(self._letterbox_color)
        scaler = pygame.transform.smoothscale if self._smooth else pygame.transform.scale
        scaled = scaler(self.base, self._dest_rect.size)
        self.window.blit(scaled, self._dest_rect.topleft)
        pygame.display.flip()

    # -- primitive queue methods --------------------------------------------
    def draw_image(self, image, x, y, *, layer=None, world=True, sort_y=None):
        ox, oy = self._offset(world)
        sx, sy = x - ox, y - oy
        s = (y + image.get_height()) if sort_y is None else sort_y
        self._layer(layer).append(_DrawCmd(lambda surf: surf.blit(image, (round(sx), round(sy))), s))

    def draw_rect(self, rect, color, *, layer=None, world=True, width=0, sort_y=None):
        ox, oy = self._offset(world)
        rx, ry, rw, rh = rect
        screen_rect = pygame.Rect(round(rx - ox), round(ry - oy), round(rw), round(rh))
        s = (ry + rh) if sort_y is None else sort_y
        if len(color) == 4 and color[3] < 255 and width == 0:
            # Translucent fill (e.g. dimming the screen behind a menu). pygame's
            # draw.rect ignores alpha, so blit a per-pixel-alpha surface instead.
            fill = pygame.Surface((screen_rect.width, screen_rect.height), pygame.SRCALPHA)
            fill.fill(tuple(color))
            self._layer(layer).append(
                _DrawCmd(lambda surf: surf.blit(fill, screen_rect.topleft), s))
        else:
            rgb = tuple(color[:3])
            self._layer(layer).append(
                _DrawCmd(lambda surf: pygame.draw.rect(surf, rgb, screen_rect, width), s))

    def draw_line(self, start, end, color, *, layer=None, world=True, width=1):
        ox, oy = self._offset(world)
        a = (round(start[0] - ox), round(start[1] - oy))
        b = (round(end[0] - ox), round(end[1] - oy))
        self._layer(layer).append(_DrawCmd(lambda surf: pygame.draw.line(surf, color, a, b, width)))

    def draw_text(self, text, x, y, font, color, *, layer="ui", world=False, anchor="topleft"):
        surf = font.render(str(text), False, tuple(color))
        ox, oy = self._offset(world)
        rect = surf.get_rect()
        setattr(rect, anchor, (round(x - ox), round(y - oy)))
        self._layer(layer).append(_DrawCmd(lambda dest: dest.blit(surf, rect.topleft)))

    # -- effects -------------------------------------------------------------
    def add_effect(self, effect: "RenderEffect") -> None:
        """Register a post-processing / lighting / particle effect (extension)."""
        self._effects.append(effect)
        log.info("Registered render effect: %s", type(effect).__name__)

    def update_effects(self, dt: float) -> None:
        """Advance time-based effects (particles, day/night). Called per frame."""
        for effect in self._effects:
            effect.update(dt)
