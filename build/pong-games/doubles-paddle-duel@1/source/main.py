"""Generated bounded simulation. Do not edit."""
from copy import deepcopy
import json
import sys

APPLICATION_ID = 'uc://applications/doubles-paddle-duel@1'
TEN_DEPTHS = ('01_identity', '02_authority', '03_declaration', '04_composition', '05_processing', '06_state', '07_boundary', '08_manifestation', '09_evidence', '10_fixed_point')
INITIAL_STATE = {'entities': {'orb': {'height': 10, 'vx': 5, 'vy': 3, 'width': 10, 'x': 195, 'y': 115}, 'left-bat-a': {'height': 45, 'vx': 0, 'vy': 0, 'width': 10, 'x': 20, 'y': 40}, 'left-bat-b': {'height': 45, 'vx': 0, 'vy': 0, 'width': 10, 'x': 20, 'y': 150}, 'right-bat-a': {'height': 45, 'vx': 0, 'vy': 0, 'width': 10, 'x': 370, 'y': 40}, 'right-bat-b': {'height': 45, 'vx': 0, 'vy': 0, 'width': 10, 'x': 370, 'y': 150}}, 'left_score': 0, 'right_score': 0, 'status': 'playing', 'tick': 0}
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
    state['entities']['left-bat-a']['y'] += -18
    state['entities']['left-bat-b']['y'] += -18
    present_state()
    return snapshot()

def control_1():
    state['entities']['left-bat-a']['y'] += 18
    state['entities']['left-bat-b']['y'] += 18
    present_state()
    return snapshot()

def control_2():
    state['entities']['right-bat-a']['y'] += -18
    state['entities']['right-bat-b']['y'] += -18
    present_state()
    return snapshot()

def control_3():
    state['entities']['right-bat-a']['y'] += 18
    state['entities']['right-bat-b']['y'] += 18
    present_state()
    return snapshot()

