"""Generated stateful application. Do not edit."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import webbrowser

APPLICATION_ID = 'uc://applications/development-observatory@1'
THING_STATES = ('unknown', 'absent', 'false', 'formed', 'valid', 'invalid')
TEN_DEPTHS = ('01_identity', '02_authority', '03_declaration', '04_composition', '05_processing', '06_state', '07_boundary', '08_manifestation', '09_evidence', '10_fixed_point')
INITIAL_STATE = {'filter': 'all', 'next_id': 5, 'observations': [{'archived': False, 'completed': True, 'id': 1, 'kind': 'achievement', 'link': 'https://github.com/adico1/unified-code', 'observed_ref': '8933e8456b67375ec2b567c0107a64d9afc3c060', 'observer': 'system', 'passed': 13, 'phase': 'verified', 'temporal': 'past', 'title': 'Milestone 1 seed-to-application proof', 'total': 13, 'אדון_הכל': 'Manifested and verified: application, API and CLI.', 'הבט': 'A runnable generated application artifact exists.', 'הבן': 'This proves bounded seed-to-application generation, not root self-hosting.', 'חקור': 'Every L1-L13 verification gate passed.', 'מלך_עולם': 'The application seed is the verified canonical authority.', 'ראה': 'The seed and generated product resolve to one identity.', 'progress': 100}, {'archived': False, 'completed': False, 'id': 2, 'kind': 'review', 'link': 'https://github.com/adico1/unified-code-manual/blob/feature/development-observatory/src/stateful_compiler.py', 'observed_ref': 'uc://applications/development-observatory@1', 'observer': 'architect', 'passed': 292, 'phase': 'verification', 'temporal': 'present', 'title': 'Manual compiler: 74 products in four groups', 'total': 292, 'אדון_הכל': 'Manifested and verified: application, API and GUI.', 'הבט': 'A public review branch and pull request exist.', 'הבן': 'Review and merge the product-family dependency before this stacked change.', 'חקור': 'The complete local proof passed within the five-second law.', 'מלך_עולם': 'ROOT pins every current creator authority.', 'ראה': 'Every product identity is derived from registered seed data.', 'progress': 100}, {'archived': False, 'completed': False, 'id': 3, 'kind': 'gap', 'link': 'https://github.com/adico1/unified-code/issues/10', 'observed_ref': '4ee817a950e323614ff4215426391e6ebd2e5afc', 'observer': 'system', 'passed': 0, 'phase': 'blocked', 'temporal': 'present', 'title': 'ROOT creator is pinned but not root-generated', 'total': 1, 'אדון_הכל': 'Manifested: partial repository; the root-generated repository is absent.', 'הבט': 'The trusted creator exists as handwritten infrastructure.', 'הבן': 'The creator must still be generated from ROOT before Milestone 2 can close.', 'חקור': 'The repository-wide fixed-point proof remains open.', 'מלך_עולם': 'ROOT is pinned but does not yet generate its creator.', 'ראה': 'Authority remains divided between ROOT and handwritten creator code.', 'progress': 0}, {'archived': False, 'completed': False, 'id': 4, 'kind': 'direction', 'link': 'https://github.com/adico1/unified-code/issues/9', 'observed_ref': 'issue-9', 'observer': 'ai', 'passed': 0, 'phase': 'planned', 'temporal': 'future', 'title': 'Clean-room whole-repository fixed point', 'total': 1, 'אדון_הכל': 'No clean-room root-generated repository has manifested yet.', 'הבט': 'The clean-room integration issue and contract exist.', 'הבן': 'Begin only after dependency provenance and root generation are complete.', 'חקור': 'Acceptance is declared; the clean-room result is not yet proven.', 'מלך_עולם': 'The completion contract is recorded as authority.', 'ראה': 'Required root-generation dependencies remain open.', 'progress': 0}]}
COLLECTION_FIELD = 'observations'
IDENTITY_FIELD = 'id'
DISPLAY_FIELDS = ['temporal', 'observer', 'phase', 'title', 'progress', 'kind', 'observed_ref', 'הבט', 'ראה', 'חקור', 'הבן', 'מלך_עולם', 'אדון_הכל', 'link']
TABLE_COLUMNS = [{'field': 'temporal', 'label': 'Time', 'width': 90}, {'field': 'observer', 'label': 'Observer', 'width': 100}, {'field': 'phase', 'label': 'SDLC phase', 'width': 120}, {'field': 'progress', 'label': 'Progress %', 'width': 90}, {'field': 'title', 'label': 'Development item', 'width': 360}]
DETAIL_FIELDS = [{'field': 'title', 'label': 'Development item'}, {'field': 'temporal', 'label': 'Time horizon'}, {'field': 'observer', 'label': 'Observer'}, {'field': 'phase', 'label': 'SDLC phase'}, {'field': 'progress', 'label': 'Measured progress (%)'}, {'field': 'הבט', 'label': 'Physical presence — הבט'}, {'field': 'ראה', 'label': 'Identity and relation — ראה'}, {'field': 'חקור', 'label': 'Measured evidence — חקור'}, {'field': 'הבן', 'label': 'Meaning and next decision — הבן'}, {'field': 'מלך_עולם', 'label': 'Canonical authority — מלך_עולם'}, {'field': 'אדון_הכל', 'label': 'Manifested projections — אדון_הכל'}, {'field': 'observed_ref', 'label': 'Evidence identity'}, {'field': 'link', 'label': 'Related code or issue'}]
OBSERVATION_METRICS = [{'label': 'generated products', 'value': '74'}, {'label': 'product families', 'value': '4'}, {'label': 'acceptance cases', 'value': '175 / 175'}, {'label': 'generated GUI checks', 'value': 'PASS'}, {'label': 'verification budget', 'value': '≤ 5 seconds'}]
PORTFOLIO_COLUMNS = [{'field': 'group', 'label': 'Product family', 'width': 150}, {'field': 'product', 'label': 'Generated product', 'width': 240}, {'field': 'identity', 'label': 'Canonical identity', 'width': 520}, {'field': 'status', 'label': 'Proof status', 'width': 110}]
PORTFOLIO_RECORDS = [{'group': 'todos', 'identity': 'uc://applications/approvals@1', 'product': 'approvals', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/bug-tracker@1', 'product': 'bug-tracker', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/calendar-tasks@1', 'product': 'calendar-tasks', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/care-plan@1', 'product': 'care-plan', 'status': 'proven'}, {'group': 'pong-games', 'identity': 'uc://applications/classic-paddle-duel@1', 'product': 'classic-paddle-duel', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/collaboration-sync-plan@1', 'product': 'collaboration-sync-plan', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/costed-todo@1', 'product': 'costed-todo', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/crm-follow-up@1', 'product': 'crm-follow-up', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/daily-planner@1', 'product': 'daily-planner', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/dependency-plan@1', 'product': 'dependency-plan', 'status': 'proven'}, {'group': 'dashboards', 'identity': 'uc://applications/development-observatory@1', 'product': 'development-observatory', 'status': 'proven'}, {'group': 'pong-games', 'identity': 'uc://applications/doubles-paddle-duel@1', 'product': 'doubles-paddle-duel', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/editorial-calendar@1', 'product': 'editorial-calendar', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/eisenhower@1', 'product': 'eisenhower', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/errands@1', 'product': 'errands', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/event-planning@1', 'product': 'event-planning', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/grocery@1', 'product': 'grocery', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/gtd@1', 'product': 'gtd', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/habits@1', 'product': 'habits', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/inventory-restock@1', 'product': 'inventory-restock', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/issue-tracker@1', 'product': 'issue-tracker', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/kanban@1', 'product': 'kanban', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/maintenance-work-orders@1', 'product': 'maintenance-work-orders', 'status': 'proven'}, {'group': 'pong-games', 'identity': 'uc://applications/multiball-paddle-duel@1', 'product': 'multiball-paddle-duel', 'status': 'proven'}, {'group': 'pong-games', 'identity': 'uc://applications/obstacle-paddle-arena@1', 'product': 'obstacle-paddle-arena', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/offline-security-plan@1', 'product': 'offline-security-plan', 'status': 'proven'}, {'group': 'pong-games', 'identity': 'uc://applications/power-up-paddle-arena@1', 'product': 'power-up-paddle-arena', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/product-roadmap@1', 'product': 'product-roadmap', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/project-work-breakdown@1', 'product': 'project-work-breakdown', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/recurring-chores@1', 'product': 'recurring-chores', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/reminders@1', 'product': 'reminders', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/research-pipeline@1', 'product': 'research-pipeline', 'status': 'proven'}, {'group': 'pong-games', 'identity': 'uc://applications/solo-paddle-opponent@1', 'product': 'solo-paddle-opponent', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/sprint-backlog@1', 'product': 'sprint-backlog', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/study-homework@1', 'product': 'study-homework', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/support-queue@1', 'product': 'support-queue', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/team-assignments@1', 'product': 'team-assignments', 'status': 'proven'}, {'group': 'pong-games', 'identity': 'uc://applications/timed-paddle-score-attack@1', 'product': 'timed-paddle-score-attack', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/todo@1', 'product': 'todo', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/travel-checklist@1', 'product': 'travel-checklist', 'status': 'proven'}, {'group': 'pong-games', 'identity': 'uc://applications/wall-return-training@1', 'product': 'wall-return-training', 'status': 'proven'}, {'group': 'todos', 'identity': 'uc://applications/weekly-planner@1', 'product': 'weekly-planner', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/arbitrary-precision@1', 'product': 'arbitrary-precision', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/calculus@1', 'product': 'calculus', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/chemistry@1', 'product': 'chemistry', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/complex-number@1', 'product': 'complex-number', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/construction@1', 'product': 'construction', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/cooking@1', 'product': 'cooking', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/currency@1', 'product': 'currency', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/date-time@1', 'product': 'date-time', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/engineering-units@1', 'product': 'engineering-units', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/financial@1', 'product': 'financial', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/fraction@1', 'product': 'fraction', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/geometry@1', 'product': 'geometry', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/graphing@1', 'product': 'graphing', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/health@1', 'product': 'health', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/investment@1', 'product': 'investment', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/loan-mortgage@1', 'product': 'loan-mortgage', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/matrix-vector@1', 'product': 'matrix-vector', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/navigation@1', 'product': 'navigation', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/normal@1', 'product': 'normal', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/ohms-law@1', 'product': 'ohms-law', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/physics@1', 'product': 'physics', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/polynomial-algebra@1', 'product': 'polynomial-algebra', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/probability@1', 'product': 'probability', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/programmer@1', 'product': 'programmer', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/quadratic-polynomial@1', 'product': 'quadratic-polynomial', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/regression@1', 'product': 'regression', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/regular@1', 'product': 'regular', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/rpn@1', 'product': 'rpn', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/scientific@1', 'product': 'scientific', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/statistical@1', 'product': 'statistical', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/subnet@1', 'product': 'subnet', 'status': 'proven'}, {'group': 'calculators', 'identity': 'uc://applications/tax@1', 'product': 'tax', 'status': 'proven'}]
FILTER_FIELD = 'filter'
FILTERS = {'all': None, 'completed': {'equals': True, 'field': 'completed'}, 'future': {'equals': 'future', 'field': 'temporal'}, 'open': {'equals': False, 'field': 'completed'}, 'past': {'equals': 'past', 'field': 'temporal'}, 'present': {'equals': 'present', 'field': 'temporal'}}
VISIBILITY = {'equals': False, 'field': 'archived'}
DEFAULT_STATE_PATH = '.unified-code-manual/development-observatory/state.json'
STATE_ENVIRONMENT = 'UC_MANUAL_DEVELOPMENT_OBSERVATORY_STATE'
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
    _root.title('Unified Development Observatory')
    _root.geometry('1400x720+40+40')
    _root.columnconfigure(0, weight=1)
    _root.columnconfigure(1, weight=1)
    _root.columnconfigure(2, weight=1)
    _root.columnconfigure(3, weight=1)
    _root.rowconfigure(1, weight=1)
    Label(_root, text='Request to AI').grid(row=0, column=0, sticky='w')
    _inputs['entry.primary'] = Entry(_root, width=80)
    _inputs['entry.primary'].grid(row=0, column=1, columnspan=3, sticky='ew')
    surface = Frame(_root, padx=12, pady=10)
    surface.grid(row=1, column=0, columnspan=4, sticky='nsew')
    surface.columnconfigure(0, weight=3)
    surface.columnconfigure(2, weight=2)
    surface.rowconfigure(3, weight=1)
    Label(surface, text='Development lifecycle — past, present and future', font=('Helvetica', 18, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 4))
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
    _tabs.add(overview_surface, text='Development direction')
    _tabs.add(portfolio_surface, text='All generated products')
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
    cases = [{'expected': {'results': [{'error': None, 'result': {'filter': 'all', 'next_id': 6, 'observations': [{'archived': False, 'completed': True, 'id': 1, 'kind': 'achievement', 'link': 'https://github.com/adico1/unified-code', 'observed_ref': '8933e8456b67375ec2b567c0107a64d9afc3c060', 'observer': 'system', 'passed': 13, 'phase': 'verified', 'progress': 100, 'temporal': 'past', 'title': 'Milestone 1 seed-to-application proof', 'total': 13, 'אדון_הכל': 'Manifested and verified: application, API and CLI.', 'הבט': 'A runnable generated application artifact exists.', 'הבן': 'This proves bounded seed-to-application generation, not root self-hosting.', 'חקור': 'Every L1-L13 verification gate passed.', 'מלך_עולם': 'The application seed is the verified canonical authority.', 'ראה': 'The seed and generated product resolve to one identity.'}, {'archived': False, 'completed': False, 'id': 2, 'kind': 'review', 'link': 'https://github.com/adico1/unified-code-manual/blob/feature/development-observatory/src/stateful_compiler.py', 'observed_ref': 'uc://applications/development-observatory@1', 'observer': 'architect', 'passed': 292, 'phase': 'verification', 'progress': 100, 'temporal': 'present', 'title': 'Manual compiler: 74 products in four groups', 'total': 292, 'אדון_הכל': 'Manifested and verified: application, API and GUI.', 'הבט': 'A public review branch and pull request exist.', 'הבן': 'Review and merge the product-family dependency before this stacked change.', 'חקור': 'The complete local proof passed within the five-second law.', 'מלך_עולם': 'ROOT pins every current creator authority.', 'ראה': 'Every product identity is derived from registered seed data.'}, {'archived': False, 'completed': False, 'id': 3, 'kind': 'gap', 'link': 'https://github.com/adico1/unified-code/issues/10', 'observed_ref': '4ee817a950e323614ff4215426391e6ebd2e5afc', 'observer': 'system', 'passed': 0, 'phase': 'blocked', 'progress': 0, 'temporal': 'present', 'title': 'ROOT creator is pinned but not root-generated', 'total': 1, 'אדון_הכל': 'Manifested: partial repository; the root-generated repository is absent.', 'הבט': 'The trusted creator exists as handwritten infrastructure.', 'הבן': 'The creator must still be generated from ROOT before Milestone 2 can close.', 'חקור': 'The repository-wide fixed-point proof remains open.', 'מלך_עולם': 'ROOT is pinned but does not yet generate its creator.', 'ראה': 'Authority remains divided between ROOT and handwritten creator code.'}, {'archived': False, 'completed': False, 'id': 4, 'kind': 'direction', 'link': 'https://github.com/adico1/unified-code/issues/9', 'observed_ref': 'issue-9', 'observer': 'ai', 'passed': 0, 'phase': 'planned', 'progress': 0, 'temporal': 'future', 'title': 'Clean-room whole-repository fixed point', 'total': 1, 'אדון_הכל': 'No clean-room root-generated repository has manifested yet.', 'הבט': 'The clean-room integration issue and contract exist.', 'הבן': 'Begin only after dependency provenance and root generation are complete.', 'חקור': 'Acceptance is declared; the clean-room result is not yet proven.', 'מלך_עולם': 'The completion contract is recorded as authority.', 'ראה': 'Required root-generation dependencies remain open.'}, {'archived': False, 'completed': False, 'id': 5, 'kind': 'request', 'link': '', 'observed_ref': 'local-request', 'observer': 'user', 'passed': 0, 'phase': 'proposed', 'progress': 0, 'temporal': 'future', 'title': 'Expose approved AI request', 'total': 1, 'אדון_הכל': 'Requested application and API projections have not manifested.', 'הבט': 'A user request is stored in the local queue.', 'הבן': 'The user must authorize the external destination before delivery.', 'חקור': 'No external AI or GitHub delivery has been executed.', 'מלך_עולם': 'A future seed must declare the audited external delivery boundary.', 'ראה': 'The request is identified but not yet authorized for external delivery.'}]}}], 'state': {'filter': 'all', 'next_id': 6, 'observations': [{'archived': False, 'completed': True, 'id': 1, 'kind': 'achievement', 'link': 'https://github.com/adico1/unified-code', 'observed_ref': '8933e8456b67375ec2b567c0107a64d9afc3c060', 'observer': 'system', 'passed': 13, 'phase': 'verified', 'progress': 100, 'temporal': 'past', 'title': 'Milestone 1 seed-to-application proof', 'total': 13, 'אדון_הכל': 'Manifested and verified: application, API and CLI.', 'הבט': 'A runnable generated application artifact exists.', 'הבן': 'This proves bounded seed-to-application generation, not root self-hosting.', 'חקור': 'Every L1-L13 verification gate passed.', 'מלך_עולם': 'The application seed is the verified canonical authority.', 'ראה': 'The seed and generated product resolve to one identity.'}, {'archived': False, 'completed': False, 'id': 2, 'kind': 'review', 'link': 'https://github.com/adico1/unified-code-manual/blob/feature/development-observatory/src/stateful_compiler.py', 'observed_ref': 'uc://applications/development-observatory@1', 'observer': 'architect', 'passed': 292, 'phase': 'verification', 'progress': 100, 'temporal': 'present', 'title': 'Manual compiler: 74 products in four groups', 'total': 292, 'אדון_הכל': 'Manifested and verified: application, API and GUI.', 'הבט': 'A public review branch and pull request exist.', 'הבן': 'Review and merge the product-family dependency before this stacked change.', 'חקור': 'The complete local proof passed within the five-second law.', 'מלך_עולם': 'ROOT pins every current creator authority.', 'ראה': 'Every product identity is derived from registered seed data.'}, {'archived': False, 'completed': False, 'id': 3, 'kind': 'gap', 'link': 'https://github.com/adico1/unified-code/issues/10', 'observed_ref': '4ee817a950e323614ff4215426391e6ebd2e5afc', 'observer': 'system', 'passed': 0, 'phase': 'blocked', 'progress': 0, 'temporal': 'present', 'title': 'ROOT creator is pinned but not root-generated', 'total': 1, 'אדון_הכל': 'Manifested: partial repository; the root-generated repository is absent.', 'הבט': 'The trusted creator exists as handwritten infrastructure.', 'הבן': 'The creator must still be generated from ROOT before Milestone 2 can close.', 'חקור': 'The repository-wide fixed-point proof remains open.', 'מלך_עולם': 'ROOT is pinned but does not yet generate its creator.', 'ראה': 'Authority remains divided between ROOT and handwritten creator code.'}, {'archived': False, 'completed': False, 'id': 4, 'kind': 'direction', 'link': 'https://github.com/adico1/unified-code/issues/9', 'observed_ref': 'issue-9', 'observer': 'ai', 'passed': 0, 'phase': 'planned', 'progress': 0, 'temporal': 'future', 'title': 'Clean-room whole-repository fixed point', 'total': 1, 'אדון_הכל': 'No clean-room root-generated repository has manifested yet.', 'הבט': 'The clean-room integration issue and contract exist.', 'הבן': 'Begin only after dependency provenance and root generation are complete.', 'חקור': 'Acceptance is declared; the clean-room result is not yet proven.', 'מלך_עולם': 'The completion contract is recorded as authority.', 'ראה': 'Required root-generation dependencies remain open.'}, {'archived': False, 'completed': False, 'id': 5, 'kind': 'request', 'link': '', 'observed_ref': 'local-request', 'observer': 'user', 'passed': 0, 'phase': 'proposed', 'progress': 0, 'temporal': 'future', 'title': 'Expose approved AI request', 'total': 1, 'אדון_הכל': 'Requested application and API projections have not manifested.', 'הבט': 'A user request is stored in the local queue.', 'הבן': 'The user must authorize the external destination before delivery.', 'חקור': 'No external AI or GitHub delivery has been executed.', 'מלך_עולם': 'A future seed must declare the audited external delivery boundary.', 'ראה': 'The request is identified but not yet authorized for external delivery.'}]}}, 'id': 'development-observatory.request-to-ai', 'input': {'steps': [{'arguments': {'title': 'Expose approved AI request'}, 'command': 'create'}]}}]
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
        cases = [{'assertions': {'collection_count': 5, 'error': None, 'outward': [], 'record': {'fields': {'archived': False, 'completed': False, 'observer': 'user', 'temporal': 'future'}, 'match': {'equals': 'Review all generated product evidence', 'field': 'title'}, 'present': True}, 'state_fields': {'filter': 'all'}, 'visible_count': 5}, 'control': 'request.submit', 'id': 'ask-ai', 'inputs': {'entry.primary': 'Review all generated product evidence'}, 'restart': True}, {'assertions': {'collection_count': 5, 'error': None, 'outward': [], 'record': {'fields': {'archived': False, 'completed': True}, 'match': {'equals': 'Complete this request', 'field': 'title'}, 'present': True}, 'state_fields': {'filter': 'all'}, 'visible_count': 5}, 'control': 'record.toggle', 'id': 'complete-request', 'restart': True, 'selection': {'identity': 'collection.primary', 'index': 4}, 'setup': [{'arguments': {'title': 'Complete this request'}, 'command': 'create'}]}, {'assertions': {'collection_count': 5, 'error': None, 'outward': [], 'record': {'fields': {'archived': False, 'completed': False}, 'match': {'equals': 'Reopen this request', 'field': 'title'}, 'present': True}, 'state_fields': {'filter': 'all'}, 'visible_count': 5}, 'control': 'record.toggle', 'id': 'reopen-request', 'restart': True, 'selection': {'identity': 'collection.primary', 'index': 4}, 'setup': [{'arguments': {'title': 'Reopen this request'}, 'command': 'create'}, {'arguments': {'id': 5}, 'command': 'toggle'}]}, {'assertions': {'collection_count': 4, 'error': 'protected-observation', 'outward': [], 'record': {'fields': {'archived': False, 'completed': False}, 'match': {'equals': 2, 'field': 'id'}, 'present': True}, 'state_fields': {'filter': 'all'}, 'visible_count': 4}, 'control': 'record.toggle', 'id': 'protect-system-completion', 'selection': {'identity': 'collection.primary', 'index': 1}}, {'assertions': {'collection_count': 4, 'error': None, 'outward': ['https://github.com/adico1/unified-code'], 'record': {'fields': {'archived': False, 'completed': True}, 'match': {'equals': 1, 'field': 'id'}, 'present': True}, 'state_fields': {'filter': 'all'}, 'visible_count': 4}, 'control': 'link.open', 'id': 'open-code', 'selection': {'identity': 'collection.primary', 'index': 0}}, {'assertions': {'collection_count': 5, 'error': 'confirmation-declined', 'outward': [], 'record': {'fields': {'archived': False}, 'match': {'equals': 'Keep this request', 'field': 'title'}, 'present': True}, 'state_fields': {'filter': 'all'}, 'visible_count': 5}, 'confirmation': False, 'control': 'record.archive', 'id': 'decline-archive', 'restart': True, 'selection': {'identity': 'collection.primary', 'index': 4}, 'setup': [{'arguments': {'title': 'Keep this request'}, 'command': 'create'}]}, {'assertions': {'collection_count': 5, 'error': None, 'outward': [], 'record': {'fields': {'archived': True}, 'match': {'equals': 'Archive this request', 'field': 'title'}, 'present': True}, 'state_fields': {'filter': 'all'}, 'visible_count': 4}, 'confirmation': True, 'control': 'record.archive', 'id': 'archive-request', 'restart': True, 'selection': {'identity': 'collection.primary', 'index': 4}, 'setup': [{'arguments': {'title': 'Archive this request'}, 'command': 'create'}]}, {'assertions': {'collection_count': 4, 'error': 'protected-observation', 'outward': [], 'record': {'fields': {'archived': False}, 'match': {'equals': 1, 'field': 'id'}, 'present': True}, 'state_fields': {'filter': 'all'}, 'visible_count': 4}, 'confirmation': True, 'control': 'record.archive', 'id': 'protect-system-archive', 'selection': {'identity': 'collection.primary', 'index': 0}}, {'assertions': {'collection_count': 4, 'error': None, 'outward': [], 'record': None, 'state_fields': {'filter': 'all'}, 'visible_count': 4}, 'control': 'filter.all', 'id': 'filter-all', 'setup': [{'arguments': {'mode': 'future'}, 'command': 'set_filter'}]}, {'assertions': {'collection_count': 4, 'error': None, 'outward': [], 'record': None, 'state_fields': {'filter': 'past'}, 'visible_count': 1}, 'control': 'filter.past', 'id': 'filter-past'}, {'assertions': {'collection_count': 4, 'error': None, 'outward': [], 'record': None, 'state_fields': {'filter': 'present'}, 'visible_count': 2}, 'control': 'filter.present', 'id': 'filter-present'}, {'assertions': {'collection_count': 4, 'error': None, 'outward': [], 'record': None, 'state_fields': {'filter': 'future'}, 'visible_count': 1}, 'control': 'filter.future', 'id': 'filter-future'}]
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
