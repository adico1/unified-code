"""Generated application stage 04."""

from .runtime import advance

SPECIALIZATION = {'index': 4, 'name': '04_core_processing', 'program': {'engine': 'numeric', 'range': [-1000000, 1000000], 'numeric_grammar': {'type': 'integer', 'syntax': 'json-integer', 'boolean': 'rejected'}, 'result_rules': {'division': 'floor', 'overflow': 'reject'}, 'representation': 'canonical-json', 'exported_contract': 'part(thing)->thing', 'operations': {'add': {'primitive': 'plus', 'arity': 2}, 'subtract': {'primitive': 'minus', 'arity': 2}, 'multiply': {'primitive': 'times', 'arity': 2}, 'divide': {'primitive': 'quotient', 'arity': 2}, 'remainder': {'primitive': 'residue', 'arity': 2}, 'power': {'primitive': 'exponent', 'arity': 2}, 'absolute': {'primitive': 'magnitude', 'arity': 1}, 'negate': {'primitive': 'negative', 'arity': 1}, 'minimum': {'primitive': 'lowest', 'arity': 2}, 'maximum': {'primitive': 'highest', 'arity': 2}, 'sum': {'primitive': 'sum_many', 'arity': 3}}}, 'dependency': None, 'resolved_dependency_identity': None}


def part(thing):
    return advance({
        **thing,
        "value": {**thing["value"], "_specialization": SPECIALIZATION},
    })
