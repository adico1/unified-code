"""Generated stateful acceptance tests. Do not edit."""
import ast
import importlib.util
import json
from pathlib import Path

CASES = [{'id': 'costed-todo.calculated-persistence', 'input': {'steps': [{'arguments': {'quantity': 3, 'title': 'Steel', 'unit_price': 7}, 'command': 'create'}, {'arguments': {'quantity': 4, 'title': 'Wood', 'unit_price': 5}, 'command': 'create'}, {'arguments': {'id': 1, 'quantity': 6, 'title': 'Steel', 'unit_price': 7}, 'command': 'update'}, {'arguments': {'id': 2}, 'command': 'toggle'}, {'restart': True}]}, 'expected': {'results': [{'error': None, 'result': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'quantity': 3, 'title': 'Steel', 'total': 21, 'unit_price': 7}]}}, {'error': None, 'result': {'filter': 'all', 'next_id': 3, 'tasks': [{'completed': False, 'id': 1, 'quantity': 3, 'title': 'Steel', 'total': 21, 'unit_price': 7}, {'completed': False, 'id': 2, 'quantity': 4, 'title': 'Wood', 'total': 20, 'unit_price': 5}]}}, {'error': None, 'result': {'filter': 'all', 'next_id': 3, 'tasks': [{'completed': False, 'id': 1, 'quantity': 6, 'title': 'Steel', 'total': 42, 'unit_price': 7}, {'completed': False, 'id': 2, 'quantity': 4, 'title': 'Wood', 'total': 20, 'unit_price': 5}]}}, {'error': None, 'result': {'filter': 'all', 'next_id': 3, 'tasks': [{'completed': False, 'id': 1, 'quantity': 6, 'title': 'Steel', 'total': 42, 'unit_price': 7}, {'completed': True, 'id': 2, 'quantity': 4, 'title': 'Wood', 'total': 20, 'unit_price': 5}]}}, {'error': None, 'result': {'filter': 'all', 'next_id': 3, 'tasks': [{'completed': False, 'id': 1, 'quantity': 6, 'title': 'Steel', 'total': 42, 'unit_price': 7}, {'completed': True, 'id': 2, 'quantity': 4, 'title': 'Wood', 'total': 20, 'unit_price': 5}]}}], 'state': {'filter': 'all', 'next_id': 3, 'tasks': [{'completed': False, 'id': 1, 'quantity': 6, 'title': 'Steel', 'total': 42, 'unit_price': 7}, {'completed': True, 'id': 2, 'quantity': 4, 'title': 'Wood', 'total': 20, 'unit_price': 5}]}}}, {'id': 'costed-todo.bounded-calculation', 'input': {'steps': [{'arguments': {'quantity': -1, 'title': 'Low', 'unit_price': 1}, 'command': 'create'}, {'arguments': {'quantity': 1, 'title': 'High', 'unit_price': 1000001}, 'command': 'create'}, {'arguments': {'quantity': 1000000, 'title': 'Maximum', 'unit_price': 1000000}, 'command': 'create'}, {'arguments': {'quantity': 1, 'title': 'Maximum', 'unit_price': 1}, 'command': 'create'}]}, 'expected': {'results': [{'error': 'invalid-quantity-range', 'result': None}, {'error': 'invalid-unit-price-range', 'result': None}, {'error': None, 'result': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'quantity': 1000000, 'title': 'Maximum', 'total': 1000000000000, 'unit_price': 1000000}]}}, {'error': 'duplicate-title', 'result': None}], 'state': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'quantity': 1000000, 'title': 'Maximum', 'total': 1000000000000, 'unit_price': 1000000}]}}}]
EXPECTED_CALLBACKS = ['control_0', 'control_1', 'control_2', 'control_3', 'control_4', 'control_5', 'control_6']

def verify_callbacks(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    interface = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'build_interface')
    buttons = sorted((node for node in ast.walk(interface) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'Button'), key=lambda node: node.lineno)
    callbacks = []
    for button in buttons:
        command = next((item.value for item in button.keywords if item.arg == 'command'), None)
        callbacks.append(command.id if isinstance(command, ast.Name) else None)
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
