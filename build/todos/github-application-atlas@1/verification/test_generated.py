"""Generated stateful acceptance tests. Do not edit."""
import ast
import importlib.util
import json
from pathlib import Path

CASES = [{'id': 'github-application-atlas.snapshot', 'input': {'steps': [{'arguments': {'title': 'Pin immutable GitHub corpus snapshot'}, 'command': 'create'}]}, 'expected': {'results': [{'error': None, 'result': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'title': 'Pin immutable GitHub corpus snapshot'}]}}], 'state': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'title': 'Pin immutable GitHub corpus snapshot'}]}}}, {'id': 'github-application-atlas.classification', 'input': {'steps': [{'arguments': {'title': 'Cluster GitHub projects and collapse mirrors'}, 'command': 'create'}]}, 'expected': {'results': [{'error': None, 'result': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'title': 'Cluster GitHub projects and collapse mirrors'}]}}], 'state': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'title': 'Cluster GitHub projects and collapse mirrors'}]}}}, {'id': 'github-application-atlas.extraction', 'input': {'steps': [{'arguments': {'title': 'Infer candidate Atlas declarations'}, 'command': 'create'}]}, 'expected': {'results': [{'error': None, 'result': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'title': 'Infer candidate Atlas declarations'}]}}], 'state': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'title': 'Infer candidate Atlas declarations'}]}}}, {'id': 'github-application-atlas.construction', 'input': {'steps': [{'arguments': {'title': 'Construct Atlas candidates through Unified Code'}, 'command': 'create'}]}, 'expected': {'results': [{'error': None, 'result': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'title': 'Construct Atlas candidates through Unified Code'}]}}], 'state': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'title': 'Construct Atlas candidates through Unified Code'}]}}}, {'id': 'github-application-atlas.holdout', 'input': {'steps': [{'arguments': {'title': 'Evaluate unseen holdout without creator changes'}, 'command': 'create'}]}, 'expected': {'results': [{'error': None, 'result': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'title': 'Evaluate unseen holdout without creator changes'}]}}], 'state': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'title': 'Evaluate unseen holdout without creator changes'}]}}}, {'id': 'github-application-atlas.publication', 'input': {'steps': [{'arguments': {'title': 'Expose searchable Atlas contributor queues'}, 'command': 'create'}]}, 'expected': {'results': [{'error': None, 'result': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'title': 'Expose searchable Atlas contributor queues'}]}}], 'state': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'title': 'Expose searchable Atlas contributor queues'}]}}}]
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
