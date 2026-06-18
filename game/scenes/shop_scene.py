"""
game.scenes.shop_scene
====================
A buy/sell shop overlay. Left/Right switch the Buy/Sell tab, Up/Down select,
Confirm trades, Esc closes. Prices come from the ShopDef + item values; currency
is GameState.currency.
"""

from __future__ import annotations

from engine.core.scene import Scene
from engine.ui.menu import Menu, MenuItem
from engine.ui.panel import Panel
from engine.ui.text import wrap_text


class ShopScene(Scene):
    transparent = True
    blocks_update = True

    def on_enter(self, shop="", **kwargs) -> None:
        g = self.game
        self.style = g.style
        self.shop = g.shops.get(shop)
        self.tab = "buy"
        self._toast = self.shop.greeting if self.shop else "..."
        self._rebuild()

    # -- list building -------------------------------------------------------
    def _rebuild(self) -> None:
        g = self.game
        if self.shop is None:
            self.menu = Menu([MenuItem("(closed)", None, enabled=False)], self.style)
            return
        items = []
        if self.tab == "buy":
            for si in self.shop.stock:
                item = g.item_db.get(si.item)
                if item is None:
                    continue
                price = self.shop.buy_price(g.item_db, si)
                affordable = g.state.currency >= price
                items.append(MenuItem(f"{item.name}  {price}g", (si.item, price), enabled=affordable))
        else:  # sell
            seen = set()
            for iid, _qty in [(s[0], s[1]) for s in g.state.inventory.slots]:
                if iid in seen:
                    continue
                seen.add(iid)
                item = g.item_db.get(iid)
                price = self.shop.sell_price(g.item_db, iid)
                if item and price > 0:
                    items.append(MenuItem(f"{item.name} x{g.state.inventory.count(iid)}  {price}g",
                                          (iid, price)))
        if not items:
            items = [MenuItem("(nothing)", None, enabled=False)]
        self.menu = Menu(items, self.style)

    # -- input ---------------------------------------------------------------
    def update(self, dt: float) -> None:
        inp = self.game.input
        if inp.just_pressed("cancel") or inp.just_pressed("menu"):
            self.game.scenes.pop()
            return
        if inp.just_pressed("left") and self.tab != "buy":
            self.tab = "buy"; self._rebuild()
        if inp.just_pressed("right") and self.tab != "sell":
            self.tab = "sell"; self._rebuild()
        if inp.just_pressed("up"):
            self.menu.move(-1)
        if inp.just_pressed("down"):
            self.menu.move(1)
        if inp.just_pressed("confirm") or inp.just_pressed("interact"):
            self._trade(self.menu.selected.value if self.menu.selected else None)

    def _trade(self, value) -> None:
        if not value:
            return
        g = self.game
        item_id, price = value
        item = g.item_db.get(item_id)
        if self.tab == "buy":
            if g.state.currency < price:
                self._toast = "Not enough gold."
            elif g.state.inventory.add(item_id, 1) <= 0:
                self._toast = "Inventory full."
            else:
                g.state.currency -= price
                g.audio.play_sound("confirm.wav")
                self._toast = f"Bought {item.name}."
        else:  # sell
            if g.state.inventory.remove(item_id, 1) > 0:
                g.state.currency += price
                g.audio.play_sound("confirm.wav")
                self._toast = f"Sold {item.name} for {price}g."
        self._rebuild()

    # -- draw ----------------------------------------------------------------
    def draw(self, renderer) -> None:
        s = self.style
        bw, bh = renderer.base_size
        renderer.draw_rect((0, 0, bw, bh), (0, 0, 0, 160), layer="ui", world=False)
        panel = Panel(10, 8, bw - 20, bh - 16, s)
        panel.draw(renderer)
        x, y = panel.inner_x, panel.inner_y

        name = self.shop.name if self.shop else "Shop"
        renderer.draw_text(name, x, y, s.title_font, s.highlight_color, layer="ui", world=False)
        renderer.draw_text(f"Gold: {self.game.state.currency}", bw - 16, y, s.font,
                           s.text_color, layer="ui", world=False, anchor="topright")
        y += s.title_font.get_height() + 2

        # Tabs.
        bx = x
        for tab, label in (("buy", "Buy"), ("sell", "Sell")):
            color = s.highlight_color if tab == self.tab else s.disabled_color
            renderer.draw_text(label, bx, y, s.font, color, layer="ui", world=False)
            bx += 34
        renderer.draw_text("(<- ->)", bx + 4, y, s.font, s.disabled_color, layer="ui", world=False)
        y += s.line_height + 2

        self.menu.draw(renderer, x, y)

        # Description of the highlighted item.
        sel = self.menu.selected
        if sel and sel.value:
            item = self.game.item_db.get(sel.value[0])
            if item:
                yy = panel.y + panel.h - 24
                for line in wrap_text(s.font, item.description, int(panel.inner_width)):
                    renderer.draw_text(line, x, yy, s.font, s.disabled_color, layer="ui", world=False)
                    yy += s.line_height
        renderer.draw_text(self._toast, bw // 2, bh - 12, s.font, s.highlight_color,
                           layer="ui", world=False, anchor="center")
