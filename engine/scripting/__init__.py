"""
engine.scripting
==============
A DATA-DRIVEN event / trigger / scripting system -- the core of making different
kinds of games without engine code. You describe cutscenes and scripted logic as
JSON sequences of *actions*; *triggers* (placed in maps) decide when a script
runs.

Pieces:
- ``conditions`` : a small boolean language over flags / items / quests / vars,
  used by triggers and by the ``if`` action.
- ``script``     : the ScriptRunner -- a sequential interpreter where some actions
  block (dialogue, entity movement, battles, waits) and the rest are instant. It
  cooperates with the scene stack: when it shows dialogue/battle it pushes that
  scene and resumes when it closes.
- ``actions``    : the built-in action handlers (set_flag, give_item, move_entity,
  dialogue, start_battle, wait, face, teleport, play_music, emit, lock/unlock
  player, quest actions, ...). Register your own with ``@script_action("name")``.

See ``data/scripts/`` for examples and the README's "Event scripting" section.
"""

from engine.scripting.conditions import check_condition
from engine.scripting.script import (
    ScriptContext,
    ScriptRunner,
    SCRIPT_ACTIONS,
    Task,
    script_action,
)
import engine.scripting.actions as _actions  # noqa: F401  (registers built-ins)

__all__ = [
    "check_condition",
    "ScriptContext",
    "ScriptRunner",
    "SCRIPT_ACTIONS",
    "Task",
    "script_action",
]
