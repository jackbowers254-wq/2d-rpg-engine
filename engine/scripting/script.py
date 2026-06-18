"""
engine.scripting.script
======================
The ScriptRunner interprets a list of action dicts in order. Most actions are
instant; some return a :class:`Task` that the runner ticks until it reports done
(movement, waits, dialogue, battles). This is what lets a cutscene read as a
simple data sequence while still spanning many frames and overlay scenes.

Scene-stack cooperation: a blocking action like ``dialogue`` pushes the dialogue
scene and waits for a ``dialogue_finished`` event. While that overlay is up, the
scene running the script is frozen (so its ``update`` -- and the runner -- pauses
automatically); when the overlay pops, the scene resumes and the task completes.
No threads, no coroutines exposed to data.

``ScriptContext`` is what actions act through: the game + its services, the active
world, the scene that started the script, a ``flags`` shortcut, and a ``vars``
scratchpad for script-local values.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from engine.scripting.conditions import check_condition
from engine.utils.logger import get_logger

log = get_logger("script")

# action name -> handler(ctx, params) -> Optional[Task]
SCRIPT_ACTIONS: Dict[str, Callable] = {}


def script_action(name: str):
    """Decorator registering a script action handler."""
    def _reg(fn):
        SCRIPT_ACTIONS[name] = fn
        return fn
    return _reg


class Task:
    """A blocking action's in-progress state. ``update`` returns True when done."""
    def update(self, dt: float) -> bool:  # pragma: no cover - interface
        return True


class ScriptContext:
    def __init__(self, game, world, scene) -> None:
        self.game = game
        self.world = world
        self.scene = scene
        self.flags = game.state.flags
        self.vars: Dict[str, Any] = {}
        self.source = None  # the trigger/entity that started the script (for "self")

    # -- target resolution ---------------------------------------------------
    def resolve(self, name: str):
        """Resolve a target name to an entity: 'player', 'self', or an entity by
        name / archetype / spawn id."""
        if name in ("player",):
            return self.world.player if self.world else None
        if name in ("self", "source"):
            return self.source
        if self.world is None:
            return None
        for e in self.world.entities:
            if e.name == name or e.type == name or e.has_tag(f"spawnid:{name}"):
                return e
            for tag in e.tags:
                if tag.startswith("spawnid:") and tag.split("/")[-1] == name:
                    return e
        return None


class _Frame:
    __slots__ = ("actions", "index")

    def __init__(self, actions: List[dict]) -> None:
        self.actions = actions
        self.index = 0


class ScriptRunner:
    def __init__(self, actions: List[dict], ctx: ScriptContext,
                 on_complete: Optional[Callable] = None) -> None:
        self.ctx = ctx
        self.on_complete = on_complete
        self._stack: List[_Frame] = [_Frame(actions or [])]
        self.task: Optional[Task] = None
        self.done = False

    def update(self, dt: float) -> None:
        if self.done:
            return
        if self.task is not None:
            if not self.task.update(dt):
                return
            self.task = None
        # Execute instant actions until one blocks or the script ends.
        guard = 0
        while self.task is None and not self.done:
            guard += 1
            if guard > 100000:  # safety against a malformed infinite script
                log.error("Script exceeded action budget; aborting")
                self._finish()
                return
            action = self._next()
            if action is None:
                self._finish()
                return
            self.task = self._exec(action)

    def _next(self) -> Optional[dict]:
        while self._stack:
            frame = self._stack[-1]
            if frame.index < len(frame.actions):
                action = frame.actions[frame.index]
                frame.index += 1
                return action
            self._stack.pop()
        return None

    def _exec(self, action: dict) -> Optional[Task]:
        name = action.get("action")
        if name == "if":
            branch = action.get("then" if check_condition(action.get("condition"), self.ctx)
                                else "else", [])
            if branch:
                self._stack.append(_Frame(branch))
            return None
        if name == "stop":
            self._stack.clear()
            return None
        handler = SCRIPT_ACTIONS.get(name)
        if handler is None:
            log.warning("Unknown script action '%s'", name)
            return None
        try:
            return handler(self.ctx, action)
        except Exception:  # noqa: BLE001 - a bad action shouldn't wedge the cutscene
            log.exception("Script action '%s' failed", name)
            return None

    def _finish(self) -> None:
        self.done = True
        if self.on_complete:
            self.on_complete()
