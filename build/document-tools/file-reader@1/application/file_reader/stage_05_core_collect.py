"""Generated application stage 05."""

from .runtime import advance

SPECIALIZATION = {'index': 5, 'name': '05_core_collect', 'format': None}


def part(thing):
    return advance({
        **thing,
        "value": {**thing["value"], "_specialization": SPECIALIZATION},
    })