def advance():
    state['entities']['orb']['x'] += state['entities']['orb']['vx']
    state['entities']['orb']['y'] += state['entities']['orb']['vy']
    if state['entities']['orb']['y'] < 0:
        state['entities']['orb']['y'] = 0
        state['entities']['orb']['vy'] = abs(state['entities']['orb']['vy'])
    if state['entities']['orb']['y'] > 230:
        state['entities']['orb']['y'] = 230
        state['entities']['orb']['vy'] = -abs(state['entities']['orb']['vy'])
    if state['entities']['left-bat-a']['y'] < 0:
        state['entities']['left-bat-a']['y'] = 0
        state['entities']['left-bat-a']['vy'] = abs(state['entities']['left-bat-a']['vy'])
    if state['entities']['left-bat-a']['y'] > 195:
        state['entities']['left-bat-a']['y'] = 195
        state['entities']['left-bat-a']['vy'] = -abs(state['entities']['left-bat-a']['vy'])
    if state['entities']['left-bat-b']['y'] < 0:
        state['entities']['left-bat-b']['y'] = 0
        state['entities']['left-bat-b']['vy'] = abs(state['entities']['left-bat-b']['vy'])
    if state['entities']['left-bat-b']['y'] > 195:
        state['entities']['left-bat-b']['y'] = 195
        state['entities']['left-bat-b']['vy'] = -abs(state['entities']['left-bat-b']['vy'])
    if state['entities']['right-bat-a']['y'] < 0:
        state['entities']['right-bat-a']['y'] = 0
        state['entities']['right-bat-a']['vy'] = abs(state['entities']['right-bat-a']['vy'])
    if state['entities']['right-bat-a']['y'] > 195:
        state['entities']['right-bat-a']['y'] = 195
        state['entities']['right-bat-a']['vy'] = -abs(state['entities']['right-bat-a']['vy'])
    if state['entities']['right-bat-b']['y'] < 0:
        state['entities']['right-bat-b']['y'] = 0
        state['entities']['right-bat-b']['vy'] = abs(state['entities']['right-bat-b']['vy'])
    if state['entities']['right-bat-b']['y'] > 195:
        state['entities']['right-bat-b']['y'] = 195
        state['entities']['right-bat-b']['vy'] = -abs(state['entities']['right-bat-b']['vy'])
    if (state['entities']['orb']['x'] < state['entities']['left-bat-a']['x'] + state['entities']['left-bat-a']['width'] and state['entities']['orb']['x'] + state['entities']['orb']['width'] > state['entities']['left-bat-a']['x'] and state['entities']['orb']['y'] < state['entities']['left-bat-a']['y'] + state['entities']['left-bat-a']['height'] and state['entities']['orb']['y'] + state['entities']['orb']['height'] > state['entities']['left-bat-a']['y']):
        state['entities']['orb']['vx'] *= -1
    if (state['entities']['orb']['x'] < state['entities']['left-bat-b']['x'] + state['entities']['left-bat-b']['width'] and state['entities']['orb']['x'] + state['entities']['orb']['width'] > state['entities']['left-bat-b']['x'] and state['entities']['orb']['y'] < state['entities']['left-bat-b']['y'] + state['entities']['left-bat-b']['height'] and state['entities']['orb']['y'] + state['entities']['orb']['height'] > state['entities']['left-bat-b']['y']):
        state['entities']['orb']['vx'] *= -1
    if (state['entities']['orb']['x'] < state['entities']['right-bat-a']['x'] + state['entities']['right-bat-a']['width'] and state['entities']['orb']['x'] + state['entities']['orb']['width'] > state['entities']['right-bat-a']['x'] and state['entities']['orb']['y'] < state['entities']['right-bat-a']['y'] + state['entities']['right-bat-a']['height'] and state['entities']['orb']['y'] + state['entities']['orb']['height'] > state['entities']['right-bat-a']['y']):
        state['entities']['orb']['vx'] *= -1
    if (state['entities']['orb']['x'] < state['entities']['right-bat-b']['x'] + state['entities']['right-bat-b']['width'] and state['entities']['orb']['x'] + state['entities']['orb']['width'] > state['entities']['right-bat-b']['x'] and state['entities']['orb']['y'] < state['entities']['right-bat-b']['y'] + state['entities']['right-bat-b']['height'] and state['entities']['orb']['y'] + state['entities']['orb']['height'] > state['entities']['right-bat-b']['y']):
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
    _surface.create_rectangle(state['entities']['left-bat-a']['x'], state['entities']['left-bat-a']['y'], state['entities']['left-bat-a']['x'] + state['entities']['left-bat-a']['width'], state['entities']['left-bat-a']['y'] + state['entities']['left-bat-a']['height'], fill='white', outline='white')
    _surface.create_rectangle(state['entities']['left-bat-b']['x'], state['entities']['left-bat-b']['y'], state['entities']['left-bat-b']['x'] + state['entities']['left-bat-b']['width'], state['entities']['left-bat-b']['y'] + state['entities']['left-bat-b']['height'], fill='white', outline='white')
    _surface.create_rectangle(state['entities']['right-bat-a']['x'], state['entities']['right-bat-a']['y'], state['entities']['right-bat-a']['x'] + state['entities']['right-bat-a']['width'], state['entities']['right-bat-a']['y'] + state['entities']['right-bat-a']['height'], fill='white', outline='white')
    _surface.create_rectangle(state['entities']['right-bat-b']['x'], state['entities']['right-bat-b']['y'], state['entities']['right-bat-b']['x'] + state['entities']['right-bat-b']['width'], state['entities']['right-bat-b']['y'] + state['entities']['right-bat-b']['height'], fill='white', outline='white')
    _surface.create_rectangle(state['entities']['orb']['x'], state['entities']['orb']['y'], state['entities']['orb']['x'] + state['entities']['orb']['width'], state['entities']['orb']['y'] + state['entities']['orb']['height'], fill='yellow', outline='yellow')
    _surface.create_text(200, 18, text='{left_score} : {right_score}'.format(**state), fill='white')
    if _status is not None:
        _status.set(str(state.get('status', 'ready')))

