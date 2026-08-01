"""Generated stateful application. Do not edit."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
from tkinter import Button, Entry, Frame, Label, Listbox, StringVar, Text, Tk

APPLICATION_ID = 'uc://applications/costed-todo@1'
THING_STATES = ('unknown', 'absent', 'false', 'formed', 'valid', 'invalid')
TEN_DEPTHS = ('01_identity', '02_authority', '03_declaration', '04_composition', '05_processing', '06_state', '07_boundary', '08_manifestation', '09_evidence', '10_fixed_point')
INITIAL_STATE = {'filter': 'all', 'next_id': 1, 'tasks': []}
COLLECTION_FIELD = 'tasks'
IDENTITY_FIELD = 'id'
DISPLAY_FIELDS = ['id', 'title', 'quantity', 'unit_price', 'total', 'completed']
FILTER_FIELD = 'filter'
FILTERS = {'all': None, 'completed': {'equals': True, 'field': 'completed'}, 'open': {'equals': False, 'field': 'completed'}}
VISIBILITY = None
DEFAULT_STATE_PATH = '.unified-code-manual/costed-todo/state.json'
STATE_ENVIRONMENT = 'UC_MANUAL_COSTED_TODO_STATE'
state = deepcopy(INITIAL_STATE)
_state_path = None
_root = None
_inputs = {}
_collections = {}
_details = {}
_record_by_row = {}
_buttons = {}
_metric_cards = {}
_portfolio = None
_tabs = None
_summary = None
_status = None
_last_outcome = None

def state_path():
    selected = os.environ.get(STATE_ENVIRONMENT)
    return Path(selected) if selected else Path.home() / DEFAULT_STATE_PATH

def configure_state_path(path):
    global _state_path
    _state_path = Path(path)

def active_state_path():
    return _state_path or state_path()

def snapshot():
    return deepcopy(state)

def reset_state():
    state.clear()
    state.update(deepcopy(INITIAL_STATE))
    present_state()

def persist_state():
    destination = active_state_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.' + destination.name + '-', dir=destination.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(state, stream, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            stream.write('\n')
        os.replace(temporary, destination)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise

def load_state():
    destination = active_state_path()
    loaded = json.loads(destination.read_text(encoding='utf-8')) if destination.exists() else deepcopy(INITIAL_STATE)
    state.clear()
    state.update(loaded)
    present_state()
    return snapshot()

def _success():
    return {'result': snapshot(), 'error': None}

def _failure(identity):
    return {'result': None, 'error': identity}

def _calculation_0(quantity, unit_price):
    return (quantity * unit_price)

def command_create(arguments):
    if 'title' not in arguments:
        return _failure('missing-title')
    if 'quantity' not in arguments:
        return _failure('missing-quantity')
    try:
        arguments['quantity'] = int(arguments['quantity'])
    except (TypeError, ValueError):
        return _failure('invalid-quantity')
    if 'unit_price' not in arguments:
        return _failure('missing-unit_price')
    try:
        arguments['unit_price'] = int(arguments['unit_price'])
    except (TypeError, ValueError):
        return _failure('invalid-unit_price')
    if not (isinstance(arguments['title'], str) and bool(arguments['title'].strip())):
        return _failure('invalid-title')
    if not (isinstance(arguments['quantity'], int) and 0 <= arguments['quantity'] <= 1000000):
        return _failure('invalid-quantity-range')
    if not (isinstance(arguments['unit_price'], int) and 0 <= arguments['unit_price'] <= 1000000):
        return _failure('invalid-unit-price-range')
    if not all(not (record['title'] == arguments['title']) for record in state['tasks']):
        return _failure('duplicate-title')
    state['tasks'].append({'completed': False, 'id': state['next_id'], 'quantity': arguments['quantity'], 'title': arguments['title'], 'total': _calculation_0(arguments['quantity'], arguments['unit_price']), 'unit_price': arguments['unit_price']})
    state['next_id'] += 1
    persist_state()
    present_state()
    return _success()

def command_update(arguments):
    if 'id' not in arguments:
        return _failure('missing-id')
    try:
        arguments['id'] = int(arguments['id'])
    except (TypeError, ValueError):
        return _failure('invalid-id')
    if 'title' not in arguments:
        return _failure('missing-title')
    if 'quantity' not in arguments:
        return _failure('missing-quantity')
    try:
        arguments['quantity'] = int(arguments['quantity'])
    except (TypeError, ValueError):
        return _failure('invalid-quantity')
    if 'unit_price' not in arguments:
        return _failure('missing-unit_price')
    try:
        arguments['unit_price'] = int(arguments['unit_price'])
    except (TypeError, ValueError):
        return _failure('invalid-unit_price')
    if not (isinstance(arguments['title'], str) and bool(arguments['title'].strip())):
        return _failure('invalid-title')
    if not (isinstance(arguments['quantity'], int) and 0 <= arguments['quantity'] <= 1000000):
        return _failure('invalid-quantity-range')
    if not (isinstance(arguments['unit_price'], int) and 0 <= arguments['unit_price'] <= 1000000):
        return _failure('invalid-unit-price-range')
    if not any(record['id'] == arguments['id'] for record in state['tasks']):
        return _failure('unknown-item')
    for record in state['tasks']:
        if record['id'] == arguments['id']:
            record['quantity'] = arguments['quantity']
            record['title'] = arguments['title']
            record['total'] = _calculation_0(arguments['quantity'], arguments['unit_price'])
            record['unit_price'] = arguments['unit_price']
    persist_state()
    present_state()
    return _success()

def command_toggle(arguments):
    if 'id' not in arguments:
        return _failure('missing-id')
    try:
        arguments['id'] = int(arguments['id'])
    except (TypeError, ValueError):
        return _failure('invalid-id')
    if not any(record['id'] == arguments['id'] for record in state['tasks']):
        return _failure('unknown-item')
    for record in state['tasks']:
        if record['id'] == arguments['id']:
            record['completed'] = (not record['completed'])
    persist_state()
    present_state()
    return _success()

def command_remove(arguments):
    if 'id' not in arguments:
        return _failure('missing-id')
    try:
        arguments['id'] = int(arguments['id'])
    except (TypeError, ValueError):
        return _failure('invalid-id')
    if not any(record['id'] == arguments['id'] for record in state['tasks']):
        return _failure('unknown-item')
    state['tasks'] = [
        record for record in state['tasks']
        if record['id'] != arguments['id']
    ]
    persist_state()
    present_state()
    return _success()

def command_set_filter(arguments):
    if 'mode' not in arguments:
        return _failure('missing-mode')
    state['filter'] = arguments['mode']
    persist_state()
    present_state()
    return _success()

COMMANDS = {
    'create': command_create,
    'update': command_update,
    'toggle': command_toggle,
    'remove': command_remove,
    'set_filter': command_set_filter,
}

def run_command(identity, arguments):
    operation = COMMANDS.get(identity)
    return operation(dict(arguments)) if operation else _failure('unknown-command')

def visible_records():
    records = list(state[COLLECTION_FIELD])
    if VISIBILITY:
        records = [record for record in records if record.get(VISIBILITY['field'], VISIBILITY['equals']) == VISIBILITY['equals']]
    selected = state.get(FILTER_FIELD) if FILTER_FIELD else None
    rule = FILTERS.get(selected)
    if not rule:
        return list(records)
    return [record for record in records if record[rule['field']] == rule['equals']]

def display_record(record):
    return ' · '.join(f'{field}={record[field]}' for field in DISPLAY_FIELDS)

def present_state():
    for identity, widget in _collections.items():
        widget.delete(0, 'end')
        for record in visible_records():
            widget.insert('end', display_record(record))

def selected_value(identity, field):
    widget = _collections[identity]
    selected = widget.curselection()
    if not selected:
        return None
    return visible_records()[selected[0]][field]

def control_0():
    global _last_outcome
    _last_outcome = command_create({'quantity': _inputs['entry.quantity'].get(), 'title': _inputs['entry.primary'].get(), 'unit_price': _inputs['entry.unit-price'].get()})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def control_1():
    global _last_outcome
    _last_outcome = command_update({'id': selected_value('collection.primary', 'id'), 'quantity': _inputs['entry.quantity'].get(), 'title': _inputs['entry.primary'].get(), 'unit_price': _inputs['entry.unit-price'].get()})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def control_2():
    global _last_outcome
    _last_outcome = command_toggle({'id': selected_value('collection.primary', 'id')})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def control_3():
    global _last_outcome
    _last_outcome = command_remove({'id': selected_value('collection.primary', 'id')})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def control_4():
    global _last_outcome
    _last_outcome = command_set_filter({'mode': 'all'})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def control_5():
    global _last_outcome
    _last_outcome = command_set_filter({'mode': 'open'})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def control_6():
    global _last_outcome
    _last_outcome = command_set_filter({'mode': 'completed'})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def build_interface():
    global _root, _status, _summary, _portfolio, _tabs
    _inputs.clear()
    _collections.clear()
    _details.clear()
    _buttons.clear()
    _metric_cards.clear()
    _root = Tk()
    _root.title('Costed Todo')
    _root.geometry('760x400+80+80')
    _root.columnconfigure(0, weight=1)
    _root.columnconfigure(1, weight=1)
    _root.columnconfigure(2, weight=1)
    _root.columnconfigure(3, weight=1)
    _root.rowconfigure(1, weight=1)
    Label(_root, text='Task').grid(row=0, column=0, sticky='w')
    _inputs['entry.primary'] = Entry(_root, width=30)
    _inputs['entry.primary'].grid(row=0, column=1, columnspan=3, sticky='ew')
    Label(_root, text='Quantity').grid(row=0, column=1, sticky='w')
    _inputs['entry.quantity'] = Entry(_root, width=12)
    _inputs['entry.quantity'].grid(row=0, column=2, columnspan=3, sticky='ew')
    Label(_root, text='Unit price').grid(row=0, column=2, sticky='w')
    _inputs['entry.unit-price'] = Entry(_root, width=12)
    _inputs['entry.unit-price'].grid(row=0, column=3, columnspan=2, sticky='ew')
    _collections['collection.primary'] = Listbox(_root, width=76, height=12)
    _collections['collection.primary'].grid(row=1, column=0, columnspan=4, sticky='nsew')
    _buttons['record.create'] = Button(_root, text='Add', command=control_0)
    _buttons['record.create'].grid(row=2, column=0, sticky='nsew')
    _buttons['record.update'] = Button(_root, text='Edit', command=control_1)
    _buttons['record.update'].grid(row=2, column=1, sticky='nsew')
    _buttons['record.toggle'] = Button(_root, text='Complete / Reopen', command=control_2)
    _buttons['record.toggle'].grid(row=2, column=2, sticky='nsew')
    _buttons['record.remove'] = Button(_root, text='Delete', command=control_3)
    _buttons['record.remove'].grid(row=2, column=3, sticky='nsew')
    _buttons['filter.all'] = Button(_root, text='All', command=control_4)
    _buttons['filter.all'].grid(row=3, column=0, sticky='nsew')
    _buttons['filter.open'] = Button(_root, text='Open', command=control_5)
    _buttons['filter.open'].grid(row=3, column=1, sticky='nsew')
    _buttons['filter.completed'] = Button(_root, text='Completed', command=control_6)
    _buttons['filter.completed'].grid(row=3, column=2, sticky='nsew')
    _status = StringVar(value='ready')
    Label(_root, textvariable=_status).grid(row=4, column=0, columnspan=4, sticky='w')
    present_state()
    return _root

def run_case(case):
    results = []
    with tempfile.TemporaryDirectory(prefix='generated-stateful-case-') as directory:
        configure_state_path(Path(directory) / 'state.json')
        reset_state()
        for step in case['steps']:
            if step.get('restart'):
                state.clear()
                results.append({'result': load_state(), 'error': None})
            else:
                results.append(run_command(step['command'], step.get('arguments', {})))
        return {'results': results, 'state': snapshot()}

def part(thing):
    result = run_case(thing['value'])
    return {'value': result, 'depths': TEN_DEPTHS, 'axes': tuple(thing.get('axes', ())), 'evidence': tuple(thing.get('evidence', ())) + ('boundary:inward', 'part:run_case', 'boundary:outward'), 'state': 'valid'}

def run_acceptance():
    cases = [{'expected': {'results': [{'error': None, 'result': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'quantity': 3, 'title': 'Steel', 'total': 21, 'unit_price': 7}]}}, {'error': None, 'result': {'filter': 'all', 'next_id': 3, 'tasks': [{'completed': False, 'id': 1, 'quantity': 3, 'title': 'Steel', 'total': 21, 'unit_price': 7}, {'completed': False, 'id': 2, 'quantity': 4, 'title': 'Wood', 'total': 20, 'unit_price': 5}]}}, {'error': None, 'result': {'filter': 'all', 'next_id': 3, 'tasks': [{'completed': False, 'id': 1, 'quantity': 6, 'title': 'Steel', 'total': 42, 'unit_price': 7}, {'completed': False, 'id': 2, 'quantity': 4, 'title': 'Wood', 'total': 20, 'unit_price': 5}]}}, {'error': None, 'result': {'filter': 'all', 'next_id': 3, 'tasks': [{'completed': False, 'id': 1, 'quantity': 6, 'title': 'Steel', 'total': 42, 'unit_price': 7}, {'completed': True, 'id': 2, 'quantity': 4, 'title': 'Wood', 'total': 20, 'unit_price': 5}]}}, {'error': None, 'result': {'filter': 'all', 'next_id': 3, 'tasks': [{'completed': False, 'id': 1, 'quantity': 6, 'title': 'Steel', 'total': 42, 'unit_price': 7}, {'completed': True, 'id': 2, 'quantity': 4, 'title': 'Wood', 'total': 20, 'unit_price': 5}]}}], 'state': {'filter': 'all', 'next_id': 3, 'tasks': [{'completed': False, 'id': 1, 'quantity': 6, 'title': 'Steel', 'total': 42, 'unit_price': 7}, {'completed': True, 'id': 2, 'quantity': 4, 'title': 'Wood', 'total': 20, 'unit_price': 5}]}}, 'id': 'costed-todo.calculated-persistence', 'input': {'steps': [{'arguments': {'quantity': 3, 'title': 'Steel', 'unit_price': 7}, 'command': 'create'}, {'arguments': {'quantity': 4, 'title': 'Wood', 'unit_price': 5}, 'command': 'create'}, {'arguments': {'id': 1, 'quantity': 6, 'title': 'Steel', 'unit_price': 7}, 'command': 'update'}, {'arguments': {'id': 2}, 'command': 'toggle'}, {'restart': True}]}}, {'expected': {'results': [{'error': 'invalid-quantity-range', 'result': None}, {'error': 'invalid-unit-price-range', 'result': None}, {'error': None, 'result': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'quantity': 1000000, 'title': 'Maximum', 'total': 1000000000000, 'unit_price': 1000000}]}}, {'error': 'duplicate-title', 'result': None}], 'state': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'quantity': 1000000, 'title': 'Maximum', 'total': 1000000000000, 'unit_price': 1000000}]}}, 'id': 'costed-todo.bounded-calculation', 'input': {'steps': [{'arguments': {'quantity': -1, 'title': 'Low', 'unit_price': 1}, 'command': 'create'}, {'arguments': {'quantity': 1, 'title': 'High', 'unit_price': 1000001}, 'command': 'create'}, {'arguments': {'quantity': 1000000, 'title': 'Maximum', 'unit_price': 1000000}, 'command': 'create'}, {'arguments': {'quantity': 1, 'title': 'Maximum', 'unit_price': 1}, 'command': 'create'}]}}]
    results = [run_case(case['input']) == case['expected'] for case in cases]
    return {'passed': sum(results), 'total': len(results), 'cases': [case['id'] for case in cases]}

def verify_interface_assertions(assertions, outward):
    checks = [
        _last_outcome['error'] == assertions['error'],
        len(state[COLLECTION_FIELD]) == assertions['collection_count'],
        len(visible_records()) == assertions['visible_count'],
        all(state.get(field) == value for field, value in assertions['state_fields'].items()),
        outward == assertions['outward'],
    ]
    rule = assertions['record']
    if rule is not None:
        matches = [record for record in state[COLLECTION_FIELD] if record.get(rule['match']['field']) == rule['match']['equals']]
        checks.append(bool(matches) == rule['present'])
        if rule['present'] and matches:
            checks.append(all(matches[0].get(field) == value for field, value in rule['fields'].items()))
    return all(checks)

def self_test_interface():
    global _state_path
    checks = []
    closed = False
    outward = []
    previous_state_path = _state_path
    with tempfile.TemporaryDirectory(prefix='generated-stateful-gui-') as directory:
        configure_state_path(Path(directory) / 'state.json')
        root = build_interface()
        root.withdraw()
        cases = [{'control': 'record.create', 'expected': {'outcome': {'error': None, 'result': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'quantity': 3, 'title': 'A', 'total': 21, 'unit_price': 7}]}}, 'state': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'quantity': 3, 'title': 'A', 'total': 21, 'unit_price': 7}]}}, 'inputs': {'entry.primary': 'A', 'entry.quantity': '3', 'entry.unit-price': '7'}}, {'control': 'record.update', 'expected': {'outcome': {'error': None, 'result': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'quantity': 9, 'title': 'B', 'total': 18, 'unit_price': 2}]}}, 'state': {'filter': 'all', 'next_id': 2, 'tasks': [{'completed': False, 'id': 1, 'quantity': 9, 'title': 'B', 'total': 18, 'unit_price': 2}]}}, 'inputs': {'entry.primary': 'B', 'entry.quantity': '9', 'entry.unit-price': '2'}, 'selection': {'identity': 'collection.primary', 'index': 0}, 'setup': [{'arguments': {'quantity': 1, 'title': 'A', 'unit_price': 1}, 'command': 'create'}]}]
        for case in cases:
            outward.clear()
            reset_state()
            for setup in case.get('setup', ()):
                run_command(setup['command'], setup.get('arguments', {}))
            for identity, value in case.get('inputs', {}).items():
                _inputs[identity].delete(0, 'end')
                _inputs[identity].insert(0, value)
            present_state()
            if 'selection' in case:
                widget = _collections[case['selection']['identity']]
                widget.selection_clear(0, 'end')
                widget.selection_set(case['selection']['index'])
            _buttons[case['control']].invoke()
            if case.get('restart'):
                state.clear()
                load_state()
            checks.append(verify_interface_assertions(case['assertions'], outward) if 'assertions' in case else _last_outcome == case['expected']['outcome'] and snapshot() == case['expected']['state'])
        root.destroy()
        _state_path = previous_state_path
        closed = True
    return {'self_test': {'passed': sum(checks), 'total': len(checks)}, 'interactions': [case.get('id', case['control']) for case in cases], 'closed': closed}

def launch():
    proof = self_test_interface()
    if proof['self_test']['passed'] != proof['self_test']['total']:
        raise RuntimeError('generated-self-test-failed')
    configure_state_path(state_path())
    root = build_interface()
    load_state()
    root.mainloop()

def main():
    if '--self-test' in sys.argv:
        report = self_test_interface()
        print(json.dumps(report, sort_keys=True))
        return 0 if report['self_test']['passed'] == report['self_test']['total'] and report['closed'] else 1
    launch()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
