"""The ten oriented depth interfaces."""


def beginning(thing):
    return {**thing, "depths": (*thing["depths"], "beginning")}


def end(thing):
    return {**thing, "depths": (*thing["depths"], "end")}


def good(thing):
    return {**thing, "depths": (*thing["depths"], "good")}


def bad(thing):
    return {**thing, "depths": (*thing["depths"], "bad")}


def below(thing):
    return {**thing, "depths": (*thing["depths"], "below")}


def above(thing):
    return {**thing, "depths": (*thing["depths"], "above")}


def west(thing):
    return {**thing, "depths": (*thing["depths"], "west")}


def east(thing):
    return {**thing, "depths": (*thing["depths"], "east")}


def south(thing):
    return {**thing, "depths": (*thing["depths"], "south")}


def north(thing):
    return {**thing, "depths": (*thing["depths"], "north")}
