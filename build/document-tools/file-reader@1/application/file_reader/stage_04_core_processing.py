"""Generated application stage 04."""

from .runtime import advance

SPECIALIZATION = {'index': 4, 'name': '04_core_processing', 'program': {'engine': 'document', 'operations': {'read': {'primitive': 'bytes_load'}}, 'encoding': 'utf-8'}, 'dependency': None, 'resolved_dependency_identity': None}


def part(thing):
    return advance({
        **thing,
        "value": {**thing["value"], "_specialization": SPECIALIZATION},
    })
