"""
Small marker / data components.

PlayerControlledComponent  - the entity the player drives. The player controller
                             system reads input only for entities carrying it,
                             so you could even hand control to an NPC by moving
                             this component.
PickupComponent            - an item lying in the world; walking over/interacting
                             grants ``item_id`` x ``quantity`` then removes it.
PortalComponent            - an entity-based map transition (alternative to map
                             object portals); steps onto it warp the player.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.ecs.component import Component, component


@component("player_controlled")
@dataclass
class PlayerControlledComponent(Component):
    enabled: bool = True


@component("pickup")
@dataclass
class PickupComponent(Component):
    item_id: str = ""
    quantity: int = 1
    auto: bool = False  # True = pick up on touch; False = on interact press


@component("portal")
@dataclass
class PortalComponent(Component):
    target_map: str = ""
    target_x: float = 0.0   # destination in tiles (converted to px by the scene)
    target_y: float = 0.0
    facing: str = "down"
