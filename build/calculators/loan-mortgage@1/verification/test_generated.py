"""Generated acceptance tests. Do not edit."""
import ast
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

CASES = [{'id': 'loan-mortgage.1', 'input': {'expression': 'payment(1200,0,12)'}, 'expected': {'error': None, 'result': '100'}}, {'id': 'loan-mortgage.2', 'input': {'expression': 'payment(1000,0.01,10)'}, 'expected': {'error': None, 'result': '105.582076551171'}}, {'id': 'derived.division-by-zero', 'input': {'expression': '1/0'}, 'expected': {'result': None, 'error': 'division-by-zero'}}, {'id': 'derived.invalid-expression', 'input': {'expression': '('}, 'expected': {'result': None, 'error': 'invalid-expression'}}]
EXPECTED_CONTROLS = [{'identity': 'digit.7', 'label': '7', 'row': 2, 'column': 0, 'route': 'append', 'arguments': ['7']}, {'identity': 'digit.8', 'label': '8', 'row': 2, 'column': 1, 'route': 'append', 'arguments': ['8']}, {'identity': 'digit.9', 'label': '9', 'row': 2, 'column': 2, 'route': 'append', 'arguments': ['9']}, {'identity': 'operator.expression.divide', 'label': '÷', 'row': 2, 'column': 3, 'route': 'append', 'arguments': ['/']}, {'identity': 'digit.4', 'label': '4', 'row': 3, 'column': 0, 'route': 'append', 'arguments': ['4']}, {'identity': 'digit.5', 'label': '5', 'row': 3, 'column': 1, 'route': 'append', 'arguments': ['5']}, {'identity': 'digit.6', 'label': '6', 'row': 3, 'column': 2, 'route': 'append', 'arguments': ['6']}, {'identity': 'operator.expression.multiply', 'label': '×', 'row': 3, 'column': 3, 'route': 'append', 'arguments': ['*']}, {'identity': 'digit.1', 'label': '1', 'row': 4, 'column': 0, 'route': 'append', 'arguments': ['1']}, {'identity': 'digit.2', 'label': '2', 'row': 4, 'column': 1, 'route': 'append', 'arguments': ['2']}, {'identity': 'digit.3', 'label': '3', 'row': 4, 'column': 2, 'route': 'append', 'arguments': ['3']}, {'identity': 'operator.expression.subtract', 'label': '−', 'row': 4, 'column': 3, 'route': 'append', 'arguments': ['-']}, {'identity': 'digit.0', 'label': '0', 'row': 5, 'column': 0, 'route': 'append', 'arguments': ['0']}, {'identity': 'syntax.decimal', 'label': '.', 'row': 5, 'column': 1, 'route': 'append', 'arguments': ['.']}, {'identity': 'command.evaluate', 'label': '=', 'row': 5, 'column': 2, 'route': 'evaluate', 'arguments': []}, {'identity': 'operator.expression.add', 'label': '+', 'row': 5, 'column': 3, 'route': 'append', 'arguments': ['+']}, {'identity': 'syntax.left', 'label': '(', 'row': 6, 'column': 0, 'route': 'append', 'arguments': ['(']}, {'identity': 'syntax.right', 'label': ')', 'row': 6, 'column': 1, 'route': 'append', 'arguments': [')']}, {'identity': 'command.backspace', 'label': '⌫', 'row': 6, 'column': 2, 'route': 'backspace', 'arguments': []}, {'identity': 'command.clear.word', 'label': 'Clear', 'row': 6, 'column': 3, 'route': 'clear', 'arguments': []}]

def verify_key_callbacks(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    interface = functions['build_interface']
    buttons = [node for node in interface.body if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == 'grid' and isinstance(node.value.func.value, ast.Call) and isinstance(node.value.func.value.func, ast.Name) and node.value.func.value.func.id == 'Button']
    actual = []
    for button in buttons:
        construction = button.value.func.value
        keywords = {item.arg: item.value for item in construction.keywords}
        grid = {item.arg: item.value for item in button.value.keywords}
        command = next(item.value for item in construction.keywords if item.arg == 'command')
        if isinstance(command, ast.Name):
            route, arguments = command.id, []
            signature = len(functions[route].args.args) == 0
        elif isinstance(command, ast.Lambda) and isinstance(command.body, ast.Call) and isinstance(command.body.func, ast.Name) and len(command.args.args) == 1 and len(command.args.defaults) == 1 and len(command.body.args) == 1 and isinstance(command.body.args[0], ast.Name) and command.body.args[0].id == command.args.args[0].arg:
            route = command.body.func.id
            arguments = [ast.literal_eval(command.args.defaults[0])]
            signature = len(functions[route].args.args) == 1
        else:
            actual.append(None)
            continue
        actual.append({'label': ast.literal_eval(keywords['text']), 'row': ast.literal_eval(grid['row']), 'column': ast.literal_eval(grid['column']), 'route': route, 'arguments': arguments} if signature else None)
    expected = [{name: value for name, value in item.items() if name != 'identity'} for item in EXPECTED_CONTROLS]
    results = [left == right for left, right in zip(actual, expected)]
    all_valid = len(actual) == len(expected) and all(results)
    return {'passed': sum(results), 'total': len(expected), 'all_valid': all_valid}

def run(*, emit=True):
    local = Path(__file__).with_name('main.py')
    path = local if local.exists() else Path(__file__).parents[1] / 'application' / 'main.py'
    specification = importlib.util.spec_from_file_location('generated_app', path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    results = [module.run_case(case['input']) == case['expected'] for case in CASES]
    things = [module.part({'value': case['input'], 'depths': (), 'axes': (), 'evidence': (), 'state': 'formed'}) for case in CASES]
    thing_results = [thing['value'] == case['expected'] and thing['state'] == ({True: 'valid', False: 'invalid'}[case['expected'].get('error') is None]) and len(thing['depths']) == 10 and thing['evidence'] == ('boundary:inward', 'part:run_case', 'boundary:outward') for thing, case in zip(things, CASES)]
    display_value = ['']
    def display_get():
        return display_value[0]
    def display_set(value):
        display_value[0] = value
    module.display = SimpleNamespace(get=display_get, set=display_set)
    editable = []
    display_set('12')
    module.state['expression'] = ''
    module.append('3')
    editable.append(display_get() == '123' and module.state['expression'] == '123')
    display_set('456')
    module.state['expression'] = ''
    module.backspace()
    editable.append(display_get() == '45' and module.state['expression'] == '45')
    display_set('7')
    module.state['expression'] = ''
    module.evaluate()
    editable.append(display_get() == '7' and module.state['expression'] == '7')
    key_callbacks = verify_key_callbacks(path)
    report = {'passed': sum(results), 'total': len(results), 'cases': [case['id'] for case in CASES], 'things': {'passed': sum(thing_results), 'total': len(thing_results)}, 'editable': {'passed': sum(editable), 'total': len(editable)}, 'key_callbacks': {'passed': key_callbacks['passed'], 'total': key_callbacks['total']}}
    if emit:
        print(json.dumps(report, sort_keys=True))
    return 0 if all((*results, *thing_results, *editable)) and key_callbacks['all_valid'] else 1

if __name__ == '__main__':
    raise SystemExit(run())
