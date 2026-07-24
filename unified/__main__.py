"""Executable demonstration."""

from json import dumps

from .dimension import space
from .thing import letter, world
from .verify import verify


def main(thing):
    return world(verify(space(letter(thing))))


if __name__ == "__main__":
    print(dumps(main("seed"), indent=2, ensure_ascii=False))
