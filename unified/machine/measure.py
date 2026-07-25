"""UEM measurements — compile/decode/execute timing and sizes."""

from __future__ import annotations

import ast
import statistics
import time
from pathlib import Path

from .bytecode import decode_program
from .compile_decl import compile_declaration_path
from .host import run_compiled
from .thing import approx_size, value_of


def measure_uem(thing):
    """Thing in: value.declaration_paths list → measurement report."""
    value = dict(value_of(thing) if isinstance(thing.get("value"), dict) else {})
    paths = value.get("declaration_paths") or []
    iterations = int(value.get("iterations") or 20)
    reports = []
    for path in paths:
        reports.append(_measure_one(str(path), iterations))
    cf = _cf_by_layer()
    return {
        **thing,
        "value": {
            **value,
            "measurements": reports,
            "control_flow_by_layer": cf,
        },
        "evidence": (*tuple(thing.get("evidence") or ()), "measure:uem"),
        "state": "valid",
    }


def _measure_one(path, iterations):
    compile_ns = []
    decode_ns = []
    exec_ns = []
    compiled = None
    for i in range(iterations):
        t0 = time.perf_counter_ns()
        compiled = compile_declaration_path(path)
        t1 = time.perf_counter_ns()
        compile_ns.append(t1 - t0)
        if compiled.get("state") == "invalid":
            break
        t0 = time.perf_counter_ns()
        dec = decode_program(compiled)
        t1 = time.perf_counter_ns()
        decode_ns.append(t1 - t0)
        host = _sample_host(value_of(compiled).get("image") or {})
        t0 = time.perf_counter_ns()
        run_compiled(compiled, host)
        t1 = time.perf_counter_ns()
        exec_ns.append(t1 - t0)
    v = value_of(compiled) if compiled else {}
    peak = approx_size(v)
    return {
        "declaration": path,
        "bytecode_size": v.get("bytecode_size"),
        "program_sha256": v.get("program_sha256"),
        "instruction_count": len(v.get("instructions") or ()),
        "compile_p95_ns": _p95(compile_ns),
        "decode_p95_ns": _p95(decode_ns),
        "execution_p95_ns": _p95(exec_ns),
        "peak_state_size": peak,
        "event_count_note": "linear program; events via EMIT when used",
    }


def _sample_host(image):
    b = image.get("boundary") or {}
    if b.get("effect") == "read_json":
        return {"document": {"tax_rate": "0.10", "items": []}}
    return {"text": "hello"}


def _p95(samples):
    if not samples:
        return None
    s = sorted(samples)
    idx = max(0, int((len(s) - 1) * 0.95))
    return s[idx]


def _cf_by_layer():
    root = Path(__file__).resolve().parents[1]
    machine = root / "machine"
    generator = root / "generator"
    counts = {
        "machine": _count_dir(machine),
        "generator": _count_dir(generator),
        "kernel_non_machine": _count_dir(root, skip={"machine", "generator"}),
    }
    return counts


def _count_dir(path: Path, skip=None):
    skip = skip or set()
    total = 0
    detail = {}
    if not path.is_dir():
        return {"total": 0}
    for p in path.rglob("*.py"):
        if any(part in skip for part in p.parts):
            continue
        c = _count_file(p)
        detail[p.name] = c
        total += c.get("total", 0)
    return {"total": total, "files": detail}


def _count_file(path: Path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return {"total": 0}
    names = (
        "If",
        "For",
        "While",
        "Match",
        "Try",
        "ListComp",
        "SetComp",
        "DictComp",
        "GeneratorExp",
    )
    counts = {n: 0 for n in names}
    for node in ast.walk(tree):
        n = type(node).__name__
        if n in counts:
            counts[n] += 1
    counts["total"] = sum(counts[n] for n in names)
    return counts
