"""
Concrete scenes for the demo. Registered by name in ``main.py`` so the engine
can switch between them. Each is a thin layer over engine systems:

- title     : main menu (New Game / Continue / Quit)
- overworld : the playable map -- world, entities, camera, HUD, interactions
- dialogue  : overlay that runs a DialogueSystem via a DialogueBox
- battle    : turn-based combat scene
- pause     : overlay menu (Resume / Save / Load / Inventory / Title)
- inventory : overlay item list (use / equip)
"""
