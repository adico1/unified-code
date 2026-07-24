"""Verification that returns evidence inside the thing."""

from .thing import is_thing


def verify(thing):
    """Check dimensional completeness; never map unknown/absent/false to each other.

    Verdict states are only `valid` or `invalid`. L6 requires that
    unknown, absent, and false remain distinct from invalid and from
    each other; this operation does not collapse them into false.
    """
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("verify:rejected-non-thing",),
            "state": "invalid",
        }

    axes = thing["axes"]
    depths = thing["depths"]
    expected = tuple(depth for axis in axes for depth in axis)
    valid = len(depths) == 2 * len(axes) and depths == expected

    return {
        **thing,
        "evidence": (
            *thing["evidence"],
            f"axes:{len(axes)}",
            f"depths:{len(depths)}",
            f"dimension-law:{'pass' if valid else 'fail'}",
        ),
        "state": "valid" if valid else "invalid",
    }
