"""
engine.input.input_manager
==========================
Abstracted, remappable input.

Game code never checks raw keys (``pygame.K_w``). Instead it asks about *actions*
("move_up", "interact", "menu", ...). The mapping from physical keys to actions
lives entirely in config (``input.bindings``), so the player -- or you, designing
a new game -- can rebind everything without code changes. Multiple keys may map
to one action (e.g. WASD *and* arrows), and one key may trigger several actions.

Three query styles cover every need:
- ``is_down(action)``       : held this frame (continuous, e.g. walking).
- ``just_pressed(action)``  : went down this frame (discrete, e.g. confirm).
- ``just_released(action)`` : went up this frame.

Held state comes from ``pygame.key.get_pressed`` (robust against lost focus);
edges come from the KEYDOWN/KEYUP events fed in each frame. The manager also
tracks the mouse in *base-surface* coordinates via the renderer so UI hit-testing
is resolution-independent.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import pygame

from engine.utils.logger import get_logger

log = get_logger("input")


class InputManager:
    def __init__(self, settings, renderer=None) -> None:
        self.settings = settings
        self.renderer = renderer  # used to translate mouse into base coords

        # action -> set of pygame key codes
        self.bindings: Dict[str, Set[int]] = {}
        self._load_bindings(settings.get("input.bindings", {}))

        # Per-frame edge sets (key codes).
        self._pressed: Set[int] = set()
        self._released: Set[int] = set()

        # Mouse state (in base-surface logical pixels).
        self.mouse_pos: Tuple[float, float] = (0.0, 0.0)
        self._mouse_pressed: Set[int] = set()
        self._mouse_released: Set[int] = set()

    # -- binding management --------------------------------------------------
    def _load_bindings(self, raw: Dict[str, List[str]]) -> None:
        self.bindings.clear()
        for action, names in raw.items():
            codes: Set[int] = set()
            for name in names:
                try:
                    codes.add(pygame.key.key_code(name))
                except (ValueError, pygame.error):
                    log.warning("Unknown key name '%s' for action '%s'", name, action)
            self.bindings[action] = codes

    def rebind(self, action: str, key_names: List[str]) -> None:
        """Remap an action at runtime (e.g. from an options menu)."""
        self._load_bindings({**{action: key_names}})  # rebuild just this action
        codes = {pygame.key.key_code(n) for n in key_names}
        self.bindings[action] = codes
        self.settings.set(f"input.bindings.{action}", key_names)

    def actions_for_key(self, key_code: int) -> List[str]:
        return [a for a, codes in self.bindings.items() if key_code in codes]

    # -- frame lifecycle -----------------------------------------------------
    def begin_frame(self) -> None:
        """Clear per-frame edge state. Call once at the top of each frame."""
        self._pressed.clear()
        self._released.clear()
        self._mouse_pressed.clear()
        self._mouse_released.clear()

    def process_event(self, event: pygame.event.Event) -> None:
        """Feed a pygame event so edge detection works."""
        if event.type == pygame.KEYDOWN:
            self._pressed.add(event.key)
        elif event.type == pygame.KEYUP:
            self._released.add(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._mouse_pressed.add(event.button)
        elif event.type == pygame.MOUSEBUTTONUP:
            self._mouse_released.add(event.button)
        elif event.type == pygame.MOUSEMOTION:
            self._update_mouse(event.pos)

    def _update_mouse(self, window_pos) -> None:
        if self.renderer is not None:
            self.mouse_pos = self.renderer.window_to_base(window_pos)
        else:
            self.mouse_pos = tuple(window_pos)

    # -- queries -------------------------------------------------------------
    def is_down(self, action: str) -> bool:
        """True while any key bound to ``action`` is held."""
        codes = self.bindings.get(action)
        if not codes:
            return False
        keys = pygame.key.get_pressed()
        return any(keys[c] for c in codes if 0 <= c < len(keys))

    def just_pressed(self, action: str) -> bool:
        """True only on the frame a bound key transitions to down."""
        codes = self.bindings.get(action)
        return bool(codes) and any(c in self._pressed for c in codes)

    def just_released(self, action: str) -> bool:
        codes = self.bindings.get(action)
        return bool(codes) and any(c in self._released for c in codes)

    # Axis helper: returns (-1, 0, 1) from a pair of opposing actions. Handy for
    # movement without repeating is_down() everywhere.
    def axis(self, negative_action: str, positive_action: str) -> int:
        return int(self.is_down(positive_action)) - int(self.is_down(negative_action))

    # -- mouse ---------------------------------------------------------------
    def mouse_just_pressed(self, button: int = 1) -> bool:
        return button in self._mouse_pressed

    def mouse_just_released(self, button: int = 1) -> bool:
        return button in self._mouse_released
