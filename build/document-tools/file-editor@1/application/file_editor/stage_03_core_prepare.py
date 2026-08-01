"""Generated application stage 03."""

from .runtime import advance

SPECIALIZATION = {'index': 3, 'name': '03_core_prepare', 'persistence': {'mode': 'declared-resource'}}


def part(thing):
    return advance({
        **thing,
        "value": {**thing["value"], "_specialization": SPECIALIZATION},
    })
