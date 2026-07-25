"""Machine Thing helpers — plain data only."""

from __future__ import annotations

import copy
import json

THING_FIELDS = ("value", "depths", "axes", "evidence", "state")
STATES = frozenset({"unknown", "absent", "false", "formed", "valid", "invalid"})


def is_machine_thing(thing):
    if not isinstance(thing, dict):
        return False
    for field in THING_FIELDS:
        if field not in thing:
            return False
    if not isinstance(thing["depths"], tuple):
        return False
    if not isinstance(thing["axes"], tuple):
        return False
    if not isinstance(thing["evidence"], tuple):
        return False
    if thing["state"] not in STATES:
        return False
    return True


def blank_thing(value=None, state="formed"):
    return {
        "value": value if value is not None else {},
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": state,
    }


def with_evidence(thing, *marks):
    return {
        **thing,
        "evidence": (*tuple(thing.get("evidence") or ()), *marks),
    }


def with_state(thing, state):
    return {**thing, "state": state}


def value_of(thing):
    v = thing.get("value")
    return v if isinstance(v, dict) else {}


def set_value(thing, value):
    return {**thing, "value": value}


def deep_copy_data(obj):
    return copy.deepcopy(obj)


def approx_size(obj):
    try:
        return len(
            json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)
        )
    except (TypeError, ValueError):
        return 0
