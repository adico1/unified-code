"""UEM-16 opcode table — fixed bytes, no domain vocabulary."""

from __future__ import annotations

# Byte → name
OPCODES = {
    0x01: "LOAD",
    0x02: "READ",
    0x03: "WRITE",
    0x04: "DELETE",
    0x05: "EMIT",
    0x06: "ENQUEUE",
    0x07: "DEQUEUE",
    0x08: "ROUTE",
    0x09: "APPLY",
    0x0A: "MAP",
    0x0B: "FOLD",
    0x0C: "VERIFY",
    0x0D: "TICKET",
    0x0E: "OUTWARD",
    0x0F: "ACK",
    0x10: "STOP",
}

NAME_TO_BYTE = {name: code for code, name in OPCODES.items()}

MAGIC = b"UEM\x16"
FORMAT_VERSION = 1
TAG_NONE = 0
TAG_STRING = 1

DEFAULT_LIMITS = {
    "max_steps": 100_000,
    "max_queue": 10_000,
    "max_depth": 64,
    "max_items": 1_000_000,
    "max_memory": 8_000_000,
    "max_output": 2_000_000,
}
