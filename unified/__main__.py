"""Executable demonstration.

Kernel composition uses only Part-shaped operations. Host printing is
outside the kernel and runs only after `outward` records the effect.
"""

from .boundary import host_render, inward, outward
from .dimension import space
from .thing import letter, world
from .verify import verify


def main(thing):
    """Compose a 3D verified world with visible inward/outward boundaries."""
    return outward(world(verify(space(letter(inward(thing))))))


if __name__ == "__main__":
    # Process host edge: render a thing that already carries boundary:outward.
    rendered = host_render(main("seed"))
    # Host-only emission after the kernel represented the effect (L7).
    print(rendered)
