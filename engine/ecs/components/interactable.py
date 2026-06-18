"""
Marks an entity the player can interact with by pressing the 'interact' action
while facing/adjacent to it.

``action`` selects what happens (dispatched by the overworld scene / interaction
handling): "dialogue", "pickup", "sign", "battle", or a custom string you handle
yourself. ``params`` carries the specifics (which dialogue id, which item, etc.).
``prompt`` is the little hint shown when in range ("Talk", "Open", "Read").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from engine.ecs.component import Component, component


@component("interactable")
@dataclass
class InteractableComponent(Component):
    action: str = "dialogue"
    prompt: str = "Look"
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    radius: float = 14.0  # how close (centre-to-centre, px) counts as "in range"
