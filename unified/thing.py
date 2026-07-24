"""Plain-data construction of a thing and a world."""

from __future__ import annotations

from typing import Any

THING_FIELDS = ("value", "depths", "axes", "evidence", "state")

STATES = frozenset(
    {
        "unknown",
        "absent",
        "false",
        "formed",
        "valid",
        "invalid",
    }
)


def is_thing(obj: Any) -> bool:
    """Return True when obj is a canonical five-field thing."""
    if not isinstance(obj, dict):
        return False
    if any(field not in obj for field in THING_FIELDS):
        return False
    if not isinstance(obj["depths"], tuple):
        return False
    if not isinstance(obj["axes"], tuple):
        return False
    if not isinstance(obj["evidence"], tuple):
        return False
    if obj["state"] not in STATES:
        return False
    return True


def _non_thing_result(raw: Any, mark: str) -> dict[str, Any]:
    return {
        "value": raw,
        "depths": (),
        "axes": (),
        "evidence": (mark,),
        "state": "invalid",
    }


def letter(thing):
    """Form the smallest distinguishable canonical thing.

    Accepts one canonical thing and returns one canonical thing (L1).
    Classifies value into distinct states (L6):
    - None  → absent
    - False → false
    - other → formed
    Non-thing input is rejected as invalid with evidence.
    """
    if not is_thing(thing):
        return _non_thing_result(thing, "letter:rejected-non-thing")

    value = thing["value"]
    if value is None:
        state = "absent"
        mark = "letter:absent"
    elif value is False:
        state = "false"
        mark = "letter:false"
    else:
        state = "formed"
        mark = "letter:distinguished"

    return {
        **thing,
        "evidence": (*thing["evidence"], mark),
        "state": state,
    }


def world(thing):
    """Mark a composition as a complete world.

    Accepts one canonical thing and returns one canonical thing.
    Non-thing input is rejected as invalid with evidence.
    """
    if not is_thing(thing):
        return _non_thing_result(thing, "world:rejected-non-thing")

    return {
        **thing,
        "evidence": (*thing["evidence"], "world:composed"),
    }
