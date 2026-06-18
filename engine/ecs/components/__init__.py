"""
Built-in components. Importing this package registers them all in
``COMPONENT_REGISTRY`` so the entity factory and save system can address them by
name. Add your own component module and import it here (or anywhere before the
factory runs) to make it data-addressable.
"""

from engine.ecs.components.ai import AIComponent
from engine.ecs.components.animation import AnimationComponent
from engine.ecs.components.collider import ColliderComponent
from engine.ecs.components.health import HealthComponent
from engine.ecs.components.interactable import InteractableComponent
from engine.ecs.components.movement import MovementComponent
from engine.ecs.components.sprite import SpriteComponent
from engine.ecs.components.stats import StatsComponent
from engine.ecs.components.tags import (
    AbilitiesComponent,
    PickupComponent,
    PlayerControlledComponent,
    PortalComponent,
)
from engine.ecs.components.transform import TransformComponent

__all__ = [
    "AIComponent",
    "AnimationComponent",
    "ColliderComponent",
    "HealthComponent",
    "InteractableComponent",
    "MovementComponent",
    "SpriteComponent",
    "StatsComponent",
    "AbilitiesComponent",
    "PickupComponent",
    "PlayerControlledComponent",
    "PortalComponent",
    "TransformComponent",
]
