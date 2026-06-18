"""
engine.ecs
==========
A lightweight Entity-Component-System.

WHY ECS / COMPOSITION OVER INHERITANCE (a core requirement of the brief)
------------------------------------------------------------------------
Instead of a class tree (``Character -> NPC -> Merchant``) that gets rigid fast,
an *entity* is just an id plus a bag of *components* (pure data: Transform,
Sprite, Health, AI, Interactable, ...). *Systems* contain the behaviour and act
on every entity that has the components they care about. To make a new kind of
thing you mix components -- in DATA, not code:

    a chest      = Transform + Sprite + Interactable
    a slime      = Transform + Sprite + Movement + Collider + Health + AI + Stats
    a sign       = Transform + Sprite + Interactable
    a warp tile  = Transform + Collider(trigger) + Portal

Because components are registered by name, the entity factory builds any of these
straight from JSON (see ``game/factories/entity_factory.py`` and ``data/entities``).
"""

from engine.ecs.component import Component, component, COMPONENT_REGISTRY
from engine.ecs.entity import Entity
from engine.ecs.system import System
from engine.ecs.world import World

# Importing the components package triggers registration of all built-ins.
from engine.ecs import components as _components  # noqa: F401

__all__ = ["Component", "component", "COMPONENT_REGISTRY", "Entity", "System", "World"]
