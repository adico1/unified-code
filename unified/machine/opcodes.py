"""UEM-16 opcode table — fixed bytes, no domain vocabulary."""

from __future__ import annotations

from generated.uem_surface.unified.machine.generated_surface import (
    DEFAULT_LIMITS,
    FORMAT_VERSION,
    MAGIC,
    OPCODES,
    TAG_NONE,
    TAG_STRING,
)

NAME_TO_BYTE = {name: code for code, name in OPCODES.items()}
