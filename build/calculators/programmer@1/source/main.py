# stamp: 01_outer_to_inner
"""Generated from concise declarations; no seed is loaded at runtime."""
import ast
import json
import operator
import sys
from tkinter import Button, Entry, Label, StringVar, Tk
IDENTITY = 'programmer'
THING_STATES = ('unknown', 'absent', 'false', 'formed', 'valid', 'invalid')
TEN_DEPTHS = ('01_identity', '02_authority', '03_declaration', '04_composition', '05_processing', '06_state', '07_boundary', '08_manifestation', '09_evidence', '10_fixed_point')

# stamp: 02_inner_to_core

# stamp: 03_core_prepare

# stamp: 04_core_processing
BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow, ast.BitAnd: operator.and_, ast.BitOr: operator.or_, ast.BitXor: operator.xor, ast.LShift: operator.lshift, ast.RShift: operator.rshift}
UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Invert: operator.invert}

def evaluate_node(node, variables):
    if isinstance(node, ast.Expression):
        return evaluate_node(node.body, variables)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
        return BINARY[type(node.op)](evaluate_node(node.left, variables), evaluate_node(node.right, variables))
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
        return UNARY[type(node.op)](evaluate_node(node.operand, variables))
    raise ValueError('invalid-expression')

def evaluate_expression(expression, variables=None):
    if not expression or len(expression) > 256:
        raise ValueError('invalid-expression')
    value = evaluate_node(ast.parse(expression, mode='eval'), variables or {})
    if type(value) is not int:
        raise ValueError('integer-required')
    return value

# stamp: 05_core_collect
def present(value, base):
    integer = int(value)
    return {
        2: ('-' if integer < 0 else '') + bin(abs(integer))[2:],
        8: ('-' if integer < 0 else '') + oct(abs(integer))[2:],
        10: str(integer),
        16: ('-' if integer < 0 else '') + hex(abs(integer))[2:].upper(),
    }[base]

def calculate_case(case):
    return evaluate_expression(case['expression'], {})

ERRORS = {'division-by-zero': 'division-by-zero', 'invalid-expression': 'invalid-expression'}

def run_case(case):
    try:
        return {'result': present(calculate_case(case), case.get('base', 10)), 'error': None}
    except ZeroDivisionError:
        return {'result': None, 'error': 'division-by-zero'}
    except IndexError:
        return {'result': None, 'error': ERRORS.get('invalid-stack', 'invalid-expression')}
    except ValueError as error:
        return {'result': None, 'error': ERRORS.get(str(error), 'invalid-expression')}
    except (ArithmeticError, KeyError, SyntaxError, TypeError):
        return {'result': None, 'error': 'invalid-expression'}

def part(thing):
    result = run_case(thing['value'])
    return {'value': result, 'depths': TEN_DEPTHS, 'axes': tuple(thing.get('axes', ())), 'evidence': tuple(thing.get('evidence', ())) + ('boundary:inward', 'part:run_case', 'boundary:outward'), 'state': {True: 'valid', False: 'invalid'}[result.get('error') is None]}

# stamp: 06_core_to_inner
display = None
displayed_value = ''
mode_text = None
state = {'base': 10, 'expression': '', 'last': 0}

def visible_expression():
    visible = display.get()
    return visible if visible != displayed_value else state['expression']

def present_display(value):
    global displayed_value
    displayed_value = str(value)
    display.set(displayed_value)

def append(value):
    state['expression'] = visible_expression() + value
    present_display(state['expression'])

def clear():
    state['expression'] = ''
    present_display('')

def backspace():
    state['expression'] = visible_expression()[:-1]
    present_display(state['expression'])

def evaluate():
    state['expression'] = visible_expression()
    try:
        value = evaluate_expression(state['expression'], {})
        state['last'] = value
        state['expression'] = str(value)
        present_display(present(value, state['base']))
    except ZeroDivisionError:
        present_display('division-by-zero')
    except (ArithmeticError, SyntaxError, TypeError, ValueError):
        present_display('invalid-expression')

def set_base(value):
    state['base'] = int(value)
    mode_text.set(f'base {value}')
    present_display(present(state['last'], state['base']))

