"""Plain-data construction of a thing and a world."""

from typing import Any


def letter(thing):
    """Form the smallest distinguishable canonical thing."""
    return {
        "value": thing,
        "depths": (),
        "axes": (),
        "evidence": ("letter:distinguished",),
        "state": "formed",
    }


def world(thing):
    """Mark a verified composition as a complete world."""
    return {
        **thing,
        "evidence": (*thing["evidence"], "world:composed"),
    }
