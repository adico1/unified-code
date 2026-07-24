"""Axes and dimensions assembled as nested code."""

from .depth import (
    above,
    bad,
    beginning,
    below,
    east,
    end,
    good,
    north,
    south,
    west,
)


def line(thing):
    return {
        **east(west(thing)),
        "axes": (*thing["axes"], ("west", "east")),
    }


def plane(thing):
    return {
        **north(south(line(thing))),
        "axes": (*thing["axes"], ("west", "east"), ("south", "north")),
    }


def space(thing):
    return {
        **above(below(plane(thing))),
        "axes": (
            *thing["axes"],
            ("west", "east"),
            ("south", "north"),
            ("below", "above"),
        ),
    }


def time(thing):
    return {
        **end(beginning(thing)),
        "axes": (*thing["axes"], ("beginning", "end")),
    }


def value(thing):
    return {
        **bad(good(thing)),
        "axes": (*thing["axes"], ("good", "bad")),
    }
