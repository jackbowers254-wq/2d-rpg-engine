"""
game.scenes.overworld_scene
=========================
The playable scene. It owns the ECS World for the active map and orchestrates the
engine systems each frame:

  PlayerController -> AI -> Movement(+collision)   (world.update)
  camera follow                                     (camera.update)
  trigger checks: portals, item pickup, enemy touch (this scene)
  draw: tilemap -> entities(y-sorted) -> HUD        (draw)

It is the integration layer -- almost all behaviour lives in the engine; this
scene wires data (maps, spawns, archetypes) to those systems and handles the
game-flow transitions (dialogue, battle, pause, map changes, save/load).

Map transitions are data: portals are Tiled objects naming a ``target_map`` and
destination tile. Spawns are Tiled objects naming an ``entity`` archetype; this
scene skips ones already "consumed" (picked up / defeated) per GameState so the
world stays persistent across saves.
"""

from __future__ import annotations

from typing import List, Optional

from engine.core.scene import Scene
from engine.ecs.systems.ai_system import AISystem
from engine.ecs.systems.animation_system import AnimationSystem
from engine.ecs.systems.movement_system import MovementSystem
from engine.ecs.systems.player_controller import PlayerControllerSystem
from engine.ecs.systems.render_system import RenderSystem
import os

from engine.ecs.world import World
from engine.graphics.camera import Camera
from engine.graphics.transitions import Transition
from engine.scripting.script import ScriptContext, ScriptRunner
from engine.ui.healthbar import HealthBar
from engine.utils.geometry import aabb_overlap
from engine.utils.logger import get_logger

log = get_logger("overworld")


