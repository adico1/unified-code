"""Generated bounded simulation. Do not edit."""
from copy import deepcopy
import json
import sys

APPLICATION_ID = 'uc://applications/solo-paddle-opponent@1'
TEN_DEPTHS = ('01_identity', '02_authority', '03_declaration', '04_composition', '05_processing', '06_state', '07_boundary', '08_manifestation', '09_evidence', '10_fixed_point')
INITIAL_STATE = {'entities': {'left-bat': {'height': 60, 'vx': 0, 'vy': 0, 'width': 10, 'x': 20, 'y': 90}, 'orb': {'height': 10, 'vx': 5, 'vy': 3, 'width': 10, 'x': 195, 'y': 115}, 'right-bat': {'height': 60, 'vx': 0, 'vy': 0, 'width': 10, 'x': 370, 'y': 90}}, 'left_score': 0, 'right_score': 0, 'status': 'playing', 'tick': 0}
TICK_MILLISECONDS = 16
state = deepcopy(INITIAL_STATE)
_root = None
_surface = None
_status = None
_buttons = {}
_running = False

def snapshot():
    return deepcopy(state)

def reset_state():
    state.clear()
    state.update(deepcopy(INITIAL_STATE))
    present_state()
    return snapshot()

def control_0():
    state['entities']['left-bat']['y'] += -18
    present_state()
    return snapshot()

def control_1():
    state['entities']['left-bat']['y'] += 18
    present_state()
    return snapshot()

def advance():
    if state['entities']['orb']['y'] < state['entities']['right-bat']['y']:
        state['entities']['right-bat']['y'] = max(0, state['entities']['right-bat']['y'] - 4)
    if state['entities']['orb']['y'] > state['entities']['right-bat']['y']:
        state['entities']['right-bat']['y'] = min(180, state['entities']['right-bat']['y'] + 4)
    state['entities']['orb']['x'] += state['entities']['orb']['vx']
    state['entities']['orb']['y'] += state['entities']['orb']['vy']
    if state['entities']['orb']['y'] < 0:
        state['entities']['orb']['y'] = 0
        state['entities']['orb']['vy'] = abs(state['entities']['orb']['vy'])
    if state['entities']['orb']['y'] > 230:
        state['entities']['orb']['y'] = 230
        state['entities']['orb']['vy'] = -abs(state['entities']['orb']['vy'])
    if state['entities']['left-bat']['y'] < 0:
        state['entities']['left-bat']['y'] = 0
        state['entities']['left-bat']['vy'] = abs(state['entities']['left-bat']['vy'])
    if state['entities']['left-bat']['y'] > 180:
        state['entities']['left-bat']['y'] = 180
        state['entities']['left-bat']['vy'] = -abs(state['entities']['left-bat']['vy'])
    if state['entities']['right-bat']['y'] < 0:
        state['entities']['right-bat']['y'] = 0
        state['entities']['right-bat']['vy'] = abs(state['entities']['right-bat']['vy'])
    if state['entities']['right-bat']['y'] > 180:
        state['entities']['right-bat']['y'] = 180
        state['entities']['right-bat']['vy'] = -abs(state['entities']['right-bat']['vy'])
    if (state['entities']['orb']['x'] < state['entities']['left-bat']['x'] + state['entities']['left-bat']['width'] and state['entities']['orb']['x'] + state['entities']['orb']['width'] > state['entities']['left-bat']['x'] and state['entities']['orb']['y'] < state['entities']['left-bat']['y'] + state['entities']['left-bat']['height'] and state['entities']['orb']['y'] + state['entities']['orb']['height'] > state['entities']['left-bat']['y']):
        state['entities']['orb']['vx'] *= -1
    if (state['entities']['orb']['x'] < state['entities']['right-bat']['x'] + state['entities']['right-bat']['width'] and state['entities']['orb']['x'] + state['entities']['orb']['width'] > state['entities']['right-bat']['x'] and state['entities']['orb']['y'] < state['entities']['right-bat']['y'] + state['entities']['right-bat']['height'] and state['entities']['orb']['y'] + state['entities']['orb']['height'] > state['entities']['right-bat']['y']):
        state['entities']['orb']['vx'] *= -1
    if state['entities']['orb']['x'] < 0:
        state['right_score'] += 1
        state['entities']['orb']['x'] = 195
        state['entities']['orb']['y'] = 115
        state['entities']['orb']['vx'] = 5
    if state['entities']['orb']['x'] > 390:
        state['left_score'] += 1
        state['entities']['orb']['x'] = 195
        state['entities']['orb']['y'] = 115
        state['entities']['orb']['vx'] = -5
    state['tick'] += 1
    present_state()
    return snapshot()