# stamp: 07_inner_to_outer
SELF_TEST_CONTROLS = [{'identity': 'command.base.16', 'label': 'HEX', 'row': 2, 'column': 0, 'action': 'base', 'value': '16'}, {'identity': 'command.base.10', 'label': 'DEC', 'row': 2, 'column': 1, 'action': 'base', 'value': '10'}, {'identity': 'command.base.8', 'label': 'OCT', 'row': 2, 'column': 2, 'action': 'base', 'value': '8'}, {'identity': 'command.base.2', 'label': 'BIN', 'row': 2, 'column': 3, 'action': 'base', 'value': '2'}, {'identity': 'operator.expression.shift-left', 'label': '<<', 'row': 2, 'column': 4, 'action': 'append', 'value': '<<'}, {'identity': 'operator.expression.shift-right', 'label': '>>', 'row': 2, 'column': 5, 'action': 'append', 'value': '>>'}, {'identity': 'operator.expression.bit-and', 'label': 'AND', 'row': 3, 'column': 0, 'action': 'append', 'value': '&'}, {'identity': 'operator.expression.bit-or', 'label': 'OR', 'row': 3, 'column': 1, 'action': 'append', 'value': '|'}, {'identity': 'operator.expression.bit-xor', 'label': 'XOR', 'row': 3, 'column': 2, 'action': 'append', 'value': '^'}, {'identity': 'operator.expression.bit-not', 'label': 'NOT', 'row': 3, 'column': 3, 'action': 'append', 'value': '~'}, {'identity': 'operator.expression.modulo', 'label': 'MOD', 'row': 3, 'column': 4, 'action': 'append', 'value': '%'}, {'identity': 'operator.expression.floor-divide', 'label': 'DIV', 'row': 3, 'column': 5, 'action': 'append', 'value': '//'}, {'identity': 'digit.7', 'label': '7', 'row': 4, 'column': 0, 'action': 'append', 'value': '7'}, {'identity': 'digit.8', 'label': '8', 'row': 4, 'column': 1, 'action': 'append', 'value': '8'}, {'identity': 'digit.9', 'label': '9', 'row': 4, 'column': 2, 'action': 'append', 'value': '9'}, {'identity': 'operator.expression.add', 'label': '+', 'row': 4, 'column': 3, 'action': 'append', 'value': '+'}, {'identity': 'operator.expression.subtract', 'label': '−', 'row': 4, 'column': 4, 'action': 'append', 'value': '-'}, {'identity': 'command.clear.compact', 'label': 'C', 'row': 4, 'column': 5, 'action': 'clear'}, {'identity': 'digit.4', 'label': '4', 'row': 5, 'column': 0, 'action': 'append', 'value': '4'}, {'identity': 'digit.5', 'label': '5', 'row': 5, 'column': 1, 'action': 'append', 'value': '5'}, {'identity': 'digit.6', 'label': '6', 'row': 5, 'column': 2, 'action': 'append', 'value': '6'}, {'identity': 'digit.1', 'label': '1', 'row': 5, 'column': 3, 'action': 'append', 'value': '1'}, {'identity': 'digit.2', 'label': '2', 'row': 5, 'column': 4, 'action': 'append', 'value': '2'}, {'identity': 'digit.3', 'label': '3', 'row': 5, 'column': 5, 'action': 'append', 'value': '3'}, {'identity': 'digit.0', 'label': '0', 'row': 6, 'column': 0, 'action': 'append', 'value': '0'}, {'identity': 'syntax.left', 'label': '(', 'row': 6, 'column': 1, 'action': 'append', 'value': '('}, {'identity': 'syntax.right', 'label': ')', 'row': 6, 'column': 2, 'action': 'append', 'value': ')'}, {'identity': 'command.backspace', 'label': '⌫', 'row': 6, 'column': 3, 'action': 'backspace'}, {'identity': 'operator.expression.multiply', 'label': '×', 'row': 6, 'column': 4, 'action': 'append', 'value': '*'}, {'identity': 'command.evaluate', 'label': '=', 'row': 6, 'column': 5, 'action': 'evaluate'}]

