"""Verification that returns evidence inside the thing."""


def verify(thing):
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
