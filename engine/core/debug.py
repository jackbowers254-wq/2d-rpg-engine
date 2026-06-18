"""
engine.core.debug
================
A runtime debug overlay, toggled with the ``debug_toggle`` action (F1 by default).

When on it shows FPS, frame time, the scene stack, entity count, the player's
pixel/tile position and the camera offset; it enables collider boxes, draws a tile
grid, and inspects the entity nearest the player (its type + component summary).
It is drawn by the Game on top of whatever scene is active, so it works
everywhere without per-scene code.

It reads the world via ``game.world`` if the active game exposes one (the demo's
overworld does); it degrades gracefully when there is none (e.g. on the title).
"""

from __future__ import annotations

from typing import List, Optional


class DebugOverlay:
    def __init__(self, game) -> None:
        self.game = game
        self.visible = False
        self.font = game.assets.get_font(game.settings.get("ui.font_size", 8))
        self.tile_size = game.settings.get("world.tile_size", 16)
        self._was_show_colliders = game.settings.get("debug.show_colliders", False)

    # -- input ---------------------------------------------------------------
    def update(self) -> None:
        if self.game.input.just_pressed("debug_toggle"):
            self.visible = not self.visible
            # Turn collider boxes on/off with the overlay (RenderSystem reads this).
            self.game.settings.set("debug.show_colliders",
                                   self.visible or self._was_show_colliders)

    # -- helpers -------------------------------------------------------------
    def _world(self):
        return getattr(self.game, "world", None)

    def _nearest_entity(self, world, player):
        if player is None or not player.has("transform"):
            return None
        pt = player.get("transform")
        best, bestd = None, 1e18
        for e in world.entities:
            if e is player or not e.has("transform"):
                continue
            t = e.get("transform")
            d = (t.x - pt.x) ** 2 + (t.y - pt.y) ** 2
            if d < bestd:
                best, bestd = e, d
        return best

    # -- draw ----------------------------------------------------------------
    def draw(self, renderer) -> None:
        if not self.visible:
            return
        bw, bh = renderer.base_size
        clock = self.game.clock
        world = self._world()

        lines: List[str] = [
            f"FPS {clock.get_fps():4.0f}  ({clock.get_time()} ms)",
            f"scene: {type(self.game.scenes.current).__name__}",
        ]
        player = world.player if world else None
        if world:
            lines.append(f"entities: {sum(1 for _ in world.entities)}")
        if player and player.has("transform"):
            t = player.get("transform")
            lines.append(f"player: ({t.x:.0f},{t.y:.0f}) tile ({int(t.x//self.tile_size)},"
                         f"{int(t.y//self.tile_size)}) facing {t.facing}")
        cam = renderer.camera
        if cam:
            ox, oy = cam.offset
            lines.append(f"camera: ({ox:.0f},{oy:.0f})")

        # Grid (world-aligned) + nearest-entity inspection.
        if world and cam:
            self._draw_grid(renderer, cam, bw, bh)
            target = self._nearest_entity(world, player)
            if target:
                lines.append(f"-- nearest: {target.type or target.name} #{target.id}")
                for cname in sorted(target.components):
                    lines.append(f"   {cname}{self._summ(target.get(cname))}")

        # Panel + text on the overlay layer (always on top, screen space).
        pad = 3
        h = pad * 2 + len(lines) * (self.font.get_height())
        renderer.draw_rect((0, 0, 150, h), (0, 0, 0, 170), layer="overlay", world=False)
        y = pad
        for line in lines:
            renderer.draw_text(line, pad, y, self.font, (140, 255, 160),
                               layer="overlay", world=False)
            y += self.font.get_height()

    def _summ(self, comp) -> str:
        """A compact one-line summary of a component's notable fields."""
        name = type(comp).__name__
        if name == "HealthComponent":
            return f": {comp.hp}/{comp.max_hp}"
        if name == "TransformComponent":
            return f": {comp.facing}"
        if name == "AIComponent":
            return f": {comp.behavior}"
        if name == "MovementComponent":
            return f": {comp.style}{' moving' if comp.moving else ''}"
        return ""

    def _draw_grid(self, renderer, cam, bw, bh) -> None:
        ts = self.tile_size
        ox, oy = cam.offset
        x0 = -(ox % ts)
        y0 = -(oy % ts)
        col = (255, 255, 255, 40)
        x = x0
        while x <= bw:
            renderer.draw_rect((ox + x, oy, 1, bh), col, layer="overlay", world=True)
            x += ts
        y = y0
        while y <= bh:
            renderer.draw_rect((ox, oy + y, bw, 1), col, layer="overlay", world=True)
            y += ts
