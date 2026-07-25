"""Validate symbolic programs and bytecode before execution."""

from __future__ import annotations

from .bytecode import decode_program
from .opcodes import NAME_TO_BYTE
from .primitives import registry
from .thing import blank_thing, with_evidence, with_state


def validate_symbolic(thing):
    """value.instructions + optional image → formed or invalid."""
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    instructions = value.get("instructions")
    if not isinstance(instructions, (list, tuple)) or len(instructions) == 0:
        return with_state(with_evidence(thing, "validate:empty-program"), "invalid")
    has_stop = False
    reg = registry()
    index = 0
    while index < len(instructions):
        item = instructions[index]
        index += 1
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            return with_state(with_evidence(thing, "validate:bad-instr"), "invalid")
        name, operand = item[0], item[1]
        if name not in NAME_TO_BYTE:
            return with_state(
                with_evidence(thing, f"validate:unknown-opcode:{name}"),
                "invalid",
            )
        if operand is not None and not isinstance(operand, str):
            return with_state(with_evidence(thing, "validate:operand-type"), "invalid")
        # L11: APPLY with explicit primitive name must be in registry
        if name == "APPLY" and operand is not None and operand not in reg:
            return with_state(
                with_evidence(thing, f"validate:unknown-primitive:{operand}"),
                "invalid",
            )
        if name == "STOP":
            has_stop = True
    if not has_stop:
        return with_state(with_evidence(thing, "validate:missing-stop"), "invalid")
    image = value.get("image")
    if image is not None and not isinstance(image, dict):
        return with_state(with_evidence(thing, "validate:image-type"), "invalid")
    return with_evidence(
        {**thing, "state": "formed"},
        "validate:symbolic:ok",
    )


def validate_bytecode(thing):
    """Decode + structural checks; rejects noncanonical encodings."""
    decoded = decode_program(thing)
    if decoded.get("state") == "invalid":
        return decoded
    return validate_symbolic(decoded)
