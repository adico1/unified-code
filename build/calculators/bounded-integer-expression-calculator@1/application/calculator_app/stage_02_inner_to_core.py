"""Generated application stage 02."""

from .runtime import advance

SPECIALIZATION = {'index': 2, 'name': '02_inner_to_core', 'boundaries': {'dependency': 'generated-library', 'acceptance_deadline_seconds': 10}}


def part(thing):
    return advance({
        **thing,
        "value": {**thing["value"], "_specialization": SPECIALIZATION},
    })
