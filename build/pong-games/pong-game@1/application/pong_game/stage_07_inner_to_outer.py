"""Generated application stage 07."""

from .runtime import advance

SPECIALIZATION = {'index': 7, 'name': '07_inner_to_outer', 'format': 'frame-state'}


def part(thing):
    return advance({
        **thing,
        "value": {**thing["value"], "_specialization": SPECIALIZATION},
    })
