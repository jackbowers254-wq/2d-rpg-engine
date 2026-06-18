"""
AI behaviour selector.

Data-driven: ``behavior`` names a routine the AISystem knows ("idle", "wander",
"chase"), and ``params`` tunes it (wander radius, chase range, speed...). ``state``
is scratch space the routine uses at runtime. Add a new behaviour by registering
a handler in the AISystem -- entities opt in purely through data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from engine.ecs.component import Component, component


@component("ai")
@dataclass
class AIComponent(Component):
    behavior: str = "idle"
    params: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
