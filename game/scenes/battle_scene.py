"""
game.scenes.battle_scene
======================
Turn-based battle UI. It is a thin driver over whatever combat system
``combat.system`` config selects (via ``create_combat``) -- it never implements
combat rules itself, so swapping in a real-time system would only require a
different scene, not changes here or anywhere else.

Flow: pick a command (Attack / Item / Flee) -> the combat system resolves a full
round and returns messages -> show them one at a time -> repeat until the system
reports it's over, then apply the outcome (XP, remove defeated enemies, sync HP)
and return to the overworld (or the title on defeat).
"""

from __future__ import annotations

from engine.combat.combat_system import Combatant, create_combat
from engine.core.scene import Scene
from engine.ui.healthbar import HealthBar
from engine.ui.menu import Menu, MenuItem
from engine.ui.panel import Panel


class BattleScene(Scene):
    transparent = False
    blocks_update = True

    def on_enter(self, enemy_ids=None, **kwargs) -> None:
        g = self.game
        self.style = g.style
        self.hpbar = HealthBar(g.style, width=60, height=5)

        hero_entity = g.world.player
        # Sync persistent vitals onto the live entity so battle starts correct.
        if hero_entity and hero_entity.has("health"):
            hp = hero_entity.get("health")
            hp.hp = g.state.player["hp"]
            hp.max_hp = g.state.player["max_hp"]
        self.hero = Combatant.from_entity(hero_entity, g.state.inventory)
        self.hero.attack = g.state.player["attack"] + g.state.inventory.stat_bonus("attack")
        self.hero.defense = g.state.player["defense"] + g.state.inventory.stat_bonus("defense")

        enemies = []
        for eid in (enemy_ids or []):
            ent = g.world.get(eid)
            if ent:
                enemies.append(Combatant.from_entity(ent))
        if not enemies:  # safety net
            enemies = [Combatant("Slime", 8, 8, 4, 1, xp_reward=8, color=[120, 200, 130])]

        self.combat = create_combat(g.settings, [self.hero], enemies)

        self.state = "command"          # command | item | message
        self._messages = []
        self._ending = None
        self.command_menu = Menu([
            MenuItem("Attack", "attack"),
            MenuItem("Item", "item"),
            MenuItem("Flee", "flee"),
        ], self.style)
        self.item_menu = None
        self._log_line = self.combat.log[-1] if self.combat.log else ""

    # -- update --------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.combat.update(dt)
        inp = self.game.input
        if self.state == "message":
            self._update_message(inp)
        elif self.state == "command":
            self._update_command(inp)
        elif self.state == "item":
            self._update_item(inp)

    def _update_message(self, inp) -> None:
        if inp.just_pressed("confirm") or inp.just_pressed("interact"):
            if self._messages:
                self._log_line = self._messages.pop(0)
            if not self._messages:
                self._after_messages()

    def _update_command(self, inp) -> None:
        if inp.just_pressed("up"):
            self.command_menu.move(-1)
        if inp.just_pressed("down"):
            self.command_menu.move(1)
        if inp.just_pressed("confirm") or inp.just_pressed("interact"):
            choice = self.command_menu.selected.value
            if choice == "attack":
                self._enqueue(self.combat.player_attack())
            elif choice == "flee":
                self._enqueue(self.combat.player_flee())
            elif choice == "item":
                self._open_items()

    def _update_item(self, inp) -> None:
        if inp.just_pressed("up"):
            self.item_menu.move(-1)
        if inp.just_pressed("down"):
            self.item_menu.move(1)
        if inp.just_pressed("cancel") or inp.just_pressed("menu"):
            self.state = "command"
        if inp.just_pressed("confirm") or inp.just_pressed("interact"):
            item_id = self.item_menu.selected.value
            if item_id:
                self._enqueue(self.combat.player_use_item(item_id, self.game.state.inventory))

    # -- helpers -------------------------------------------------------------
    def _open_items(self) -> None:
        inv = self.game.state.inventory
        consumables = []
        seen = set()
        for item_id, _ in [(s[0], s[1]) for s in inv.slots]:
            item = self.game.item_db.get(item_id)
            if item and item.is_consumable and item_id not in seen:
                seen.add(item_id)
                consumables.append(MenuItem(f"{item.name} x{inv.count(item_id)}", item_id))
        if not consumables:
            self._enqueue(["No usable items!"])
            return
        self.item_menu = Menu(consumables, self.style, title="Use which?")
        self.state = "item"

    def _enqueue(self, lines) -> None:
        # Show the first line now; the rest advance on each confirm. Even a
        # single-line message stays up until the player confirms.
        if lines:
            self._messages.extend(lines)
            self._log_line = self._messages.pop(0)
        self.state = "message"

    def _after_messages(self) -> None:
        if self._ending is not None:
            self._finish()
            return
        if self.combat.is_over:
            self._begin_ending()
        else:
            self.state = "command"

    def _begin_ending(self) -> None:
        g = self.game
        res = self.combat.result
        self._ending = res["outcome"]
        # Persist hero HP back to the shared state.
        g.state.player["hp"] = max(0, self.hero.hp)

        if res["outcome"] == "victory":
            leveled = g.state.grant_xp(res["xp"])
            for eid in res["defeated_entity_ids"]:
                ent = g.world.get(eid)
                if ent:
                    for tag in ent.tags:
                        if tag.startswith("spawnid:"):
                            g.state.consumed.add(tag[len("spawnid:"):])
                    g.world.remove_entity(eid)
            msgs = [f"Victory! +{res['xp']} XP"]
            if leveled:
                msgs.append(f"Level up! Now Lv {g.state.player['level']}")
                g.state.player["hp"] = g.state.player["max_hp"]
        elif res["outcome"] == "fled":
            msgs = ["You slipped away."]
        else:
            msgs = ["You were defeated..."]
        self._messages = msgs
        self._log_line = self._messages.pop(0)
        self.state = "message"

    def _finish(self) -> None:
        g = self.game
        if self._ending == "defeat":
            g.scenes.switch_to("title")
        else:
            g.scenes.pop()  # back to the overworld

    # -- draw ----------------------------------------------------------------
    def draw(self, renderer) -> None:
        s = self.style
        bw, bh = renderer.base_size
        renderer.draw_rect((0, 0, bw, bh), (18, 14, 26), layer="background", world=False)

        # Enemies (top), hero (bottom-left), with HP bars.
        for i, enemy in enumerate(self.combat.enemies):
            ex = bw - 90 + i * 26
            ey = 30
            color = tuple(enemy.color) if enemy.alive else (70, 70, 70)
            renderer.draw_rect((ex, ey, 20, 16), color, layer="entities", world=False)
            self.hpbar.draw(renderer, ex - 20, ey - 10, enemy.fraction, label=enemy.name)

        renderer.draw_rect((24, bh - 70, 16, 18), tuple(self.hero.color),
                           layer="entities", world=False)
        self.hpbar.draw(renderer, 20, bh - 84,
                        self.hero.fraction,
                        label=f"{self.hero.name}  {self.hero.hp}/{self.hero.max_hp}")

        # Bottom panel: command menu OR message log.
        panel = Panel(6, bh - 46, bw - 12, 40, s)
        panel.draw(renderer)
        if self.state == "command":
            renderer.draw_text("What will you do?", panel.inner_x, panel.inner_y,
                               s.font, s.text_color, layer="ui", world=False)
            self._draw_commands_row(renderer, panel)
        elif self.state == "item" and self.item_menu:
            self.item_menu.draw(renderer, panel.inner_x, panel.inner_y)
        else:  # message
            renderer.draw_text(self._log_line, panel.inner_x, panel.inner_y + 6,
                               s.font, s.text_color, layer="ui", world=False)
            renderer.draw_text(s.cursor, panel.x + panel.w - 12,
                               panel.y + panel.h - s.line_height - 2,
                               s.font, s.highlight_color, layer="ui", world=False)

    def _draw_commands_row(self, renderer, panel) -> None:
        s = self.style
        x = panel.inner_x
        y = panel.inner_y + s.line_height + 3
        for i, item in enumerate(self.command_menu.items):
            color = s.highlight_color if i == self.command_menu.index else s.text_color
            prefix = (s.cursor + " ") if i == self.command_menu.index else "  "
            renderer.draw_text(prefix + item.label, x, y, s.font, color, layer="ui", world=False)
            x += 52