def build_interface():
    global _root, _surface, _status, Button, Canvas, Label, StringVar, Tk
    from tkinter import Button, Canvas, Label, StringVar, Tk
    _root = Tk()
    _root.title('Doubles Paddle Duel')
    _root.geometry('420x330+80+80')
    _surface = Canvas(_root, width=400, height=240, bg='black', highlightthickness=0)
    _surface.grid(row=0, column=0, columnspan=4)
    _buttons['team.left.up'] = Button(_root, text='Left team ↑', command=control_0)
    _buttons['team.left.up'].grid(row=1, column=0, sticky='nsew')
    _root.bind('<w>', lambda event, operation=control_0: operation())
    _buttons['team.left.down'] = Button(_root, text='Left team ↓', command=control_1)
    _buttons['team.left.down'].grid(row=1, column=1, sticky='nsew')
    _root.bind('<s>', lambda event, operation=control_1: operation())
    _buttons['team.right.up'] = Button(_root, text='Right team ↑', command=control_2)
    _buttons['team.right.up'].grid(row=1, column=2, sticky='nsew')
    _root.bind('<Up>', lambda event, operation=control_2: operation())
    _buttons['team.right.down'] = Button(_root, text='Right team ↓', command=control_3)
    _buttons['team.right.down'].grid(row=1, column=3, sticky='nsew')
    _root.bind('<Down>', lambda event, operation=control_3: operation())
    _status = StringVar(value='ready')
    Label(_root, textvariable=_status).grid(row=2, column=0, columnspan=4)
    present_state()
    return _root

def run_case(case):
    reset_state()
    operations = {
        'team.left.up': control_0,
        'team.left.down': control_1,
        'team.right.up': control_2,
        'team.right.down': control_3,
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
    cases = [{'expected': {'entities': {'left-bat-a': {'height': 45, 'vx': 0, 'vy': 0, 'width': 10, 'x': 20, 'y': 22}, 'left-bat-b': {'height': 45, 'vx': 0, 'vy': 0, 'width': 10, 'x': 20, 'y': 132}, 'orb': {'height': 10, 'vx': 5, 'vy': 3, 'width': 10, 'x': 195, 'y': 115}, 'right-bat-a': {'height': 45, 'vx': 0, 'vy': 0, 'width': 10, 'x': 370, 'y': 40}, 'right-bat-b': {'height': 45, 'vx': 0, 'vy': 0, 'width': 10, 'x': 370, 'y': 150}}, 'left_score': 0, 'right_score': 0, 'status': 'playing', 'tick': 0}, 'id': 'doubles.team-control', 'input': {'steps': [{'control': 'team.left.up'}]}}]
    results = [run_case(case['input']) == case['expected'] for case in cases]
    return {'passed': sum(results), 'total': len(results), 'cases': [case['id'] for case in cases]}

def self_test_application():
    root = build_interface()
    root.withdraw()
    cases = [{'expected': {'entities': {'left-bat-a': {'height': 45, 'vx': 0, 'vy': 0, 'width': 10, 'x': 20, 'y': 22}, 'left-bat-b': {'height': 45, 'vx': 0, 'vy': 0, 'width': 10, 'x': 20, 'y': 132}, 'orb': {'height': 10, 'vx': 5, 'vy': 3, 'width': 10, 'x': 195, 'y': 115}, 'right-bat-a': {'height': 45, 'vx': 0, 'vy': 0, 'width': 10, 'x': 370, 'y': 40}, 'right-bat-b': {'height': 45, 'vx': 0, 'vy': 0, 'width': 10, 'x': 370, 'y': 150}}, 'left_score': 0, 'right_score': 0, 'status': 'playing', 'tick': 0}, 'input': {'steps': [{'control': 'team.left.up'}]}}]
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
        checks.append(len(_surface.find_all()) == 6)
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
