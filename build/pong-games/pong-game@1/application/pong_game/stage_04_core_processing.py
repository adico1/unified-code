"""Generated application stage 04."""

from .runtime import advance

SPECIALIZATION = {'index': 4, 'name': '04_core_processing', 'program': {'engine': 'world', 'operations': {'transition': {'primitive': 'world_advance'}}, 'window': {'width': 800, 'height': 480}, 'field': {'width': 100, 'height': 60}, 'horizontal_roles': ['left', 'right'], 'controls': {'Space': {'event': 'start'}, 'KeyP': {'event': 'pause'}, 'KeyR': {'event': 'reset'}, 'ArrowUp': {'event': 'tick', 'ticks': 1, 'inputs': [{'actor': 'right', 'delta': -4}]}, 'ArrowDown': {'event': 'tick', 'ticks': 1, 'inputs': [{'actor': 'right', 'delta': 4}]}, 'KeyW': {'event': 'tick', 'ticks': 1, 'inputs': [{'actor': 'left', 'delta': -5}]}, 'KeyS': {'event': 'tick', 'ticks': 1, 'inputs': [{'actor': 'left', 'delta': 4}]}}, 'browser_proof': {'control_codes': ['Space', 'KeyW', 'KeyP'], 'expected_scenario': 'deterministic-replay', 'expected_step': 2, 'minimum_distinct_frames': 2}, 'presentation': {'background': '#05080f', 'foreground': '#ffffff'}, 'events': {'start': 'start', 'pause': 'pause', 'resume': 'resume', 'advance': 'tick', 'point': 'score', 'reset': 'reset', 'stop': 'stop'}, 'state_file': 'world-state.json', 'initial_state': {'active': False, 'tick': 0, 'actors': {'left': {'x': 2, 'y': 20, 'width': 4, 'height': 20}, 'right': {'x': 94, 'y': 0, 'width': 4, 'height': 2}}, 'mover': {'x': 98, 'y': 30, 'vx': 3, 'vy': 2, 'size': 2}, 'counters': {'left': 0, 'right': 0}}}, 'dependency': None, 'resolved_dependency_identity': None}


def part(thing):
    return advance({
        **thing,
        "value": {**thing["value"], "_specialization": SPECIALIZATION},
    })
