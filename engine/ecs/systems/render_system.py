"""
engine.ecs.systems.render_system
===============================
Draws every entity that has a Transform + Sprite.

Unlike other systems this runs in the *draw* phase (call ``draw(world, renderer)``
from the scene), because drawing must happen between the renderer's
begin/end-frame, not during update. It:

- resolves each sprite's surface once and caches it on the component (a colour
  box via the AssetManager, or a loaded image, scaled by ``world.sprite_scale``),
- enqueues it on the sprite's configured layer with a y-sort key at the entity's
  "feet" so characters lower on screen overlap those above them,
- advances the optional AnimationComponent (extension hook),
- optionally overlays collider boxes when ``debug.show_colliders`` is set.

Resolution independence and layering are entirely the renderer's job; this system
just feeds it world-space draw calls.
"""

from __future__ import annotations

import pygame

from engine.utils.geometry import clamp


class RenderSystem:
    def __init__(self, assets, settings, palettes=None) -> None:
        self.assets = assets
        self.settings = settings
        self.palettes = palettes               # optional PaletteManager (recolour)
        self.sprite_scale = settings.get("world.sprite_scale", 1.0)
        self.debug_colliders = settings.get("debug.show_colliders", False)
        self._scaled_cache = {}  # id(surface) -> scaled surface
        self._flash_cache = {}   # id(surface) -> whitened surface
        self.flashes = {}        # entity_id -> remaining flash seconds (hit-flash)

    def flash(self, entity_id: int, duration: float = 0.12) -> None:
        """Trigger a white hit-flash on an entity (pixel-art damage feedback)."""
        self.flashes[entity_id] = duration

    def update_flashes(self, dt: float) -> None:
        if self.flashes:
            self.flashes = {k: v - dt for k, v in self.flashes.items() if v - dt > 0}

    def _whiten(self, surf):
        cached = self._flash_cache.get(id(surf))
        if cached is None:
            cached = surf.copy()
            cached.fill((180, 180, 180), special_flags=pygame.BLEND_RGB_ADD)
            self._flash_cache[id(surf)] = cached
        return cached

    # -- surface resolution --------------------------------------------------
    def _apply_scale(self, surf: pygame.Surface) -> pygame.Surface:
        if self.sprite_scale == 1.0:
            return surf
        key = id(surf)
        cached = self._scaled_cache.get(key)
        if cached is None:
            w, h = surf.get_size()
            cached = pygame.transform.scale(
                surf, (int(w * self.sprite_scale), int(h * self.sprite_scale)))
            self._scaled_cache[key] = cached
        return cached

    def _surface_for(self, sprite) -> pygame.Surface:
        if sprite._surface is not None:
            return sprite._surface
        if sprite.image:
            surf = self.assets.get_image(sprite.image)
        else:
            color = tuple(sprite.color) if sprite.color else (255, 0, 220)
            w, h = sprite.size
            surf = self.assets.placeholder(w, h, color)
        if sprite.palette and self.palettes:
            surf = self.palettes.recolor(surf, sprite.palette)
        surf = self._apply_scale(surf)
        sprite._surface = surf
        return surf

    # -- draw ----------------------------------------------------------------
    def draw(self, world, renderer) -> None:
        for e in world.with_components("transform", "sprite"):
            sprite = e.get("sprite")
            if not sprite.visible:
                continue
            t = e.get("transform")
            # Prefer an active animation frame; fall back to the static sprite.
            anim = e.get("animation")
            if anim is not None and getattr(anim, "current_surface", None) is not None:
                frame = anim.current_surface
                if sprite.palette and self.palettes:        # runtime recolour
                    frame = self.palettes.recolor(frame, sprite.palette)
                surf = self._apply_scale(frame)
            else:
                surf = self._surface_for(sprite)
            if self.flashes.get(e.id):                       # white hit-flash
                surf = self._whiten(surf)
            x = t.x + sprite.offset[0]
            y = t.y + sprite.offset[1]
            sort_y = (t.y + surf.get_height()) if sprite.y_sort else None
            renderer.draw_image(surf, x, y, layer=sprite.layer, world=True, sort_y=sort_y)

        if self.debug_colliders or self.settings.get("debug.show_colliders", False):
            self._draw_colliders(world, renderer)

    def _draw_colliders(self, world, renderer) -> None:
        for e in world.with_components("transform", "collider"):
            t = e.get("transform")
            col = e.get("collider")
            color = (255, 80, 80) if col.solid else (80, 200, 255)
            renderer.draw_rect(col.rect(t.x, t.y), color, layer="overlay",
                               world=True, width=1)
