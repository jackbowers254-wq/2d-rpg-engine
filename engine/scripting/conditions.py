"""
engine.scripting.conditions
==========================
A tiny boolean condition language evaluated against the game state. Used by
triggers ("only run if...") and the ``if`` script action.

A condition is one of:
- ``null`` / missing            -> always true
- a string ``"flag_name"``      -> that flag is truthy
- ``{"flag": n, "value": v}``    -> flag n equals v (v defaults to "truthy")
- ``{"not": cond}``             -> negation
- ``{"all": [c, ...]}``          -> every sub-condition true
- ``{"any": [c, ...]}``          -> some sub-condition true
- ``{"has_item": id, "qty": n}`` -> inventory holds >= n (n defaults to 1)
- ``{"quest": id, "state": s}``  -> quest id is in state s (e.g. "active","done")
- ``{"var": name, "value": v}``  -> a script-local variable equals v

Everything is data, so designers gate cutscenes/dialogue on world state without code.
"""

from __future__ import annotations

from typing import Any


def check_condition(cond: Any, ctx) -> bool:
    if cond is None:
        return True
    if isinstance(cond, str):
        return bool(ctx.flags.get(cond))
    if isinstance(cond, list):  # bare list == "all"
        return all(check_condition(c, ctx) for c in cond)
    if not isinstance(cond, dict):
        return bool(cond)

    if "not" in cond:
        return not check_condition(cond["not"], ctx)
    if "all" in cond:
        return all(check_condition(c, ctx) for c in cond["all"])
    if "any" in cond:
        return any(check_condition(c, ctx) for c in cond["any"])
    if "flag" in cond:
        val = ctx.flags.get(cond["flag"])
        return (val == cond["value"]) if "value" in cond else bool(val)
    if "var" in cond:
        val = ctx.vars.get(cond["var"])
        return (val == cond["value"]) if "value" in cond else bool(val)
    if "has_item" in cond:
        inv = getattr(ctx.game.state, "inventory", None)
        return bool(inv) and inv.has(cond["has_item"], cond.get("qty", 1))
    if "quest" in cond:
        q = ctx.game.state.quests.get(cond["quest"], {})
        return q.get("state") == cond.get("state")
    return False
