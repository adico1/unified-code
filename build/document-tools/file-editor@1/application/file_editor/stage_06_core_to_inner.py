"""Generated application stage 06."""

from .runtime import advance

SPECIALIZATION = {'index': 6, 'name': '06_core_to_inner', 'format': None}


def part(thing):
    return advance({
        **thing,
        "value": {**thing["value"], "_specialization": SPECIALIZATION},
    })
