"""
engine.core.events
===================
A minimal publish/subscribe event bus.

WHY THIS EXISTS
---------------
Systems should not call each other directly -- that creates tangled, hard to
swap modules. Instead they publish named events ("entity_died", "item_picked_up",
"map_changed", "dialogue_finished", ...) and any number of listeners react. This
keeps combat, UI, audio, quests, achievements, etc. decoupled: you can add a new
reaction to an event without touching the code that fires it.

This is deliberately tiny (no priorities, no async). It is an EXTENSION POINT:
swap in a more featureful bus later without changing publishers/subscribers.

Example
-------
    bus.subscribe("item_picked_up", lambda item: print("got", item))
    bus.publish("item_picked_up", item="potion")
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, DefaultDict, List

from engine.utils.logger import get_logger

log = get_logger("events")

# A listener takes arbitrary keyword args describing the event payload.
Listener = Callable[..., None]


class EventBus:
    def __init__(self) -> None:
        self._listeners: DefaultDict[str, List[Listener]] = defaultdict(list)

    def subscribe(self, event_name: str, listener: Listener) -> Callable[[], None]:
        """Register ``listener`` for ``event_name``.

        Returns an *unsubscribe* callable so callers can detach without keeping a
        reference to the original function.
        """
        self._listeners[event_name].append(listener)

        def _unsubscribe() -> None:
            self.unsubscribe(event_name, listener)

        return _unsubscribe

    def unsubscribe(self, event_name: str, listener: Listener) -> None:
        listeners = self._listeners.get(event_name)
        if listeners and listener in listeners:
            listeners.remove(listener)

    def publish(self, event_name: str, **payload: Any) -> None:
        """Synchronously notify all listeners of ``event_name``.

        Listener exceptions are caught and logged so one bad subscriber cannot
        crash the whole frame -- important for a foundation other people extend.
        """
        # Iterate over a copy: listeners may subscribe/unsubscribe during dispatch.
        for listener in list(self._listeners.get(event_name, ())):
            try:
                listener(**payload)
            except Exception:  # noqa: BLE001 - defensive: never let one listener kill the loop
                log.exception("Listener for '%s' raised", event_name)

    def clear(self) -> None:
        self._listeners.clear()
