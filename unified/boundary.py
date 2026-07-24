"""Visible input/output boundary parts (L7).

Boundary parts are the only public operations that may admit a host value
that is not yet a canonical thing. They always return a canonical thing
and record the boundary crossing in evidence.
"""

from __future__ import annotations

from typing import Any

from .thing import THING_FIELDS, is_thing


def inward(thing):
    """Admit a host value into the kernel as a canonical unknown thing.

    - If `thing` is already canonical, re-enter it as state `unknown`
      and append boundary evidence.
    - If `thing` is a raw host value, wrap it into a canonical thing
      with state `unknown`.

    This is the visible input boundary (L7). Classification into
    absent/false/formed is performed later by `letter` (L6).
    """
    if is_thing(thing):
        return {
            **thing,
            "evidence": (*thing["evidence"], "boundary:inward"),
            "state": "unknown",
        }

    return {
        "value": thing,
        "depths": (),
        "axes": (),
        "evidence": ("boundary:inward",),
        "state": "unknown",
    }


def outward(thing):
    """Represent an output effect as part of the thing (L7).

    Does not print, write, or perform any host side effect. Records the
    outward boundary in evidence so a process host may render the result.
    """
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("boundary:outward", "outward:rejected-non-thing"),
            "state": "invalid",
        }

    return {
        **thing,
        "evidence": (*thing["evidence"], "boundary:outward"),
    }


def host_render(thing) -> str:
    """Process-host serialization helper.

    Not a kernel Part. Used only at the OS process edge after `outward`
    has already made the emission intent visible inside the thing.
    """
    from json import dumps

    if not is_thing(thing):
        payload = {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("host:render-non-thing",),
            "state": "invalid",
        }
        return dumps(payload, indent=2, ensure_ascii=False)

    return dumps(
        {field: thing[field] for field in THING_FIELDS},
        indent=2,
        ensure_ascii=False,
    )
