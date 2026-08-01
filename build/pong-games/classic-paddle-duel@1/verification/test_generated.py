"""Generated bounded-simulation tests. Do not edit."""
import ast
import importlib.util
import json
from pathlib import Path

CASES = [{'id': 'classic.motion', 'input': {'steps': [{'ticks': 1}]}, 'expected': {'entities': {'left-bat': {'height': 60, 'vx': 0, 'vy': 0, 'width': 10, 'x': 20, 'y': 90}, 'orb': {'height': 10, 'vx': 5, 'vy': 3, 'width': 10, 'x': 200, 'y': 118}, 'right-bat': {'height': 60, 'vx': 0, 'vy': 0, 'width': 10, 'x': 370, 'y': 90}}, 'left_score': 0, 'right_score': 0, 'status': 'playing', 'tick': 1}}, {'id': 'classic.control', 'input': {'steps': [{'control': 'participant.left.up'}]}, 'expected': {'entities': {'left-bat': {'height': 60, 'vx': 0, 'vy': 0, 'width': 10, 'x': 20, 'y': 72}, 'orb': {'height': 10, 'vx': 5, 'vy': 3, 'width': 10, 'x': 195, 'y': 115}, 'right-bat': {'height': 60, 'vx': 0, 'vy': 0, 'width': 10, 'x': 370, 'y': 90}}, 'left_score': 0, 'right_score': 0, 'status': 'playing', 'tick': 0}}]
EXPECTED_CALLBACKS = ['control_0', 'control_1', 'control_2', 'control_3']

def verify_callbacks(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    interface = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'build_interface')
    buttons = sorted((node for node in ast.walk(interface) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'Button'), key=lambda node: node.lineno)
    callbacks = [next(item.value for item in button.keywords if item.arg == 'command').id for button in buttons]
    results = [actual == expected and actual in functions for actual, expected in zip(callbacks, EXPECTED_CALLBACKS)]
    return {'passed': sum(results), 'total': len(EXPECTED_CALLBACKS), 'all_valid': len(callbacks) == len(EXPECTED_CALLBACKS) and all(results)}

def run(*, emit=True):
    local = Path(__file__).with_name('main.py')
    path = local if local.exists() else Path(__file__).parents[1] / 'application' / 'main.py'
    specification = importlib.util.spec_from_file_location('generated_app', path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    results = [module.run_case(case['input']) == case['expected'] for case in CASES]
    things = [module.part({'value': case['input'], 'depths': (), 'axes': (), 'evidence': (), 'state': 'formed'}) for case in CASES]
    thing_results = [thing['value'] == case['expected'] and thing['state'] == 'valid' and len(thing['depths']) == 10 and thing['evidence'] == ('boundary:inward', 'part:run_case', 'boundary:outward') for thing, case in zip(things, CASES)]
    callbacks = verify_callbacks(path)
    report = {'passed': sum(results), 'total': len(results), 'cases': [case['id'] for case in CASES], 'things': {'passed': sum(thing_results), 'total': len(thing_results)}, 'editable': {'passed': 0, 'total': 0}, 'key_callbacks': {'passed': callbacks['passed'], 'total': callbacks['total']}}
    if emit:
        print(json.dumps(report, sort_keys=True))
    return 0 if all((*results, *thing_results)) and callbacks['all_valid'] else 1

if __name__ == '__main__':
    raise SystemExit(run())
