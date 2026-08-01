"""Generated application stage 04."""

from .runtime import advance

SPECIALIZATION = {'index': 4, 'name': '04_core_processing', 'program': {'engine': 'expression', 'operations': {'evaluate': {'primitive': 'infix_evaluate'}}, 'operators': {'+': 'add', '-': 'subtract', '*': 'multiply', '/': 'divide', '%': 'remainder', '^': 'power', 'unary': 'negate'}, 'precedence': {'+': 1, '-': 1, '*': 2, '/': 2, '%': 2, '^': 3, 'unary': 4}}, 'dependency': {'application': 'math-library', 'interface': 'library'}, 'resolved_dependency_identity': 'e962f575d085938a4a9ddf03173f320fc28951c14ae02d4cc284e3501dffe167'}


def part(thing):
    return advance({
        **thing,
        "value": {**thing["value"], "_specialization": SPECIALIZATION},
    })
