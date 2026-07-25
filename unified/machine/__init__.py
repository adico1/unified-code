"""Unified Event Machine UEM-16 v0.1 — chip-neutral foundation.

Public surface: Thing → Thing functions only. No user-defined classes.
"""

from .bytecode import decode_program, encode_program, program_identity
from .compile_decl import compile_declaration
from .gauntlet import run_uem_gauntlet
from .host import run_program
from .interpreter import machine_load, machine_run, machine_step
from .l11 import run_l11_gauntlet
from .measure import measure_uem
from .validate import validate_bytecode, validate_symbolic

__all__ = [
    "compile_declaration",
    "decode_program",
    "encode_program",
    "machine_load",
    "machine_run",
    "machine_step",
    "measure_uem",
    "program_identity",
    "run_l11_gauntlet",
    "run_program",
    "run_uem_gauntlet",
    "validate_bytecode",
    "validate_symbolic",
]
