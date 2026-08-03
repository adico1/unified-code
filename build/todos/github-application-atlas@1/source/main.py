"""Generated stateful application. Do not edit."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import webbrowser

APPLICATION_ID = 'uc://applications/github-application-atlas@1'
THING_STATES = ('unknown', 'absent', 'false', 'formed', 'valid', 'invalid')
TEN_DEPTHS = ('01_identity', '02_authority', '03_declaration', '04_composition', '05_processing', '06_state', '07_boundary', '08_manifestation', '09_evidence', '10_fixed_point')
INITIAL_STATE = {'filter': 'all', 'next_id': 8, 'observations': [{'archived': False, 'completed': True, 'id': 1, 'kind': 'measured-result', 'link': 'https://github.com/adico1/unified-code/blob/6499be3835e831d9c3b2a23c54f1436e978d52ed/seed/github_corpus/fixtures/EXPECTED.json', 'observed_ref': 'e69517fc5087b44f1541467bc619e484a4a16cf2121b6dd3c7938c93b0d160a4', 'observer': 'system', 'passed': 3, 'phase': 'measured-pass', 'progress': 100, 'temporal': 'past', 'title': 'Measured-pass offline GitHub corpus snapshot', 'total': 3, 'אדון_הכל': 'GUI, CLI and evidence expose the same snapshot.', 'הבט': 'The pinned fixture pack contains three acquired project records.', 'הבן': 'This is measured offline evidence, not a live GitHub view.', 'חקור': 'Acquisition is complete; fixture, request and evidence content identities are pinned.', 'מלך_עולם': 'fixtures/EXPECTED.json', 'ראה': 'The snapshot resolves to one immutable offline authority.'}, {'archived': False, 'completed': True, 'id': 2, 'kind': 'measured-result', 'link': 'https://github.com/adico1/unified-code/blob/6499be3835e831d9c3b2a23c54f1436e978d52ed/seed/github_corpus/candidates/EXPECTED.json', 'observed_ref': '24cd7584254a715590da4e0162904a36a1649ed179cc564fccf5750b2ef5487c', 'observer': 'system', 'passed': 2, 'phase': 'measured-pass', 'progress': 100, 'temporal': 'past', 'title': 'Canonical projects and extracted candidate declarations', 'total': 2, 'אדון_הכל': 'The Atlas projects counts, gaps and provenance.', 'הבט': 'Three canonical projects form three groups and two candidate declarations.', 'הבן': 'Counts are measured; open distinctions stay open.', 'חקור': 'Normalization a33cfe69ae715a984b09ae240c880ebeaf34b8691f8a559667fd5bec03a4b9eb records six open distinctions.', 'מלך_עולם': 'normalization/EXPECTED.json + candidates/EXPECTED.json', 'ראה': 'Relationships are canonicalized without approximate merging or ranking.'}, {'archived': False, 'completed': True, 'id': 3, 'kind': 'measured-result', 'link': 'https://github.com/adico1/unified-code/blob/6499be3835e831d9c3b2a23c54f1436e978d52ed/seed/github_corpus/holdout/EVALUATION.json', 'observed_ref': 'bc4a12032771aaaec094bec5240c66817a6fec19c9c71ae778461d60de58ded8', 'observer': 'system', 'passed': 7, 'phase': 'measured-pass', 'progress': 100, 'temporal': 'past', 'title': 'Accepted unseen holdout generated without compiler changes', 'total': 7, 'אדון_הכל': 'CLI and GUI project the same outcome.', 'הבט': 'The accepted holdout generated two byte-identical trees.', 'הבן': 'This proves one supported unseen example, not arbitrary applications.', 'חקור': 'Evaluation is generated-and-measured-pass; compiler identity stayed unchanged.', 'מלך_עולם': 'holdout/EVALUATION.json', 'ראה': 'Candidate and seed identities stay pinned to project 995929651.'}, {'archived': False, 'completed': False, 'id': 4, 'kind': 'open', 'link': 'https://github.com/adico1/unified-code/blob/6499be3835e831d9c3b2a23c54f1436e978d52ed/seed/github_corpus/holdout/EVALUATION.json', 'observed_ref': 'gap.unsupported-feature:application-language-without-backspace-control', 'observer': 'system', 'passed': 0, 'phase': 'standard.gap', 'progress': 0, 'temporal': 'present', 'title': 'Unsupported holdout remains an explicit Standard Ten gap', 'total': 1, 'אדון_הכל': 'The Atlas displays the open outcome.', 'הבט': 'Project 609855380 produced no accepted artifact.', 'הבן': 'Support requires a separately authorized language change.', 'חקור': 'Evaluation is standard.gap; no handwritten manual substitute was used.', 'מלך_עולם': 'holdout/EVALUATION.json', 'ראה': 'Unsupported stays distinct from measured-pass.'}, {'archived': False, 'completed': False, 'id': 5, 'kind': 'hypothesis', 'link': 'https://github.com/adico1/unified-code/issues/41', 'observed_ref': 'hypothesis:atlas-corpus-breadth@1', 'observer': 'architect', 'passed': 0, 'phase': 'research', 'progress': 0, 'temporal': 'present', 'title': 'Broader corpus coverage may expose new reusable distinctions', 'total': 1, 'אדון_הכל': 'The Atlas labels this as hypothesis.', 'הבט': 'No broader measured-pass corpus is present.', 'הבן': 'More pinned holdouts are required.', 'חקור': 'Current fixtures cannot establish prevalence or universal coverage.', 'מלך_עולם': 'Hypothesis only; no measured authority.', 'ראה': 'Hypothesis stays separate from measured counts.'}, {'archived': False, 'completed': False, 'id': 6, 'kind': 'plan', 'link': 'https://github.com/adico1/unified-code/issues/43', 'observed_ref': 'issue-43', 'observer': 'contributor', 'passed': 0, 'phase': 'OUTWARD-boundary', 'progress': 0, 'temporal': 'future', 'title': 'Implement the read-only live GitHub corpus adapter', 'total': 1, 'אדון_הכל': 'The queue links without acquiring.', 'הבט': 'Issue #43 exists; no live adapter exists here.', 'הבן': 'Contributors can implement the explicit boundary independently.', 'חקור': 'No network request is executed by this application.', 'מלך_עולם': 'GitHub Issue #43', 'ראה': 'Live acquisition remains outside the offline Atlas.'}, {'archived': False, 'completed': False, 'id': 7, 'kind': 'plan', 'link': 'https://github.com/adico1/unified-code/issues/41', 'observed_ref': 'issue-41', 'observer': 'contributor', 'passed': 0, 'phase': 'contributor-queue', 'progress': 0, 'temporal': 'future', 'title': 'Evaluate additional independently pinned application groups', 'total': 1, 'אדון_הכל': 'The queue exposes the next evidence task.', 'הבט': 'The research issue is open.', 'הבן': 'Add pinned evidence without inference or approximate merging.', 'חקור': 'No result is counted before evidence exists.', 'מלך_עולם': 'GitHub Issue #41', 'ראה': 'Future holdouts preserve all identities.'}]}
COLLECTION_FIELD = 'observations'
IDENTITY_FIELD = 'id'
DISPLAY_FIELDS = ['temporal', 'observer', 'phase', 'title', 'progress', 'kind', 'observed_ref', 'הבט', 'ראה', 'חקור', 'הבן', 'מלך_עולם', 'אדון_הכל', 'link']
TABLE_COLUMNS = [{'field': 'temporal', 'label': 'Time', 'width': 90}, {'field': 'observer', 'label': 'Observer', 'width': 100}, {'field': 'phase', 'label': 'SDLC phase', 'width': 120}, {'field': 'progress', 'label': 'Progress %', 'width': 90}, {'field': 'title', 'label': 'Development item', 'width': 360}]
DETAIL_FIELDS = [{'field': 'title', 'label': 'Development item'}, {'field': 'temporal', 'label': 'Time horizon'}, {'field': 'observer', 'label': 'Observer'}, {'field': 'phase', 'label': 'SDLC phase'}, {'field': 'progress', 'label': 'Measured progress (%)'}, {'field': 'הבט', 'label': 'Physical presence — הבט'}, {'field': 'ראה', 'label': 'Identity and relation — ראה'}, {'field': 'חקור', 'label': 'Measured evidence — חקור'}, {'field': 'הבן', 'label': 'Meaning and next decision — הבן'}, {'field': 'מלך_עולם', 'label': 'Canonical authority — מלך_עולם'}, {'field': 'אדון_הכל', 'label': 'Manifested projections — אדון_הכל'}, {'field': 'observed_ref', 'label': 'Evidence identity'}, {'field': 'link', 'label': 'Related code or issue'}]
OBSERVATION_METRICS = [{'label': 'acquisition status', 'value': 'complete (offline fixture)'}, {'label': 'snapshot projects', 'value': '3'}, {'label': 'candidate declarations', 'value': '2'}, {'label': 'open distinctions', 'value': '6'}, {'label': 'holdout evaluations', 'value': '1 measured-pass / 1 standard.gap'}]
PORTFOLIO_COLUMNS = [{'field': 'group', 'label': 'Boundary', 'width': 150}, {'field': 'product', 'label': 'Contributor task', 'width': 300}, {'field': 'identity', 'label': 'Canonical issue', 'width': 520}, {'field': 'status', 'label': 'State', 'width': 130}]
PORTFOLIO_RECORDS = [{'group': 'OUTWARD', 'identity': 'https://github.com/adico1/unified-code/issues/43', 'product': 'Read-only GitHub corpus adapter', 'status': 'future'}, {'group': 'RESEARCH', 'identity': 'https://github.com/adico1/unified-code/issues/41', 'product': 'Independent holdout groups', 'status': 'open'}]
FILTER_FIELD = 'filter'
FILTERS = {'all': None, 'completed': {'equals': True, 'field': 'completed'}, 'future': {'equals': 'future', 'field': 'temporal'}, 'open': {'equals': False, 'field': 'completed'}, 'past': {'equals': 'past', 'field': 'temporal'}, 'present': {'equals': 'present', 'field': 'temporal'}}
VISIBILITY = {'equals': False, 'field': 'archived'}
DEFAULT_STATE_PATH = '.unified-code/github-application-atlas/state.json'
STATE_ENVIRONMENT = 'UC_GITHUB_APPLICATION_ATLAS_STATE'
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
_open_url = webbrowser.open
def _confirm(*arguments, **options):
    from tkinter.messagebox import askyesno
    return askyesno(*arguments, **options)


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
    if not (isinstance(arguments['title'], str) and bool(arguments['title'].strip())):
        return _failure('invalid-request')
    if not all(not (record['title'] == arguments['title']) for record in state['observations']):
        return _failure('duplicate-request')
    state['observations'].append({'archived': False, 'completed': False, 'id': state['next_id'], 'kind': 'request', 'link': '', 'observed_ref': 'local-request', 'observer': 'user', 'passed': 0, 'phase': 'proposed', 'temporal': 'future', 'title': arguments['title'], 'total': 1, 'אדון_הכל': 'Requested application and API projections have not manifested.', 'הבט': 'A user request is stored in the local queue.', 'הבן': 'The user must authorize the external destination before delivery.', 'חקור': 'No external AI or GitHub delivery has been executed.', 'מלך_עולם': 'A future seed must declare the audited external delivery boundary.', 'ראה': 'The request is identified but not yet authorized for external delivery.', 'progress': ((0 * 100) // 1)})
    state['next_id'] += 1
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
    if not any(record['id'] == arguments['id'] for record in state['observations']):
        return _failure('unknown-observation')
    if not any(record['id'] == arguments['id'] and record['observer'] == 'user' for record in state['observations']):
        return _failure('protected-observation')
    for record in state['observations']:
        if record['id'] == arguments['id']:
            record['completed'] = (not record['completed'])
    persist_state()
    present_state()
    return _success()

def command_archive(arguments):
    if 'id' not in arguments:
        return _failure('missing-id')
    try:
        arguments['id'] = int(arguments['id'])
    except (TypeError, ValueError):
        return _failure('invalid-id')
    if not any(record['id'] == arguments['id'] for record in state['observations']):
        return _failure('unknown-observation')
    if not any(record['id'] == arguments['id'] and record['observer'] == 'user' for record in state['observations']):
        return _failure('protected-observation')
    for record in state['observations']:
        if record['id'] == arguments['id']:
            record['archived'] = True
    persist_state()
    present_state()
    return _success()

def command_set_filter(arguments):
    if 'mode' not in arguments:
        return _failure('missing-mode')
    state['filter'] = arguments['mode']
    present_state()
    return _success()

def command_open_link(arguments):
    if 'link' not in arguments:
        return _failure('missing-link')
    if not (isinstance(arguments['link'], str) and bool(arguments['link'].strip())):
        return _failure('link-absent')
    if not (isinstance(arguments['link'], str) and arguments['link'].startswith('https://')):
        return _failure('invalid-link')
    _open_url(arguments['link'])
    present_state()
    return _success()

COMMANDS = {
    'create': command_create,
    'toggle': command_toggle,
    'archive': command_archive,
    'set_filter': command_set_filter,
    'open_link': command_open_link,
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

def selected_record(identity):
    selected = _collections[identity].selection()
    return _record_by_row.get(selected[0]) if selected else None

def present_detail(identity):
    detail = _details[identity]
    record = selected_record(identity)
    detail.delete('1.0', 'end')
    detail.insert('1.0', '\n\n'.join(f'{item["label"]}\n{record[item["field"]]}' for item in DETAIL_FIELDS) if record else 'Select an observation')

def present_state():
    records = visible_records()
    _record_by_row.clear()
    for identity, widget in _collections.items():
        widget.delete(*widget.get_children())
        for record in records:
            row = str(record[IDENTITY_FIELD])
            _record_by_row[row] = record
            widget.insert('', 'end', iid=row, values=tuple(record[column['field']] for column in TABLE_COLUMNS))
        if records:
            widget.selection_set(str(records[0][IDENTITY_FIELD]))
        present_detail(identity)
    if _summary is not None:
        _summary.set(f'{len(records)} shown / {len(state[COLLECTION_FIELD])} total · filter={state.get(FILTER_FIELD, "all")}')

def selected_value(identity, field):
    record = selected_record(identity)
    return record[field] if record else None

def control_0():
    global _last_outcome
    _last_outcome = command_create({'title': _inputs['entry.primary'].get()})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def control_1():
    global _last_outcome
    _last_outcome = command_toggle({'id': selected_value('collection.primary', 'id')})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def control_2():
    global _last_outcome
    _last_outcome = command_open_link({'link': selected_value('collection.primary', 'link')})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def control_3():
    global _last_outcome
    if not _confirm('Archive request?', 'The request will leave the active view but remain recoverable in persisted state.'):
        _last_outcome = _failure('confirmation-declined')
        _status.set(_last_outcome['error'])
        return _last_outcome
    _last_outcome = command_archive({'id': selected_value('collection.primary', 'id')})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def control_4():
    global _last_outcome
    _last_outcome = command_set_filter({'mode': 'all'})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def control_5():
    global _last_outcome
    _last_outcome = command_set_filter({'mode': 'past'})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def control_6():
    global _last_outcome
    _last_outcome = command_set_filter({'mode': 'present'})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def control_7():
    global _last_outcome
    _last_outcome = command_set_filter({'mode': 'future'})
    _status.set(_last_outcome['error'] or 'ok')
    return _last_outcome

def build_interface():
    global _root, _status, _summary, _portfolio, _tabs, Button, Entry, Frame, Label, Listbox, StringVar, Text, Tk
    from tkinter import Button, Entry, Frame, Label, Listbox, StringVar, Text, Tk
    global Notebook, Scrollbar, Treeview
    from tkinter.ttk import Notebook, Scrollbar, Treeview
    _inputs.clear()
    _collections.clear()
    _details.clear()
    _buttons.clear()
    _metric_cards.clear()
    _root = Tk()
    _root.title('GitHub Application Atlas — Measured-pass Offline Evidence')
    _root.geometry('1400x720+40+40')
    _root.columnconfigure(0, weight=1)
    _root.columnconfigure(1, weight=1)
    _root.columnconfigure(2, weight=1)
    _root.columnconfigure(3, weight=1)
    _root.rowconfigure(1, weight=1)
    Label(_root, text='Add contributor request').grid(row=0, column=0, sticky='w')
    _inputs['entry.primary'] = Entry(_root, width=80)
    _inputs['entry.primary'].grid(row=0, column=1, columnspan=3, sticky='ew')
    surface = Frame(_root, padx=12, pady=10)
    surface.grid(row=1, column=0, columnspan=4, sticky='nsew')
    surface.columnconfigure(0, weight=3)
    surface.columnconfigure(2, weight=2)
    surface.rowconfigure(3, weight=1)
    Label(surface, text='Measured-pass offline Atlas — measured results, gaps, hypotheses and plans', font=('Helvetica', 18, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 4))
    _summary = StringVar(value='')
    Label(surface, textvariable=_summary, foreground='#4a5568').grid(row=1, column=0, columnspan=3, sticky='w', pady=(0, 8))
    metrics = Frame(surface)
    metrics.grid(row=2, column=0, columnspan=3, sticky='ew', pady=(0, 10))
    for index, metric in enumerate(OBSERVATION_METRICS):
        metrics.columnconfigure(index, weight=1)
        card = Frame(metrics, highlightbackground='#cbd5e0', highlightthickness=1, padx=12, pady=8)
        card.grid(row=0, column=index, sticky='nsew', padx=(0, 8))
        _metric_cards[metric['label']] = card
        Label(card, text=metric['value'], font=('Helvetica', 18, 'bold')).pack(anchor='w')
        Label(card, text=metric['label'], foreground='#4a5568').pack(anchor='w')
    _tabs = Notebook(surface)
    _tabs.grid(row=3, column=0, columnspan=3, sticky='nsew')
    overview_surface = Frame(_tabs)
    overview_surface.columnconfigure(0, weight=3)
    overview_surface.columnconfigure(2, weight=2)
    overview_surface.rowconfigure(0, weight=1)
    portfolio_surface = Frame(_tabs)
    portfolio_surface.columnconfigure(0, weight=1)
    portfolio_surface.rowconfigure(0, weight=1)
    _tabs.add(overview_surface, text='Measured-pass offline evidence')
    _tabs.add(portfolio_surface, text='Contributor queues')
    _collections['collection.primary'] = Treeview(overview_surface, columns=tuple(column['field'] for column in TABLE_COLUMNS), show='headings', selectmode='browse')
    table_widget = _collections['collection.primary']
    for column in TABLE_COLUMNS:
        table_widget.heading(column['field'], text=column['label'])
        table_widget.column(column['field'], width=column['width'], minwidth=70, stretch=True)
    table_widget.grid(row=0, column=0, sticky='nsew')
    table_scroll = Scrollbar(overview_surface, orient='vertical', command=table_widget.yview)
    table_scroll.grid(row=0, column=1, sticky='ns')
    table_widget.configure(yscrollcommand=table_scroll.set)
    _details['collection.primary'] = Text(overview_surface, width=46, wrap='word', padx=12, pady=10)
    _details['collection.primary'].grid(row=0, column=2, sticky='nsew', padx=(12, 0))
    _details['collection.primary'].bind('<Key>', lambda _event: 'break')
    table_widget.bind('<<TreeviewSelect>>', lambda _event: present_detail('collection.primary'))
    _portfolio = Treeview(portfolio_surface, columns=tuple(column['field'] for column in PORTFOLIO_COLUMNS), show='headings')
    for column in PORTFOLIO_COLUMNS:
        _portfolio.heading(column['field'], text=column['label'])
        _portfolio.column(column['field'], width=column['width'], minwidth=80, stretch=True)
    for index, record in enumerate(PORTFOLIO_RECORDS):
        _portfolio.insert('', 'end', iid=str(index), values=tuple(record[column['field']] for column in PORTFOLIO_COLUMNS))
    _portfolio.grid(row=0, column=0, sticky='nsew')
    portfolio_scroll = Scrollbar(portfolio_surface, orient='vertical', command=_portfolio.yview)
    portfolio_scroll.grid(row=0, column=1, sticky='ns')
    _portfolio.configure(yscrollcommand=portfolio_scroll.set)
    _buttons['request.submit'] = Button(_root, text='Ask AI', command=control_0)
    _buttons['request.submit'].grid(row=2, column=0, sticky='nsew')
    _buttons['record.toggle'] = Button(_root, text='Complete / Reopen', command=control_1)
    _buttons['record.toggle'].grid(row=2, column=1, sticky='nsew')
    _buttons['link.open'] = Button(_root, text='Open Code', command=control_2)
    _buttons['link.open'].grid(row=2, column=2, sticky='nsew')
    _buttons['record.archive'] = Button(_root, text='Archive Request', command=control_3)
    _buttons['record.archive'].grid(row=2, column=3, sticky='nsew')
    _buttons['filter.all'] = Button(_root, text='All', command=control_4)
    _buttons['filter.all'].grid(row=3, column=0, sticky='nsew')
    _buttons['filter.past'] = Button(_root, text='Past', command=control_5)
    _buttons['filter.past'].grid(row=3, column=1, sticky='nsew')
    _buttons['filter.present'] = Button(_root, text='Present', command=control_6)
    _buttons['filter.present'].grid(row=3, column=2, sticky='nsew')
    _buttons['filter.future'] = Button(_root, text='Future', command=control_7)
    _buttons['filter.future'].grid(row=3, column=3, sticky='nsew')
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
    cases = [{'expected': {'results': [{'error': None, 'result': {'filter': 'all', 'next_id': 8, 'observations': [{'archived': False, 'completed': True, 'id': 1, 'kind': 'measured-result', 'link': 'https://github.com/adico1/unified-code/blob/6499be3835e831d9c3b2a23c54f1436e978d52ed/seed/github_corpus/fixtures/EXPECTED.json', 'observed_ref': 'e69517fc5087b44f1541467bc619e484a4a16cf2121b6dd3c7938c93b0d160a4', 'observer': 'system', 'passed': 3, 'phase': 'measured-pass', 'progress': 100, 'temporal': 'past', 'title': 'Measured-pass offline GitHub corpus snapshot', 'total': 3, 'אדון_הכל': 'GUI, CLI and evidence expose the same snapshot.', 'הבט': 'The pinned fixture pack contains three acquired project records.', 'הבן': 'This is measured offline evidence, not a live GitHub view.', 'חקור': 'Acquisition is complete; fixture, request and evidence content identities are pinned.', 'מלך_עולם': 'fixtures/EXPECTED.json', 'ראה': 'The snapshot resolves to one immutable offline authority.'}, {'archived': False, 'completed': True, 'id': 2, 'kind': 'measured-result', 'link': 'https://github.com/adico1/unified-code/blob/6499be3835e831d9c3b2a23c54f1436e978d52ed/seed/github_corpus/candidates/EXPECTED.json', 'observed_ref': '24cd7584254a715590da4e0162904a36a1649ed179cc564fccf5750b2ef5487c', 'observer': 'system', 'passed': 2, 'phase': 'measured-pass', 'progress': 100, 'temporal': 'past', 'title': 'Canonical projects and extracted candidate declarations', 'total': 2, 'אדון_הכל': 'The Atlas projects counts, gaps and provenance.', 'הבט': 'Three canonical projects form three groups and two candidate declarations.', 'הבן': 'Counts are measured; open distinctions stay open.', 'חקור': 'Normalization a33cfe69ae715a984b09ae240c880ebeaf34b8691f8a559667fd5bec03a4b9eb records six open distinctions.', 'מלך_עולם': 'normalization/EXPECTED.json + candidates/EXPECTED.json', 'ראה': 'Relationships are canonicalized without approximate merging or ranking.'}, {'archived': False, 'completed': True, 'id': 3, 'kind': 'measured-result', 'link': 'https://github.com/adico1/unified-code/blob/6499be3835e831d9c3b2a23c54f1436e978d52ed/seed/github_corpus/holdout/EVALUATION.json', 'observed_ref': 'bc4a12032771aaaec094bec5240c66817a6fec19c9c71ae778461d60de58ded8', 'observer': 'system', 'passed': 7, 'phase': 'measured-pass', 'progress': 100, 'temporal': 'past', 'title': 'Accepted unseen holdout generated without compiler changes', 'total': 7, 'אדון_הכל': 'CLI and GUI project the same outcome.', 'הבט': 'The accepted holdout generated two byte-identical trees.', 'הבן': 'This proves one supported unseen example, not arbitrary applications.', 'חקור': 'Evaluation is generated-and-measured-pass; compiler identity stayed unchanged.', 'מלך_עולם': 'holdout/EVALUATION.json', 'ראה': 'Candidate and seed identities stay pinned to project 995929651.'}, {'archived': False, 'completed': False, 'id': 4, 'kind': 'open', 'link': 'https://github.com/adico1/unified-code/blob/6499be3835e831d9c3b2a23c54f1436e978d52ed/seed/github_corpus/holdout/EVALUATION.json', 'observed_ref': 'gap.unsupported-feature:application-language-without-backspace-control', 'observer': 'system', 'passed': 0, 'phase': 'standard.gap', 'progress': 0, 'temporal': 'present', 'title': 'Unsupported holdout remains an explicit Standard Ten gap', 'total': 1, 'אדון_הכל': 'The Atlas displays the open outcome.', 'הבט': 'Project 609855380 produced no accepted artifact.', 'הבן': 'Support requires a separately authorized language change.', 'חקור': 'Evaluation is standard.gap; no handwritten manual substitute was used.', 'מלך_עולם': 'holdout/EVALUATION.json', 'ראה': 'Unsupported stays distinct from measured-pass.'}, {'archived': False, 'completed': False, 'id': 5, 'kind': 'hypothesis', 'link': 'https://github.com/adico1/unified-code/issues/41', 'observed_ref': 'hypothesis:atlas-corpus-breadth@1', 'observer': 'architect', 'passed': 0, 'phase': 'research', 'progress': 0, 'temporal': 'present', 'title': 'Broader corpus coverage may expose new reusable distinctions', 'total': 1, 'אדון_הכל': 'The Atlas labels this as hypothesis.', 'הבט': 'No broader measured-pass corpus is present.', 'הבן': 'More pinned holdouts are required.', 'חקור': 'Current fixtures cannot establish prevalence or universal coverage.', 'מלך_עולם': 'Hypothesis only; no measured authority.', 'ראה': 'Hypothesis stays separate from measured counts.'}, {'archived': False, 'completed': False, 'id': 6, 'kind': 'plan', 'link': 'https://github.com/adico1/unified-code/issues/43', 'observed_ref': 'issue-43', 'observer': 'contributor', 'passed': 0, 'phase': 'OUTWARD-boundary', 'progress': 0, 'temporal': 'future', 'title': 'Implement the read-only live GitHub corpus adapter', 'total': 1, 'אדון_הכל': 'The queue links without acquiring.', 'הבט': 'Issue #43 exists; no live adapter exists here.', 'הבן': 'Contributors can implement the explicit boundary independently.', 'חקור': 'No network request is executed by this application.', 'מלך_עולם': 'GitHub Issue #43', 'ראה': 'Live acquisition remains outside the offline Atlas.'}, {'archived': False, 'completed': False, 'id': 7, 'kind': 'plan', 'link': 'https://github.com/adico1/unified-code/issues/41', 'observed_ref': 'issue-41', 'observer': 'contributor', 'passed': 0, 'phase': 'contributor-queue', 'progress': 0, 'temporal': 'future', 'title': 'Evaluate additional independently pinned application groups', 'total': 1, 'אדון_הכל': 'The queue exposes the next evidence task.', 'הבט': 'The research issue is open.', 'הבן': 'Add pinned evidence without inference or approximate merging.', 'חקור': 'No result is counted before evidence exists.', 'מלך_עולם': 'GitHub Issue #41', 'ראה': 'Future holdouts preserve all identities.'}]}}], 'state': {'filter': 'all', 'next_id': 8, 'observations': [{'archived': False, 'completed': True, 'id': 1, 'kind': 'measured-result', 'link': 'https://github.com/adico1/unified-code/blob/6499be3835e831d9c3b2a23c54f1436e978d52ed/seed/github_corpus/fixtures/EXPECTED.json', 'observed_ref': 'e69517fc5087b44f1541467bc619e484a4a16cf2121b6dd3c7938c93b0d160a4', 'observer': 'system', 'passed': 3, 'phase': 'measured-pass', 'progress': 100, 'temporal': 'past', 'title': 'Measured-pass offline GitHub corpus snapshot', 'total': 3, 'אדון_הכל': 'GUI, CLI and evidence expose the same snapshot.', 'הבט': 'The pinned fixture pack contains three acquired project records.', 'הבן': 'This is measured offline evidence, not a live GitHub view.', 'חקור': 'Acquisition is complete; fixture, request and evidence content identities are pinned.', 'מלך_עולם': 'fixtures/EXPECTED.json', 'ראה': 'The snapshot resolves to one immutable offline authority.'}, {'archived': False, 'completed': True, 'id': 2, 'kind': 'measured-result', 'link': 'https://github.com/adico1/unified-code/blob/6499be3835e831d9c3b2a23c54f1436e978d52ed/seed/github_corpus/candidates/EXPECTED.json', 'observed_ref': '24cd7584254a715590da4e0162904a36a1649ed179cc564fccf5750b2ef5487c', 'observer': 'system', 'passed': 2, 'phase': 'measured-pass', 'progress': 100, 'temporal': 'past', 'title': 'Canonical projects and extracted candidate declarations', 'total': 2, 'אדון_הכל': 'The Atlas projects counts, gaps and provenance.', 'הבט': 'Three canonical projects form three groups and two candidate declarations.', 'הבן': 'Counts are measured; open distinctions stay open.', 'חקור': 'Normalization a33cfe69ae715a984b09ae240c880ebeaf34b8691f8a559667fd5bec03a4b9eb records six open distinctions.', 'מלך_עולם': 'normalization/EXPECTED.json + candidates/EXPECTED.json', 'ראה': 'Relationships are canonicalized without approximate merging or ranking.'}, {'archived': False, 'completed': True, 'id': 3, 'kind': 'measured-result', 'link': 'https://github.com/adico1/unified-code/blob/6499be3835e831d9c3b2a23c54f1436e978d52ed/seed/github_corpus/holdout/EVALUATION.json', 'observed_ref': 'bc4a12032771aaaec094bec5240c66817a6fec19c9c71ae778461d60de58ded8', 'observer': 'system', 'passed': 7, 'phase': 'measured-pass', 'progress': 100, 'temporal': 'past', 'title': 'Accepted unseen holdout generated without compiler changes', 'total': 7, 'אדון_הכל': 'CLI and GUI project the same outcome.', 'הבט': 'The accepted holdout generated two byte-identical trees.', 'הבן': 'This proves one supported unseen example, not arbitrary applications.', 'חקור': 'Evaluation is generated-and-measured-pass; compiler identity stayed unchanged.', 'מלך_עולם': 'holdout/EVALUATION.json', 'ראה': 'Candidate and seed identities stay pinned to project 995929651.'}, {'archived': False, 'completed': False, 'id': 4, 'kind': 'open', 'link': 'https://github.com/adico1/unified-code/blob/6499be3835e831d9c3b2a23c54f1436e978d52ed/seed/github_corpus/holdout/EVALUATION.json', 'observed_ref': 'gap.unsupported-feature:application-language-without-backspace-control', 'observer': 'system', 'passed': 0, 'phase': 'standard.gap', 'progress': 0, 'temporal': 'present', 'title': 'Unsupported holdout remains an explicit Standard Ten gap', 'total': 1, 'אדון_הכל': 'The Atlas displays the open outcome.', 'הבט': 'Project 609855380 produced no accepted artifact.', 'הבן': 'Support requires a separately authorized language change.', 'חקור': 'Evaluation is standard.gap; no handwritten manual substitute was used.', 'מלך_עולם': 'holdout/EVALUATION.json', 'ראה': 'Unsupported stays distinct from measured-pass.'}, {'archived': False, 'completed': False, 'id': 5, 'kind': 'hypothesis', 'link': 'https://github.com/adico1/unified-code/issues/41', 'observed_ref': 'hypothesis:atlas-corpus-breadth@1', 'observer': 'architect', 'passed': 0, 'phase': 'research', 'progress': 0, 'temporal': 'present', 'title': 'Broader corpus coverage may expose new reusable distinctions', 'total': 1, 'אדון_הכל': 'The Atlas labels this as hypothesis.', 'הבט': 'No broader measured-pass corpus is present.', 'הבן': 'More pinned holdouts are required.', 'חקור': 'Current fixtures cannot establish prevalence or universal coverage.', 'מלך_עולם': 'Hypothesis only; no measured authority.', 'ראה': 'Hypothesis stays separate from measured counts.'}, {'archived': False, 'completed': False, 'id': 6, 'kind': 'plan', 'link': 'https://github.com/adico1/unified-code/issues/43', 'observed_ref': 'issue-43', 'observer': 'contributor', 'passed': 0, 'phase': 'OUTWARD-boundary', 'progress': 0, 'temporal': 'future', 'title': 'Implement the read-only live GitHub corpus adapter', 'total': 1, 'אדון_הכל': 'The queue links without acquiring.', 'הבט': 'Issue #43 exists; no live adapter exists here.', 'הבן': 'Contributors can implement the explicit boundary independently.', 'חקור': 'No network request is executed by this application.', 'מלך_עולם': 'GitHub Issue #43', 'ראה': 'Live acquisition remains outside the offline Atlas.'}, {'archived': False, 'completed': False, 'id': 7, 'kind': 'plan', 'link': 'https://github.com/adico1/unified-code/issues/41', 'observed_ref': 'issue-41', 'observer': 'contributor', 'passed': 0, 'phase': 'contributor-queue', 'progress': 0, 'temporal': 'future', 'title': 'Evaluate additional independently pinned application groups', 'total': 1, 'אדון_הכל': 'The queue exposes the next evidence task.', 'הבט': 'The research issue is open.', 'הבן': 'Add pinned evidence without inference or approximate merging.', 'חקור': 'No result is counted before evidence exists.', 'מלך_עולם': 'GitHub Issue #41', 'ראה': 'Future holdouts preserve all identities.'}]}}, 'id': 'github-application-atlas.offline-evidence', 'input': {'steps': [{'arguments': {'mode': 'all'}, 'command': 'set_filter'}]}}]
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
    global _state_path, _open_url, _confirm
    checks = []
    closed = False
    outward = []
    previous_state_path = _state_path
    previous_open_url = _open_url
    _open_url = outward.append
    previous_confirm = _confirm
    with tempfile.TemporaryDirectory(prefix='generated-stateful-gui-') as directory:
        configure_state_path(Path(directory) / 'state.json')
        root = build_interface()
        root.withdraw()
        table_widget = _collections['collection.primary']
        checks.append(tuple(table_widget['columns']) == tuple(column['field'] for column in TABLE_COLUMNS))
        checks.append(all(table_widget.heading(column['field'], 'text') == column['label'] for column in TABLE_COLUMNS))
        checks.append(tuple(_metric_cards) == tuple(metric['label'] for metric in OBSERVATION_METRICS))
        checks.append(len(_portfolio.get_children()) == len(PORTFOLIO_RECORDS))
        _tabs.select(1)
        checks.append(_tabs.index(_tabs.select()) == 1)
        _tabs.select(0)
        checks.append(bool(table_widget.get_children()) and bool(_details['collection.primary'].get('1.0', 'end').strip()))
        cases = [{'assertions': {'collection_count': 8, 'error': None, 'outward': [], 'record': {'fields': {'archived': False, 'completed': False, 'kind': 'request', 'observer': 'user', 'temporal': 'future'}, 'match': {'equals': 'Review another pinned project family', 'field': 'title'}, 'present': True}, 'state_fields': {'filter': 'all'}, 'visible_count': 8}, 'control': 'request.submit', 'id': 'request-queue', 'inputs': {'entry.primary': 'Review another pinned project family'}, 'restart': True}, {'assertions': {'collection_count': 7, 'error': 'protected-observation', 'outward': [], 'record': {'fields': {'completed': True, 'observed_ref': 'e69517fc5087b44f1541467bc619e484a4a16cf2121b6dd3c7938c93b0d160a4'}, 'match': {'equals': 1, 'field': 'id'}, 'present': True}, 'state_fields': {'filter': 'all'}, 'visible_count': 7}, 'control': 'record.toggle', 'id': 'protect-measured-result', 'selection': {'identity': 'collection.primary', 'index': 0}}, {'assertions': {'collection_count': 7, 'error': None, 'outward': ['https://github.com/adico1/unified-code/blob/6499be3835e831d9c3b2a23c54f1436e978d52ed/seed/github_corpus/fixtures/EXPECTED.json'], 'record': {'fields': {'kind': 'measured-result', 'observed_ref': 'e69517fc5087b44f1541467bc619e484a4a16cf2121b6dd3c7938c93b0d160a4'}, 'match': {'equals': 1, 'field': 'id'}, 'present': True}, 'state_fields': {'filter': 'all'}, 'visible_count': 7}, 'control': 'link.open', 'id': 'open-snapshot-provenance', 'selection': {'identity': 'collection.primary', 'index': 0}}, {'assertions': {'collection_count': 7, 'error': None, 'outward': [], 'record': None, 'state_fields': {'filter': 'past'}, 'visible_count': 3}, 'control': 'filter.past', 'id': 'filter-past'}, {'assertions': {'collection_count': 7, 'error': None, 'outward': [], 'record': None, 'state_fields': {'filter': 'present'}, 'visible_count': 2}, 'control': 'filter.present', 'id': 'filter-present'}, {'assertions': {'collection_count': 7, 'error': None, 'outward': [], 'record': None, 'state_fields': {'filter': 'future'}, 'visible_count': 2}, 'control': 'filter.future', 'id': 'filter-future'}]
        for case in cases:
            outward.clear()
            _confirm = lambda _title, _message: case.get('confirmation', True)
            reset_state()
            for setup in case.get('setup', ()):
                run_command(setup['command'], setup.get('arguments', {}))
            for identity, value in case.get('inputs', {}).items():
                _inputs[identity].delete(0, 'end')
                _inputs[identity].insert(0, value)
            present_state()
            if 'selection' in case:
                widget = _collections[case['selection']['identity']]
                widget.selection_remove(*widget.selection())
                widget.selection_set(widget.get_children()[case['selection']['index']])
            _buttons[case['control']].invoke()
            if case.get('restart'):
                state.clear()
                load_state()
            checks.append(verify_interface_assertions(case['assertions'], outward) if 'assertions' in case else _last_outcome == case['expected']['outcome'] and snapshot() == case['expected']['state'])
        root.destroy()
        _open_url = previous_open_url
        _confirm = previous_confirm
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
    if '--case-json' in sys.argv:
        position = sys.argv.index('--case-json')
        print(json.dumps(run_case(json.loads(sys.argv[position + 1])), sort_keys=True))
        return 0
    if '--self-test' in sys.argv:
        report = self_test_interface()
        print(json.dumps(report, sort_keys=True))
        return 0 if report['self_test']['passed'] == report['self_test']['total'] and report['closed'] else 1
    launch()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
