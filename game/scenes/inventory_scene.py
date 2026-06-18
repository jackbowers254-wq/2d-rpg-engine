"""
game.scenes.inventory_scene
=========================
An overlay listing the player's items. Confirm uses a consumable (on the player)
or equips an equipment item; equipped items are marked. Demonstrates the
inventory's use/equip API and the Menu widget driving live data.
"""

from __future__ import annotations

from engine.core.scene import Scene
from engine.ui.menu import Menu, MenuItem
from engine.ui.panel import Panel
from engine.ui.text import wrap_text


class InventoryScene(Scene):
    transparent = True
    blocks_update = True

    def on_enter(self, **kwargs) -> None:
        self.style = self.game.style
        self._toast = ""
        self._rebuild()

    def _rebuild(self) -> None:
        inv = self.game.state.inventory
        items = []
        for item_id, qty in [(s[0], s[1]) for s in inv.slots]:
            item = self.game.item_db.get(item_id)
            if not item:
                continue
            equipped = inv.equipped.get(item.equip_slot or "") == item_id
            label = f"{item.name} x{qty}" + ("  [E]" if equipped else "")
            items.append(MenuItem(label, item_id))
        if not items:
            items = [MenuItem("(empty)", None, enabled=False)]
        self.menu = Menu(items, self.style, title="Items")

    def update(self, dt: float) -> None:
        inp = self.game.input
        if inp.just_pressed("up"):
            self.menu.move(-1)
        if inp.just_pressed("down"):
            self.menu.move(1)
        if inp.just_pressed("inventory") or inp.just_pressed("cancel") or inp.just_pressed("menu"):
            self.game.scenes.pop()
            return
        if inp.just_pressed("confirm") or inp.just_pressed("interact"):
            self._use(self.menu.selected.value if self.menu.selected else None)

    def _use(self, item_id) -> None:
        if not item_id:
            return
        g = self.game
        item = g.item_db.get(item_id)
        inv = g.state.inventory
        player = getattr(g, "world", None).player if getattr(g, "world", None) else None
        if item.equip_slot:
            inv.equip(item_id)
            self._toast = f"Equipped {item.name}."
        else:
            ok, msg = inv.use(item_id, player)
            self._toast = msg if ok else "Can't use that."
            # Keep persistent player vitals in sync with the healed entity.
            if player is not None and player.has("health"):
                g.state.player["hp"] = player.get("health").hp
        self._rebuild()

    def draw(self, renderer) -> None:
        s = self.style
        bw, bh = renderer.base_size
        renderer.draw_rect((0, 0, bw, bh), (0, 0, 0, 150), layer="ui", world=False)
        panel = Panel(bw // 2 - 70, 16, 140, bh - 48, s)
        panel.draw(renderer)
        self.menu.draw(renderer, panel.inner_x, panel.inner_y)

        # Description of the highlighted item.
        sel = self.menu.selected
        item = self.game.item_db.get(sel.value) if sel and sel.value else None
        y = panel.y + panel.h - 22
        if item:
            for line in wrap_text(s.font, item.description, int(panel.inner_width)):
                renderer.draw_text(line, panel.inner_x, y, s.font, s.disabled_color,
                                   layer="ui", world=False)
                y += s.line_height
        if self._toast:
            renderer.draw_text(self._toast, bw // 2, bh - 12, s.font, s.highlight_color,
                               layer="ui", world=False, anchor="center")
