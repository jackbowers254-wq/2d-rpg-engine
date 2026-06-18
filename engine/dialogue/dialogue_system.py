"""
engine.dialogue.dialogue_system
==============================
A branching dialogue *state machine*. Conversations are pure DATA
(``data/dialogue/*.json``); this class walks them. It knows nothing about
rendering -- a UI scene reads ``current`` and calls ``advance`` / ``choose``.

Data format
-----------
    {
      "start": "greet",
      "nodes": {
        "greet": {"speaker": "Villager", "text": "Welcome!", "next": "ask"},
        "ask":   {"speaker": "Villager", "text": "Seen the cave?",
                  "choices": [
                    {"text": "Yes", "next": "knows"},
                    {"text": "No",  "next": "tells", "set": {"told": true}},
                    {"text": "Bye", "next": null}        // null/missing => end
                  ]},
        ...
      }
    }

Per-node optional actions (applied when the node is entered):
- ``set``   : {flag: value, ...}     -> writes to the shared flags dict.
- ``give``  : "item_id" or [ids]      -> adds to the inventory (if provided).
- ``event`` : "event_name"            -> published on the event bus.

Choices may be CONDITIONAL on flags:
- ``requires``: flag (or {flag: value}) -> choice shown only if it matches.
- ``hide_if`` : flag                     -> choice hidden if the flag is truthy.

Conditions let one NPC react differently across visits -- real branching without
any code. The ``context`` (flags dict, inventory, event bus) is supplied by the
game so dialogue can affect the world.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from engine.data.schemas import DIALOGUE_SCHEMA
from engine.data.validation import DataError, validate
from engine.utils.logger import get_logger

log = get_logger("dialogue")


def validate_dialogue(data: dict, source: str) -> None:
    """Validate a dialogue file's shape AND its node references.

    Beyond the schema, this checks that ``start`` and every ``next`` (node and
    choice) point at a node that actually exists -- the most common dialogue bug.
    Raises :class:`DataError` listing every problem with its location.
    """
    errors = validate(data, DIALOGUE_SCHEMA)
    nodes = data.get("nodes", {}) if isinstance(data.get("nodes"), dict) else {}

    start = data.get("start")
    if start is not None and start not in nodes:
        errors.append(f"start: points at missing node '{start}'")

    for node_id, node in nodes.items():
        if not isinstance(node, dict):
            continue
        nxt = node.get("next")
        if nxt is not None and nxt not in nodes:
            errors.append(f"nodes.{node_id}.next: points at missing node '{nxt}'")
        for i, choice in enumerate(node.get("choices", []) or []):
            cnext = choice.get("next") if isinstance(choice, dict) else None
            if cnext is not None and cnext not in nodes:
                errors.append(
                    f"nodes.{node_id}.choices[{i}].next: missing node '{cnext}'")

    if errors:
        bullet = "\n  - ".join(errors)
        raise DataError(f"Invalid dialogue in {source}:\n  - {bullet}")


@dataclass
class DialogueChoice:
    text: str
    next: Optional[str] = None
    set: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DialogueNode:
    speaker: str
    text: str
    choices: List[DialogueChoice]
    raw: dict


class DialogueContext:
    """What dialogue is allowed to read/affect in the world."""

    def __init__(self, flags: Optional[Dict[str, Any]] = None,
                 inventory=None, events=None) -> None:
        self.flags: Dict[str, Any] = flags if flags is not None else {}
        self.inventory = inventory
        self.events = events


class DialogueSystem:
    def __init__(self, data: dict, context: Optional[DialogueContext] = None) -> None:
        self._nodes: Dict[str, dict] = data.get("nodes", {})
        self._start: Optional[str] = data.get("start")
        self.context = context or DialogueContext()
        self.current_id: Optional[str] = None
        self.finished: bool = False

    # -- lifecycle -----------------------------------------------------------
    def start(self) -> None:
        self.finished = False
        self._goto(self._start)

    def _goto(self, node_id: Optional[str]) -> None:
        self.current_id = node_id
        if node_id is None or node_id not in self._nodes:
            self.finished = True
            self.current_id = None
            if self.context.events:
                self.context.events.publish("dialogue_finished")
            return
        self._run_actions(self._nodes[node_id])

    def _run_actions(self, node: dict) -> None:
        for flag, value in node.get("set", {}).items():
            self.context.flags[flag] = value
        give = node.get("give")
        if give and self.context.inventory is not None:
            for item_id in ([give] if isinstance(give, str) else give):
                self.context.inventory.add(item_id, 1)
        if node.get("event") and self.context.events is not None:
            self.context.events.publish(node["event"])

    # -- reading -------------------------------------------------------------
    @property
    def current(self) -> Optional[DialogueNode]:
        if self.current_id is None:
            return None
        raw = self._nodes[self.current_id]
        return DialogueNode(
            speaker=raw.get("speaker", ""),
            text=raw.get("text", ""),
            choices=self._visible_choices(raw),
            raw=raw,
        )

    def _visible_choices(self, raw: dict) -> List[DialogueChoice]:
        out: List[DialogueChoice] = []
        for c in raw.get("choices", []):
            if not self._choice_visible(c):
                continue
            out.append(DialogueChoice(
                text=c.get("text", "..."),
                next=c.get("next"),
                set=c.get("set", {}),
            ))
        return out

    def _choice_visible(self, c: dict) -> bool:
        flags = self.context.flags
        req = c.get("requires")
        if isinstance(req, str) and not flags.get(req):
            return False
        if isinstance(req, dict) and any(flags.get(k) != v for k, v in req.items()):
            return False
        hide = c.get("hide_if")
        if isinstance(hide, str) and flags.get(hide):
            return False
        return True

    # -- advancing -----------------------------------------------------------
    def advance(self) -> None:
        """Advance a node that has no choices (linear ``next``)."""
        if self.current_id is None:
            return
        raw = self._nodes[self.current_id]
        if raw.get("choices"):
            return  # caller must use choose() instead
        self._goto(raw.get("next"))

    def choose(self, index: int) -> None:
        """Pick a visible choice by index."""
        node = self.current
        if node is None or not node.choices:
            return
        if 0 <= index < len(node.choices):
            choice = node.choices[index]
            for flag, value in choice.set.items():
                self.context.flags[flag] = value
            self._goto(choice.next)
