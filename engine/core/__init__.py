"""Core runtime: game loop, scene/state stack, and the global event bus."""

from engine.core.events import EventBus
from engine.core.scene import Scene
from engine.core.scene_manager import SceneManager

__all__ = ["EventBus", "Scene", "SceneManager"]
