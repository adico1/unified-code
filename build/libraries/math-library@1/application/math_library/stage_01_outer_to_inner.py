"""Generated application stage 01."""

from .runtime import advance

SPECIALIZATION = {'index': 1, 'name': '01_outer_to_inner', 'format': 'json-object'}


def part(thing):
    return advance({
        **thing,
        "value": {**thing["value"], "_specialization": SPECIALIZATION},
    })
