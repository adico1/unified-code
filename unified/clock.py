"""Named clock boundary (L7) for integer-nanosecond duration measurement (L9).

Public operations accept one thing and return one thing. Wall time is read
only inside this module. Tests may supply a plain-data ``clock_feed`` of
integer nanosecond readings instead of the host clock.
"""

from __future__ import annotations

import time
from typing import Any

from .thing import is_thing

LIMIT_NS = 1_000_000_000


def clock_start(thing):
    """Record the start of a measured interval inside the thing."""
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("boundary:clock_start", "clock:rejected-non-thing"),
            "state": "invalid",
        }

    reading, value, clock_state = _read_ns(thing)
    if clock_state != "ok":
        return {
            **thing,
            "value": value,
            "evidence": (*thing["evidence"], "boundary:clock_start", f"clock:{clock_state}"),
            "state": clock_state if clock_state in {"unknown", "absent", "false", "invalid"} else "invalid",
        }

    clock = {
        "start_ns": reading,
        "end_ns": None,
        "duration_ns": None,
        "status": "running",
    }
    return {
        **thing,
        "value": _with_clock(value, clock),
        "evidence": (*thing["evidence"], "boundary:clock_start", "clock:started"),
        "state": thing["state"] if thing["state"] not in {"invalid"} else thing["state"],
    }


def clock_end(thing):
    """Record the end of a measured interval and duration_ns."""
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("boundary:clock_end", "clock:rejected-non-thing"),
            "state": "invalid",
        }

    value = thing["value"]
    if not isinstance(value, dict):
        return {
            **thing,
            "evidence": (*thing["evidence"], "boundary:clock_end", "clock:value-not-map"),
            "state": "invalid",
        }

    clock = value.get("clock")
    if clock is None:
        return {
            **thing,
            "evidence": (*thing["evidence"], "boundary:clock_end", "clock:absent-start"),
            "state": "absent",
        }
    if clock is False:
        return {
            **thing,
            "evidence": (*thing["evidence"], "boundary:clock_end", "clock:false-start"),
            "state": "false",
        }
    if not isinstance(clock, dict):
        return {
            **thing,
            "evidence": (*thing["evidence"], "boundary:clock_end", "clock:invalid-start"),
            "state": "invalid",
        }

    start_ns = clock.get("start_ns")
    if start_ns is None:
        return {
            **thing,
            "value": {
                **value,
                "clock": {
                    **clock,
                    "status": "unknown",
                    "end_ns": None,
                    "duration_ns": None,
                },
            },
            "evidence": (*thing["evidence"], "boundary:clock_end", "clock:unknown-start"),
            "state": "unknown",
        }
    if start_ns is False:
        return {
            **thing,
            "evidence": (*thing["evidence"], "boundary:clock_end", "clock:false-start-ns"),
            "state": "false",
        }
    if not isinstance(start_ns, int):
        return {
            **thing,
            "evidence": (*thing["evidence"], "boundary:clock_end", "clock:invalid-start-ns"),
            "state": "invalid",
        }

    reading, value, clock_state = _read_ns(thing)
    if clock_state != "ok":
        return {
            **thing,
            "value": value,
            "evidence": (*thing["evidence"], "boundary:clock_end", f"clock:{clock_state}"),
            "state": clock_state if clock_state in {"unknown", "absent", "false", "invalid"} else "invalid",
        }

    duration_ns = reading - start_ns
    if duration_ns < 0:
        return {
            **thing,
            "value": {
                **value,
                "clock": {
                    "start_ns": start_ns,
                    "end_ns": reading,
                    "duration_ns": None,
                    "status": "invalid",
                },
            },
            "evidence": (*thing["evidence"], "boundary:clock_end", "clock:negative-duration"),
            "state": "invalid",
        }

    return {
        **thing,
        "value": {
            **value,
            "clock": {
                "start_ns": start_ns,
                "end_ns": reading,
                "duration_ns": duration_ns,
                "status": "complete",
            },
        },
        "evidence": (
            *thing["evidence"],
            "boundary:clock_end",
            "clock:complete",
            f"clock:duration_ns:{duration_ns}",
        ),
        "state": "formed" if thing["state"] in {"unknown", "formed", "valid"} else thing["state"],
    }


def _read_ns(thing) -> tuple[Any, Any, str]:
    """Return (nanoseconds, updated_value, status).

    status is ``ok`` or a distinct L6 state name.
    """
    value = thing["value"]
    if not isinstance(value, dict):
        value = {"payload": value}

    if "clock_feed" in value:
        feed = value["clock_feed"]
        if feed is None:
            return None, value, "unknown"
        if feed is False:
            return False, value, "false"
        if not isinstance(feed, (list, tuple)):
            return None, value, "invalid"
        if len(feed) == 0:
            return None, value, "absent"
        head = feed[0]
        rest = tuple(feed[1:])
        if head is None:
            return None, {**value, "clock_feed": rest}, "unknown"
        if head is False:
            return False, {**value, "clock_feed": rest}, "false"
        if not isinstance(head, int):
            return None, {**value, "clock_feed": rest}, "invalid"
        return head, {**value, "clock_feed": rest}, "ok"

    # Host clock — only place wall time is read.
    return time.perf_counter_ns(), value, "ok"


def _with_clock(value: dict, clock: dict) -> dict:
    return {**value, "clock": clock}
