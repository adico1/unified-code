"""Generated stateful application. Do not edit."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
from tkinter import Button, Entry, Frame, Label, Listbox, StringVar, Text, Tk

APPLICATION_ID = 'uc://applications/errands@1'
THING_STATES = ('unknown', 'absent', 'false', 'formed', 'valid', 'invalid')
TEN_DEPTHS = ('01_identity', '02_authority', '03_declaration', '04_composition', '05_processing', '06_state', '07_boundary', '08_manifestation', '09_evidence', '10_fixed_point')
INITIAL_STATE = {'filter': 'all', 'next_id': 1, 'records': []}
COLLECTION_FIELD = 'records'
IDENTITY_FIELD = 'id'
DISPLAY_FIELDS = ['id', 'title', 'location_field', 'route_order_field', 'completion_state_field', 'completed']
FILTER_FIELD = 'filter'
FILTERS = {'all': None, 'completed': {'equals': True, 'field': 'completed'}, 'open': {'equals': False, 'field': 'completed'}}
VISIBILITY = None
DEFAULT_STATE_PATH = '.unified-code-manual/errands/state.json'
STATE_ENVIRONMENT = 'UC_MANUAL_ERRANDS_STATE'
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

def command_create(arguments):
    if 'title' not in arguments:
        return _failure('missing-title')
    if 'location_field' not in arguments:
        return _failure('missing-location_field')
    if 'route_order_field' not in arguments:
        return _failure('missing-route_order_field')
    if 'completion_state_field' not in arguments:
        return _failure('missing-completion_state_field')
    if not (isinstance(arguments['title'], str) and bool(arguments['title'].strip())):
        return _failure('invalid-title')
    if not all(not (record['title'] == arguments['title']) for record in state['records']):
        return _failure('duplicate-title')
    state['records'].append({'completed': False, 'completion_state_field': arguments['completion_state_field'], 'id': state['next_id'], 'location_field': arguments['location_field'], 'route_order_field': arguments['route_order_field'], 'title': arguments['title']})
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
    if 'location_field' not in arguments:
        return _failure('missing-location_field')
    if 'route_order_field' not in arguments:
        return _failure('missing-route_order_field')
    if 'completion_state_field' not in arguments:
        return _failure('missing-completion_state_field')
    if not (isinstance(arguments['title'], str) and bool(arguments['title'].strip())):
        return _failure('invalid-title')
    if not any(record['id'] == arguments['id'] for record in state['records']):
        return _failure('unknown-item')
    for record in state['records']:
        if record['id'] == arguments['id']:
            record['completion_state_field'] = arguments['completion_state_field']
            record['location_field'] = arguments['location_field']
            record['route_order_field'] = arguments['route_order_field']
            record['title'] = arguments['title']
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
    if not any(record['id'] == arguments['id'] for record in state['records']):
        return _failure('unknown-item')
    for record in state['records']:
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
    if not any(record['id'] == arguments['id'] for record in state['records']):
        return _failure('unknown-item')
    state['records'] = [
        record for record in state['records']
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
    _last_outcome = command_create({'completion_state_field': _inputs['entry.completion_state_field'].get(), 'location_field': _inputs['entry.location_field'].get(), 'route_order_field': _inputs['entry.route_order_field'].get(), 'title': _inputs['entry.primary'].get()})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def control_1():
    global _last_outcome
    _last_outcome = command_update({'completion_state_field': _inputs['entry.completion_state_field'].get(), 'id': selected_value('collection.primary', 'id'), 'location_field': _inputs['entry.location_field'].get(), 'route_order_field': _inputs['entry.route_order_field'].get(), 'title': _inputs['entry.primary'].get()})
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
    _root.title('Errand list')
    _root.geometry('760x474+80+80')
    _root.columnconfigure(0, weight=1)
    _root.columnconfigure(1, weight=1)
    _root.columnconfigure(2, weight=1)
    _root.columnconfigure(3, weight=1)
    _root.rowconfigure(1, weight=1)
    Label(_root, text='Title').grid(row=0, column=0, sticky='w')
    _inputs['entry.primary'] = Entry(_root, width=38)
    _inputs['entry.primary'].grid(row=0, column=1, columnspan=3, sticky='ew')
    Label(_root, text='Location Field').grid(row=1, column=0, sticky='w')
    _inputs['entry.location_field'] = Entry(_root, width=38)
    _inputs['entry.location_field'].grid(row=1, column=1, columnspan=3, sticky='ew')
    Label(_root, text='Route Order Field').grid(row=2, column=0, sticky='w')
    _inputs['entry.route_order_field'] = Entry(_root, width=38)
    _inputs['entry.route_order_field'].grid(row=2, column=1, columnspan=3, sticky='ew')
    Label(_root, text='Completion State Field').grid(row=3, column=0, sticky='w')
    _inputs['entry.completion_state_field'] = Entry(_root, width=38)
    _inputs['entry.completion_state_field'].grid(row=3, column=1, columnspan=3, sticky='ew')
    _collections['collection.primary'] = Listbox(_root, width=82, height=12)
    _collections['collection.primary'].grid(row=4, column=0, columnspan=4, sticky='nsew')
    _buttons['record.create'] = Button(_root, text='Add', command=control_0)
    _buttons['record.create'].grid(row=5, column=0, sticky='nsew')
    _buttons['record.update'] = Button(_root, text='Edit', command=control_1)
    _buttons['record.update'].grid(row=5, column=1, sticky='nsew')
    _buttons['record.toggle'] = Button(_root, text='Complete / Reopen', command=control_2)
    _buttons['record.toggle'].grid(row=5, column=2, sticky='nsew')
    _buttons['record.remove'] = Button(_root, text='Delete', command=control_3)
    _buttons['record.remove'].grid(row=5, column=3, sticky='nsew')
    _buttons['filter.all'] = Button(_root, text='All', command=control_4)
    _buttons['filter.all'].grid(row=6, column=0, sticky='nsew')
    _buttons['filter.open'] = Button(_root, text='Open', command=control_5)
    _buttons['filter.open'].grid(row=6, column=1, sticky='nsew')
    _buttons['filter.completed'] = Button(_root, text='Completed', command=control_6)
    _buttons['filter.completed'].grid(row=6, column=2, sticky='nsew')
    _status = StringVar(value='ready')
    Label(_root, textvariable=_status).grid(row=7, column=0, columnspan=4, sticky='w')
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
    cases = [{'expected': {'results': [{'error': None, 'result': {'filter': 'all', 'next_id': 2, 'records': [{'completed': False, 'completion_state_field': 'completion_state_field-value', 'id': 1, 'location_field': 'location_field-value', 'route_order_field': 'route_order_field-value', 'title': 'A'}]}}, {'error': None, 'result': {'filter': 'all', 'next_id': 2, 'records': [{'completed': True, 'completion_state_field': 'completion_state_field-value', 'id': 1, 'location_field': 'location_field-value', 'route_order_field': 'route_order_field-value', 'title': 'A'}]}}, {'error': None, 'result': {'filter': 'all', 'next_id': 2, 'records': [{'completed': True, 'completion_state_field': 'completion_state_field-value', 'id': 1, 'location_field': 'location_field-value', 'route_order_field': 'route_order_field-value', 'title': 'A'}]}}], 'state': {'filter': 'all', 'next_id': 2, 'records': [{'completed': True, 'completion_state_field': 'completion_state_field-value', 'id': 1, 'location_field': 'location_field-value', 'route_order_field': 'route_order_field-value', 'title': 'A'}]}}, 'id': 'errands.lifecycle', 'input': {'steps': [{'arguments': {'completion_state_field': 'completion_state_field-value', 'location_field': 'location_field-value', 'route_order_field': 'route_order_field-value', 'title': 'A'}, 'command': 'create'}, {'arguments': {'id': 1}, 'command': 'toggle'}, {'restart': True}]}}]
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
        cases = [{'control': 'record.create', 'expected': {'outcome': {'error': None, 'result': {'filter': 'all', 'next_id': 2, 'records': [{'completed': False, 'completion_state_field': 'completion_state_field-value', 'id': 1, 'location_field': 'location_field-value', 'route_order_field': 'route_order_field-value', 'title': 'A'}]}}, 'state': {'filter': 'all', 'next_id': 2, 'records': [{'completed': False, 'completion_state_field': 'completion_state_field-value', 'id': 1, 'location_field': 'location_field-value', 'route_order_field': 'route_order_field-value', 'title': 'A'}]}}, 'inputs': {'entry.completion_state_field': 'completion_state_field-value', 'entry.location_field': 'location_field-value', 'entry.primary': 'A', 'entry.route_order_field': 'route_order_field-value'}}, {'control': 'record.update', 'expected': {'outcome': {'error': None, 'result': {'filter': 'all', 'next_id': 2, 'records': [{'completed': False, 'completion_state_field': 'completion_state_field-value', 'id': 1, 'location_field': 'location_field-value', 'route_order_field': 'route_order_field-value', 'title': 'B'}]}}, 'state': {'filter': 'all', 'next_id': 2, 'records': [{'completed': False, 'completion_state_field': 'completion_state_field-value', 'id': 1, 'location_field': 'location_field-value', 'route_order_field': 'route_order_field-value', 'title': 'B'}]}}, 'inputs': {'entry.completion_state_field': 'completion_state_field-value', 'entry.location_field': 'location_field-value', 'entry.primary': 'B', 'entry.route_order_field': 'route_order_field-value'}, 'selection': {'identity': 'collection.primary', 'index': 0}, 'setup': [{'arguments': {'completion_state_field': 'completion_state_field-value', 'location_field': 'location_field-value', 'route_order_field': 'route_order_field-value', 'title': 'A'}, 'command': 'create'}]}, {'control': 'record.toggle', 'expected': {'outcome': {'error': None, 'result': {'filter': 'all', 'next_id': 2, 'records': [{'completed': True, 'completion_state_field': 'completion_state_field-value', 'id': 1, 'location_field': 'location_field-value', 'route_order_field': 'route_order_field-value', 'title': 'A'}]}}, 'state': {'filter': 'all', 'next_id': 2, 'records': [{'completed': True, 'completion_state_field': 'completion_state_field-value', 'id': 1, 'location_field': 'location_field-value', 'route_order_field': 'route_order_field-value', 'title': 'A'}]}}, 'selection': {'identity': 'collection.primary', 'index': 0}, 'setup': [{'arguments': {'completion_state_field': 'completion_state_field-value', 'location_field': 'location_field-value', 'route_order_field': 'route_order_field-value', 'title': 'A'}, 'command': 'create'}]}, {'control': 'record.remove', 'expected': {'outcome': {'error': None, 'result': {'filter': 'all', 'next_id': 2, 'records': []}}, 'state': {'filter': 'all', 'next_id': 2, 'records': []}}, 'selection': {'identity': 'collection.primary', 'index': 0}, 'setup': [{'arguments': {'completion_state_field': 'completion_state_field-value', 'location_field': 'location_field-value', 'route_order_field': 'route_order_field-value', 'title': 'A'}, 'command': 'create'}]}, {'control': 'filter.all', 'expected': {'outcome': {'error': None, 'result': {'filter': 'all', 'next_id': 1, 'records': []}}, 'state': {'filter': 'all', 'next_id': 1, 'records': []}}}, {'control': 'filter.open', 'expected': {'outcome': {'error': None, 'result': {'filter': 'open', 'next_id': 1, 'records': []}}, 'state': {'filter': 'open', 'next_id': 1, 'records': []}}}, {'control': 'filter.completed', 'expected': {'outcome': {'error': None, 'result': {'filter': 'completed', 'next_id': 1, 'records': []}}, 'state': {'filter': 'completed', 'next_id': 1, 'records': []}}}]
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
