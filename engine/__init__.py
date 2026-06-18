"""
2D RPG Engine
=============
A flexible, data-driven, component-based foundation for building 2D RPGs with
Python + Pygame.

This top-level package contains ONLY reusable engine code. Game-specific content
lives in the sibling ``game/`` package and ``data/`` folder, so the whole
``engine/`` directory can be copied wholesale into a new project.

Sub-packages
------------
- ``engine.settings`` : central config access (no magic numbers anywhere else).
- ``engine.core``     : game loop, scene/state stack, event bus.
- ``engine.ecs``      : entity/component/system model + built-in components.
- ``engine.graphics`` : renderer abstraction, camera, layered draw, FX hooks.
- ``engine.map``      : Tiled map loading, multi-map world, portals, chunk stub.
- ``engine.assets``   : caching asset manager (images/audio/fonts/data).
- ``engine.input``    : remappable, config-driven input manager.
- ``engine.ui``       : reusable, resolution-aware UI widgets.
- ``engine.dialogue`` : branching, data-driven dialogue.
- ``engine.inventory``: data-driven items + inventory.
- ``engine.combat``   : swappable combat (turn-based example included).
- ``engine.save``     : full game-state serialization.
"""

__version__ = "0.1.0"
