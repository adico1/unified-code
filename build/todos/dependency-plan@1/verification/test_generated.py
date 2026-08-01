"""Generated stateful acceptance tests. Do not edit."""
import ast
import importlib.util
import json
from pathlib import Path

CASES = [{'id': 'dependency-plan.lifecycle', 'input': {'steps': [{'arguments': {'blocked_state_field': 'blocked_state_field-value', 'critical_order_field': 'critical_order_field-value', 'dependency_edge_field': 'dependency_edge_field-value', 'title': 'A'}, 'command': 'create'}, {'arguments': {'id': 1}, 'command': 'toggle'}, {'restart': True}]}, 'expected': {'results': [{'error': None, 'result': {'filter': 'all', 'next_id': 2, 'records': [{'blocked_state_field': 'blocked_state_field-value', 'completed': False, 'critical_order_field': 'critical_order_field-value', 'dependency_edge_field': 'dependency_edge_field-value', 'id': 1, 'title': 'A'}]}}, {'error': None, 'result': {'filter': 'all', 'next_id': 2, 'records': [{'blocked_state_field': 'blocked_state_field-value', 'completed': True, 'critical_order_field': 'critical_order_field-value', 'dependency_edge_field': 'dependency_edge_field-value', 'id': 1, 'title': 'A'}]}}, {'error': None, 'result': {'filter': 'all', 'next_id': 2, 'records': [{'blocked_state_field': 'blocked_state_field-value', 'completed': True, 'critical_order_field': 'critical_order_field-value', 'dependency_edge_field': 'dependency_edge_field-value', 'id': 1, 'title': 'A'}]}}], 'state': {'filter': 'all', 'next_id': 2, 'records': [{'blocked_state_field': 'blocked_state_field-value', 'completed': True, 'critical_order_field': 'critical_order_field-value', 'dependency_edge_field': 'dependency_edge_field-value', 'id': 1, 'title': 'A'}]}}}]
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