def present_state():
    if _surface is None:
        return
    _surface.delete('all')
    _surface.create_rectangle(state['entities']['left-bat']['x'], state['entities']['left-bat']['y'], state['entities']['left-bat']['x'] + state['entities']['left-bat']['width'], state['entities']['left-bat']['y'] + state['entities']['left-bat']['height'], fill='white', outline='white')
    _surface.create_rectangle(state['entities']['right-bat']['x'], state['entities']['right-bat']['y'], state['entities']['right-bat']['x'] + state['entities']['right-bat']['width'], state['entities']['right-bat']['y'] + state['entities']['right-bat']['height'], fill='white', outline='white')
    _surface.create_rectangle(state['entities']['orb']['x'], state['entities']['orb']['y'], state['entities']['orb']['x'] + state['entities']['orb']['width'], state['entities']['orb']['y'] + state['entities']['orb']['height'], fill='white', outline='white')
    _surface.create_text(200, 18, text='{left_score} : {right_score}'.format(**state), fill='white')
    if _status is not None:
        _status.set(str(state.get('status', 'ready')))

def build_interface():
    global _root, _surface, _status, Button, Canvas, Label, StringVar, Tk
    from tkinter import Button, Canvas, Label, StringVar, Tk
    _root = Tk()
    _root.title('Solo Paddle Opponent')
    _root.geometry('420x330+80+80')
    _surface = Canvas(_root, width=400, height=240, bg='black', highlightthickness=0)
    _surface.grid(row=0, column=0, columnspan=2)
    _buttons['participant.left.up'] = Button(_root, text='Left ↑', command=control_0)
    _buttons['participant.left.up'].grid(row=1, column=0, sticky='nsew')
    _root.bind('<w>', lambda event, operation=control_0: operation())
    _buttons['participant.left.down'] = Button(_root, text='Left ↓', command=control_1)
    _buttons['participant.left.down'].grid(row=1, column=1, sticky='nsew')
    _root.bind('<s>', lambda event, operation=control_1: operation())
    _status = StringVar(value='ready')
    Label(_root, textvariable=_status).grid(row=2, column=0, columnspan=2)
    present_state()
    return _root

def run_case(case):
    reset_state()
    operations = {
        'participant.left.up': control_0,
        'participant.left.down': control_1,
    }
    for step in case['steps']:
        operation = step.get('control')
        if operation is not None:
            operations[operation]()
        for _ in range(step.get('ticks', 0)):
            advance()
    return snapshot()

def part(thing):
    result = run_case(thing['value'])
    return {'value': result, 'depths': TEN_DEPTHS, 'axes': tuple(thing.get('axes', ())), 'evidence': tuple(thing.get('evidence', ())) + ('boundary:inward', 'part:run_case', 'boundary:outward'), 'state': 'valid'}

def run_acceptance():
    cases = [{'expected': {'entities': {'left-bat': {'height': 60, 'vx': 0, 'vy': 0, 'width': 10, 'x': 20, 'y': 90}, 'orb': {'height': 10, 'vx': 5, 'vy': 3, 'width': 10, 'x': 200, 'y': 118}, 'right-bat': {'height': 60, 'vx': 0, 'vy': 0, 'width': 10, 'x': 370, 'y': 94}}, 'left_score': 0, 'right_score': 0, 'status': 'playing', 'tick': 1}, 'id': 'solo.opponent-motion', 'input': {'steps': [{'ticks': 1}]}}]
    results = [run_case(case['input']) == case['expected'] for case in cases]
    return {'passed': sum(results), 'total': len(results), 'cases': [case['id'] for case in cases]}

def self_test_application():
    root = build_interface()
    root.withdraw()
    cases = [{'expected': {'entities': {'left-bat': {'height': 60, 'vx': 0, 'vy': 0, 'width': 10, 'x': 20, 'y': 90}, 'orb': {'height': 10, 'vx': 5, 'vy': 3, 'width': 10, 'x': 200, 'y': 118}, 'right-bat': {'height': 60, 'vx': 0, 'vy': 0, 'width': 10, 'x': 370, 'y': 94}}, 'left_score': 0, 'right_score': 0, 'status': 'playing', 'tick': 1}, 'input': {'steps': [{'ticks': 1}]}}]
    checks = []
    for case in cases:
        reset_state()
        for step in case['input']['steps']:
            control = step.get('control')
            if control is not None:
                _buttons[control].invoke()
            for _ in range(step.get('ticks', 0)):
                advance()
        checks.append(snapshot() == case['expected'])
        checks.append(len(_surface.find_all()) == 4)
    root.destroy()
    return {'self_test': {'passed': sum(checks), 'total': len(checks)}, 'closed': True}

def scheduled_tick():
    if _running:
        advance()
        _root.after(TICK_MILLISECONDS, scheduled_tick)

def launch():
    global _running
    proof = self_test_application()
    if proof['self_test']['passed'] != proof['self_test']['total']:
        raise RuntimeError('generated-self-test-failed')
    reset_state()
    root = build_interface()
    _running = True
    root.after(TICK_MILLISECONDS, scheduled_tick)
    root.mainloop()

def main():
    if '--self-test' in sys.argv:
        report = self_test_application()
        print(json.dumps(report, sort_keys=True))
        return 0 if report['self_test']['passed'] == report['self_test']['total'] and report['closed'] else 1
    launch()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