def build_interface():
    global display, mode_text
    root = Tk()
    root.title('Programmer Calculator')
    root.geometry('520x340+70+470')
    root.configure(bg='#101820')
    display = StringVar()
    mode_text = StringVar(value='integer · base 10 · bitwise')
    Entry(root, textvariable=display, font=('Menlo', 18), justify='right').grid(row=0, column=0, columnspan=6, sticky='nsew')
    Label(root, textvariable=mode_text, bg='#101820', fg='#f2aa4c').grid(row=1, column=0, columnspan=6, sticky='w')
    Button(root, text='HEX', command=lambda value='16': set_base(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=2, column=0, sticky='nsew')
    Button(root, text='DEC', command=lambda value='10': set_base(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=2, column=1, sticky='nsew')
    Button(root, text='OCT', command=lambda value='8': set_base(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=2, column=2, sticky='nsew')
    Button(root, text='BIN', command=lambda value='2': set_base(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=2, column=3, sticky='nsew')
    Button(root, text='<<', command=lambda value='<<': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=2, column=4, sticky='nsew')
    Button(root, text='>>', command=lambda value='>>': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=2, column=5, sticky='nsew')
    Button(root, text='AND', command=lambda value='&': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=3, column=0, sticky='nsew')
    Button(root, text='OR', command=lambda value='|': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=3, column=1, sticky='nsew')
    Button(root, text='XOR', command=lambda value='^': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=3, column=2, sticky='nsew')
    Button(root, text='NOT', command=lambda value='~': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=3, column=3, sticky='nsew')
    Button(root, text='MOD', command=lambda value='%': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=3, column=4, sticky='nsew')
    Button(root, text='DIV', command=lambda value='//': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=3, column=5, sticky='nsew')
    Button(root, text='7', command=lambda value='7': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=4, column=0, sticky='nsew')
    Button(root, text='8', command=lambda value='8': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=4, column=1, sticky='nsew')
    Button(root, text='9', command=lambda value='9': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=4, column=2, sticky='nsew')
    Button(root, text='+', command=lambda value='+': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=4, column=3, sticky='nsew')
    Button(root, text='−', command=lambda value='-': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=4, column=4, sticky='nsew')
    Button(root, text='C', command=clear, bg='#23313f', fg='#f2aa4c', width=7).grid(row=4, column=5, sticky='nsew')
    Button(root, text='4', command=lambda value='4': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=5, column=0, sticky='nsew')
    Button(root, text='5', command=lambda value='5': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=5, column=1, sticky='nsew')
    Button(root, text='6', command=lambda value='6': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=5, column=2, sticky='nsew')
    Button(root, text='1', command=lambda value='1': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=5, column=3, sticky='nsew')
    Button(root, text='2', command=lambda value='2': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=5, column=4, sticky='nsew')
    Button(root, text='3', command=lambda value='3': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=5, column=5, sticky='nsew')
    Button(root, text='0', command=lambda value='0': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=6, column=0, sticky='nsew')
    Button(root, text='(', command=lambda value='(': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=6, column=1, sticky='nsew')
    Button(root, text=')', command=lambda value=')': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=6, column=2, sticky='nsew')
    Button(root, text='⌫', command=backspace, bg='#23313f', fg='#f2aa4c', width=7).grid(row=6, column=3, sticky='nsew')
    Button(root, text='×', command=lambda value='*': append(value), bg='#23313f', fg='#f2aa4c', width=7).grid(row=6, column=4, sticky='nsew')
    Button(root, text='=', command=evaluate, bg='#23313f', fg='#f2aa4c', width=7).grid(row=6, column=5, sticky='nsew')
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)
    root.grid_columnconfigure(2, weight=1)
    root.grid_columnconfigure(3, weight=1)
    root.grid_columnconfigure(4, weight=1)
    root.grid_columnconfigure(5, weight=1)
    return root

def reset_interface():
    state.clear()
    state.update({'base': 10, 'expression': '', 'last': 0})
    state['expression'] = '1'
    present_display('1')
    mode_text.set('integer · base 10 · bitwise')

def self_test_prepare(control):
    reset_interface()
    if control['action'] == 'base':
        state['last'] = 1

def self_test_effect(control):
    checks = {
        'append': lambda: display.get() == '1' + control['value'],
        'clear': lambda: display.get() == '',
        'backspace': lambda: display.get() == '',
        'evaluate': lambda: display.get() == '1',
        'base': lambda: state['base'] == int(control['value']),
    }
    return checks[control['action']]()

def self_test_interface(root):
    results = []
    for control in SELF_TEST_CONTROLS:
        self_test_prepare(control)
        widgets = [item for item in root.grid_slaves(row=control['row'], column=control['column']) if item.winfo_class() == 'Button']
        try:
            widget = widgets[0] if len(widgets) == 1 else None
            widget.invoke()
            results.append(widget.cget('text') == control['label'] and self_test_effect(control))
        except Exception:
            results.append(False)
    reset_interface()
    display.set('12&10')
    state['expression'] = ''
    widgets = [item for item in root.grid_slaves(row=6, column=5) if item.winfo_class() == 'Button']
    widgets[0].invoke()
    results.append(display.get() == '8')
    reset_interface()
    return {'passed': sum(results), 'total': len(results)}

def self_test_application():
    root = build_interface()
    closed = False
    try:
        report = self_test_interface(root)
    finally:
        root.destroy()
        closed = True
    return {'self_test': report, 'closed': closed}

def launch():
    root = build_interface()
    report = self_test_interface(root)
    if report['passed'] != report['total']:
        root.destroy()
        raise RuntimeError('self-test-failed')
    root.mainloop()

def main(argv=None):
    arguments = list(sys.argv if argv is None else argv)
    if len(arguments) == 3 and arguments[1] == '--case':
        print(json.dumps(run_case(json.loads(arguments[2])), sort_keys=True))
        return 0
    if len(arguments) == 2 and arguments[1] == '--self-test':
        report = self_test_application()
        print(json.dumps(report, sort_keys=True))
        return 0 if report['closed'] and report['self_test']['passed'] == report['self_test']['total'] else 1
    launch()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