class OverworldScene(Scene):
    def on_enter(self, load_existing: bool = False, **kwargs) -> None:
        g = self.game
        self.style = g.style
        self.hpbar = HealthBar(g.style, width=64, height=5)
        self._toast = ""
        self._toast_t = 0.0
        self._portal_cooldown = 0.0
        self._portal_locked = True        # unlocked once the player steps off portals
        self._near_interactable = None
        self.transition = None            # active screen Transition, if any
        self.script = None                # active cutscene ScriptRunner, if any
        self._player_locked = False        # True during a cutscene
        self._inside_triggers = set()      # trigger names the player currently overlaps

        # Quest toasts + hit SFX (subscriptions cleaned up in on_exit).
        self._event_unsubs = [
            g.events.subscribe("quest_started", self._on_quest_started),
            g.events.subscribe("quest_completed", self._on_quest_completed),
            g.events.subscribe("entity_damaged", lambda **k: g.audio.play_sound("hit.wav")),
        ]

        # ECS world + systems (intent -> ai -> movement -> render).
        self.world = World(settings=g.settings, events=g.events)
        self.world.add_system(PlayerControllerSystem(g.input))
        self.world.add_system(AISystem())
        self.world.add_system(MovementSystem())
        self.world.add_system(AnimationSystem(g.assets))
        self.render_system = RenderSystem(g.assets, g.settings)
        g.world = self.world  # expose for overlays (inventory/battle)

        # Combat style is a config switch: "encounter" (turn-based battle scene)
        # or "action" (real-time melee handled by a system in this scene).
        self.combat_style = g.settings.get("combat.style", "encounter")
        if self.combat_style == "action":
            from engine.combat.action_combat import ActionCombatSystem
            self.world.add_system(ActionCombatSystem(
                g.input, g.events, g.settings,
                on_enemy_defeated=self._on_enemy_defeated,
                on_player_death=self._on_player_death))

        ts = g.settings.get("world.tile_size", 16)
        self.tile_size = ts
        view_w, view_h = g.renderer.base_size
        self.camera = Camera(view_w, view_h, g.settings)

        self._load_map(g.state.current_map, use_player_start=not bool(g.state.spawn_position))

    # -- map loading ---------------------------------------------------------
    def _load_map(self, name: str, use_player_start: bool = False) -> None:
        g = self.game
        tmap = g.world_map.change_to(name)
        g.state.current_map = name
        g.state.flags[f"visited_{name}"] = True  # e.g. visited_cave for dialogue

        self.world.clear_entities()
        self.world.tilemap = tmap
        self.camera.set_bounds(0, 0, tmap.pixel_width, tmap.pixel_height)

        # Spawn entities from map 'spawn' objects, skipping consumed ones.
        for obj in tmap.find_objects("spawn"):
            if g.state.is_consumed(name, obj.name):
                continue
            entity = g.factory.create_from_spawn(obj, self.tile_size)
            if entity is None:
                continue
            entity.add_tag(f"spawnid:{name}/{obj.name}")  # so battle/pickup can consume it
            self.world.add_entity(entity)

        # Place the player.
        px, py, facing = self._player_spawn(tmap, use_player_start)
        self.player = self._make_player(px, py, facing)
        self.world.add_entity(self.player)
        self.camera.snap_to(px + 8, py + 8)
        g.state.spawn_position = None  # consumed once used
        # Don't let the just-arrived player immediately re-trigger a portal; they
        # must step off any portal tile first.
        self._portal_locked = True
        self._inside_triggers = set()

        # Background music for this map (data-driven), crossfading from the last.
        music = tmap.properties.get("music")
        if music:
            g.audio.play_music(music)

        # Fire any 'load' triggers for this map (e.g. an intro on first entry).
        for trg in tmap.find_objects("trigger"):
            if trg.properties.get("event") == "load":
                self._maybe_fire_trigger(trg)

    def _player_spawn(self, tmap, use_player_start: bool):
        g = self.game
        if not use_player_start and g.state.spawn_position:
            x, y, facing = g.state.spawn_position
            return x, y, facing
        start = next(iter(tmap.find_objects("player_start")), None)
        if start:
            return start.x, start.y, start.properties.get("facing", "down")
        return self.tile_size * 2, self.tile_size * 2, "down"  # fallback

    def _make_player(self, x, y, facing):
        g = self.game
        # Movement style/speed are a single config switch (player.*).
        overrides = {"movement": {
            "style": g.settings.get("player.movement_style", "smooth"),
            "speed": g.settings.get("player.move_speed", 70),
            "run_multiplier": g.settings.get("player.run_multiplier", 1.7),
        }}
        player = g.factory.create("player", x=x, y=y, overrides=overrides)
        t = player.get("transform")
        t.facing = facing
        # Apply persistent vitals from GameState.
        if player.has("health"):
            hp = player.get("health")
            hp.hp = g.state.player["hp"]
            hp.max_hp = g.state.player["max_hp"]
        if player.has("stats"):
            st = player.get("stats")
            st.attack = g.state.player["attack"]
            st.defense = g.state.player["defense"]
        return player

    # -- per-frame -----------------------------------------------------------
    def update(self, dt: float) -> None:
        g = self.game
        inp = g.input

        # A screen transition freezes the world until it finishes (the map swap
        # happens at its covered midpoint via on_cover).
        if self.transition is not None:
            if self.transition.update(dt):
                self.transition = None
            return

        # Cutscene mode: advance the script (before world.update so scripted
        # movement intent is consumed this frame), keep the world simulating
        # (entities move), but ignore player input and triggers.
        if self.script is not None or self._player_locked:
            if self.script is not None:
                self.script.update(dt)
            self.world.update(dt)
            t = self.player.get("transform")
            self.camera.update(t.x + 8, t.y + 8, dt)
            return

        self._portal_cooldown = max(0.0, self._portal_cooldown - dt)
        if self._toast_t > 0:
            self._toast_t -= dt

        # Global hotkeys.
        if inp.just_pressed("menu"):
            g.scenes.push("pause")
            return
        if inp.just_pressed("inventory"):
            g.scenes.push("inventory")
            return
        if inp.just_pressed("quest_log"):
            g.scenes.push("quest_log")
            return
        if inp.just_pressed("quicksave"):
            self._sync_player_to_state()
            g.saves.save(1, g.state.to_data(), g.state.save_meta())
            self._show_toast("Saved.")
        if inp.just_pressed("quickload") and g.saves.exists(1):
            data = g.saves.load(1)
            if data:
                g.state.from_data(data)
                g.scenes.switch_to("overworld", load_existing=True)
                return

        # Advance simulation (movement, collision, AI). Removal flush happens here,
        # so a just-defeated enemy can't re-trigger below.
        self.world.update(dt)  # includes the AnimationSystem

        # Camera follows the player centre.
        t = self.player.get("transform")
        self.camera.update(t.x + 8, t.y + 8, dt)

        if getattr(self.game, "quests", None):
            self.game.quests.update(dt)  # poll flag/collect objectives

        self._update_interactions(inp)
        self._update_pickups()
        if self.combat_style == "encounter":
            self._update_enemy_touch()  # action style handles combat in its system
        self._update_portals()
        self._update_triggers()

    # -- interactions --------------------------------------------------------
    def _player_rect(self):
        col = self.player.get("collider")
        t = self.player.get("transform")
        return col.rect(t.x, t.y)

    def _player_center(self):
        t = self.player.get("transform")
        return (t.x + 8, t.y + 8)

    def _update_interactions(self, inp) -> None:
        # Find the nearest enabled interactable within range (for prompt + action).
        cx, cy = self._player_center()
        nearest = None
        best = 1e9
        for e in self.world.with_components("transform", "interactable"):
            inter = e.get("interactable")
            if not inter.enabled:
                continue
            et = e.get("transform")
            dx, dy = (et.x + 8) - cx, (et.y + 8) - cy
            d = (dx * dx + dy * dy) ** 0.5
            if d <= inter.radius and d < best:
                best, nearest = d, e
        self._near_interactable = nearest

        pressed = inp.just_pressed("interact") or inp.just_pressed("confirm")
        if nearest and pressed:
            self._interact_with(nearest)
        elif pressed:
            # 'interact' triggers (map objects) fire when stood on and confirmed.
            pr = self._player_rect()
            for trg in self.world.tilemap.find_objects("trigger"):
                if trg.properties.get("event") == "interact" and \
                        aabb_overlap(*pr, trg.x, trg.y, trg.width, trg.height):
                    self._maybe_fire_trigger(trg)
                    break

    def _interact_with(self, entity) -> None:
        inter = entity.get("interactable")
        if inter.action == "dialogue" or inter.action == "sign":
            self.game.scenes.push("dialogue", dialogue=inter.params.get("dialogue", ""))
        elif inter.action == "pickup":
            self._pick_up(entity)
        elif inter.action == "battle":
            self._start_battle([entity.id])

    # -- pickups -------------------------------------------------------------
    def _update_pickups(self) -> None:
        pr = self._player_rect()
        for e in self.world.with_components("transform", "pickup", "collider"):
            pick = e.get("pickup")
            if not pick.auto:
                continue
            col = e.get("collider")
            t = e.get("transform")
            if aabb_overlap(*pr, *col.rect(t.x, t.y)):
                self._pick_up(e)

    def _pick_up(self, entity) -> None:
        pick = entity.get("pickup")
        added = self.game.state.inventory.add(pick.item_id, pick.quantity)
        if added <= 0:
            self._show_toast("Inventory full!")
            return
        item = self.game.item_db.get(pick.item_id)
        self._show_toast(f"Got {item.name if item else pick.item_id}!")
        self.game.audio.play_sound("pickup.wav")
        self._consume_entity(entity)

    # -- enemy contact -> battle --------------------------------------------
    def _update_enemy_touch(self) -> None:
        if self._portal_cooldown > 0:
            return
        pr = self._player_rect()
        for e in self.world.with_components("transform", "collider"):
            if not e.has_tag("enemy"):
                continue
            col = e.get("collider")
            if not col.trigger:
                continue
            t = e.get("transform")
            if aabb_overlap(*pr, *col.rect(t.x, t.y)):
                self._start_battle([e.id])
                return

    def _start_battle(self, enemy_ids: List[int]) -> None:
        self._sync_player_to_state()
        self._portal_cooldown = 0.6  # avoid instant re-trigger on return
        self.game.scenes.push("battle", enemy_ids=enemy_ids)

    # -- action-combat callbacks (used when combat.style == "action") --------
    def _on_enemy_defeated(self, entity) -> None:
        stats = entity.get("stats")
        xp = stats.xp_reward if stats else 0
        leveled = self.game.state.grant_xp(xp)
        if leveled:
            self._apply_state_to_player()  # level-up heals + boosts the live entity
        self._consume_entity(entity)
        self._show_toast(f"Defeated {entity.name}! +{xp} XP")

    def _on_player_death(self) -> None:
        self.game.state.player["hp"] = 0
        self.game.scenes.switch_to("title")

    def _apply_state_to_player(self) -> None:
        st = self.game.state.player
        if self.player.has("health"):
            hp = self.player.get("health")
            hp.max_hp = st["max_hp"]
            hp.hp = st["hp"]
        if self.player.has("stats"):
            s = self.player.get("stats")
            s.attack, s.defense = st["attack"], st["defense"]

    # -- portals / map transitions ------------------------------------------
    def _update_portals(self) -> None:
        if self._portal_cooldown > 0:
            return
        pr = self._player_rect()
        on_portal = None
        for portal in self.world.tilemap.find_objects("portal"):
            if aabb_overlap(*pr, portal.x, portal.y, portal.width, portal.height):
                on_portal = portal
                break
        # Step-off lock: after arriving, ignore portals until the player has
        # moved clear of every portal (robust, no timing hacks at boundaries).
        if self._portal_locked:
            if on_portal is None:
                self._portal_locked = False
            return
        if on_portal is not None:
            self._take_portal(on_portal)

    def _take_portal(self, portal) -> None:
        g = self.game
        p = portal.properties
        target = p.get("target_map")
        # Validate the destination up front with a clear message instead of a crash.
        if not target:
            log.error("Portal '%s' has no target_map", portal.name)
            self._show_toast("Broken portal (no target_map)")
            return
        if not g.world_map.has(target):
            log.error("Portal '%s' targets unknown map '%s' (known: %s)",
                      portal.name, target, g.world_map.map_names)
            self._show_toast(f"Portal target '{target}' not found")
            return
        dest = g.world_map.get(target)
        txi, tyi = int(p.get("target_x", 0)), int(p.get("target_y", 0))
        if not (0 <= txi < dest.width and 0 <= tyi < dest.height):
            log.error("Portal '%s' target tile (%d,%d) out of bounds for '%s' (%dx%d)",
                      portal.name, txi, tyi, target, dest.width, dest.height)
            self._show_toast("Portal destination out of bounds")
            return

        tx, ty = txi * self.tile_size, tyi * self.tile_size
        g.state.spawn_position = (tx, ty, p.get("facing", "down"))

        def _do_change():
            self._load_map(target, use_player_start=False)

        if g.settings.get("transitions.enabled", True):
            self.transition = Transition(
                kind=g.settings.get("transitions.type", "fade"),
                duration=g.settings.get("transitions.duration", 0.45),
                color=tuple(g.settings.get("transitions.color", [0, 0, 0])),
                cell=g.settings.get("transitions.cell", 8),
                on_cover=_do_change)
        else:
            _do_change()

    # -- triggers & cutscene scripting --------------------------------------
    def _update_triggers(self) -> None:
        """Fire 'enter' triggers on the frame the player steps into them."""
        pr = self._player_rect()
        current = set()
        for trg in self.world.tilemap.find_objects("trigger"):
            if trg.properties.get("event", "enter") != "enter":
                continue
            name = trg.name or f"trg@{trg.x:.0f},{trg.y:.0f}"
            if aabb_overlap(*pr, trg.x, trg.y, trg.width, trg.height):
                current.add(name)
                if name not in self._inside_triggers:
                    self._maybe_fire_trigger(trg)
                    if self.script is not None:  # a cutscene just started
                        self._inside_triggers = current
                        return
        self._inside_triggers = current

    def _trigger_condition_ok(self, props: dict) -> bool:
        req, unless = props.get("requires"), props.get("unless")
        if req and not self.game.state.flags.get(req):
            return False
        if unless and self.game.state.flags.get(unless):
            return False
        return True

    def _maybe_fire_trigger(self, trg) -> None:
        if self.script is not None:
            return  # one cutscene at a time
        props = trg.properties
        if not self._trigger_condition_ok(props):
            return
        sid = f"{self.world.tilemap.name}/{trg.name}"
        once = props.get("once", True)
        if once and self.game.state.flags.get(f"_trg:{sid}"):
            return
        actions = self._load_script(props["script"]) if props.get("script") else []
        if not actions:
            return
        if once:
            self.game.state.flags[f"_trg:{sid}"] = True
        self._start_script(actions)

    def _load_script(self, script_id: str):
        path = os.path.join(self.game.settings.get("scripting.scripts_path", "data/scripts"),
                            f"{script_id}.json")
        data = self.game.assets.load_json(path, cache=True)
        return data.get("actions", []) if isinstance(data, dict) else data

    def _start_script(self, actions, source=None) -> None:
        ctx = ScriptContext(self.game, self.world, self)
        ctx.source = source
        self.script = ScriptRunner(actions, ctx, on_complete=self._end_cutscene)
        self.set_player_locked(True)

    def _end_cutscene(self) -> None:
        self.script = None
        self.set_player_locked(False)

    def set_player_locked(self, locked: bool) -> None:
        """Disable player control + movement during a cutscene (and restore)."""
        self._player_locked = locked
        pc = self.player.get("player_controlled")
        if pc is not None:
            pc.enabled = not locked
        if locked:
            m = self.player.get("movement")
            if m is not None:
                m.vx = m.vy = 0.0
                m.input_dx = m.input_dy = 0

    def warp_player(self, map_name: str, tx, ty, facing: str = "down") -> None:
        """Scripted teleport (used by the 'teleport' action with a map)."""
        ts = self.tile_size
        self.game.state.spawn_position = (tx * ts, ty * ts, facing)
        self._load_map(map_name, use_player_start=False)
        if self._player_locked or self.script is not None:
            self.set_player_locked(True)  # re-lock the rebuilt player entity

    # -- consume / persistence ----------------------------------------------
    def _consume_entity(self, entity) -> None:
        for tag in entity.tags:
            if tag.startswith("spawnid:"):
                self.game.state.consumed.add(tag[len("spawnid:"):])
        self.world.remove_entity(entity.id)

    def _sync_player_to_state(self) -> None:
        g = self.game
        t = self.player.get("transform")
        g.state.spawn_position = (t.x, t.y, t.facing)
        if self.player.has("health"):
            hp = self.player.get("health")
            g.state.player["hp"] = hp.hp
            g.state.player["max_hp"] = hp.max_hp

    def on_pause(self) -> None:
        # Called when an overlay (pause/dialogue/battle/inventory) is pushed on
        # top -> capture current position so a Save reflects where we are.
        self._sync_player_to_state()

    def on_resume(self) -> None:
        # Returning from a scene that changed the music (e.g. battle) -> restore
        # this map's track (a no-op crossfade if it never changed).
        music = self.world.tilemap.properties.get("music") if self.world.tilemap else None
        if music:
            self.game.audio.play_music(music)

    # -- quest toasts --------------------------------------------------------
    def _on_quest_started(self, quest="", **_kw) -> None:
        qdef = self.game.quest_db.get(quest)
        self._show_toast(f"New quest: {qdef.name if qdef else quest}", 2.5)

    def _on_quest_completed(self, quest="", **_kw) -> None:
        qdef = self.game.quest_db.get(quest)
        self._show_toast(f"Quest complete: {qdef.name if qdef else quest}!", 3.0)

    def on_exit(self) -> None:
        for unsub in self._event_unsubs:
            unsub()
        self._event_unsubs = []

    # -- toast ---------------------------------------------------------------
    def _show_toast(self, text: str, duration: float = 2.0) -> None:
        self._toast = text
        self._toast_t = duration

    # -- draw ----------------------------------------------------------------
    def draw(self, renderer) -> None:
        renderer.camera = self.camera
        self.world.tilemap.draw(renderer, self.camera)
        self.render_system.draw(self.world, renderer)
        self._draw_hud(renderer)
        if self.transition is not None:
            self.transition.draw(renderer)

    def _draw_hud(self, renderer) -> None:
        s = self.style
        g = self.game
        bw, bh = renderer.base_size

        # Player HP + level (top-left).
        if self.player.has("health"):
            hp = self.player.get("health")
            self.hpbar.draw(renderer, 6, 12, hp.fraction,
                            label=f"Lv{g.state.player['level']}  HP {hp.hp}/{hp.max_hp}")

        # Location name (top-right).
        loc = self.world.tilemap.properties.get("display_name", self.world.tilemap.name)
        renderer.draw_text(loc, bw - 6, 4, s.font, s.text_color,
                           layer="ui", world=False, anchor="topright")

        # Interaction prompt.
        if self._near_interactable:
            inter = self._near_interactable.get("interactable")
            renderer.draw_text(f"[E] {inter.prompt}", bw // 2, bh - 24, s.font,
                               s.highlight_color, layer="ui", world=False, anchor="center")

        # Toast.
        if self._toast_t > 0:
            renderer.draw_text(self._toast, bw // 2, 6, s.font, s.highlight_color,
                               layer="ui", world=False, anchor="center")

        # First-run controls hint.
        if not g.state.flags.get("seen_hint"):
            renderer.draw_text("WASD move  E interact  I items  Esc menu",
                               bw // 2, bh - 8, s.font, s.disabled_color,
                               layer="ui", world=False, anchor="center")
