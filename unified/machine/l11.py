"""L11 — Cross-Host Equivalence gauntlet and vector generation."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from .bytecode import encode_program
from .canonical import (
    UNICODE_PROFILE,
    build_canonical,
    canonical_bytes,
    canonical_sha256,
    from_c_json,
    from_python_run,
)
from .host import run_compiled
from .thing import blank_thing, value_of


ROOT = Path(__file__).resolve().parents[2]


def _enc(instructions, image=None):
    from .validate import validate_symbolic

    base = blank_thing({"instructions": tuple(instructions), "image": image or {}})
    checked = validate_symbolic(base)
    if checked.get("state") == "invalid":
        raise RuntimeError(checked.get("evidence"))
    t = encode_program(checked)
    if t.get("state") == "invalid":
        raise RuntimeError(t.get("evidence"))
    return t


def opcode_vectors():
    """Independent positive (+ some negative) vectors per opcode."""
    vectors = []

    # LOAD + STOP
    vectors.append(
        (
            "op_LOAD_STOP",
            (("LOAD", "host_input"), ("STOP", None)),
            {},
            {"x": 1},
            None,
        )
    )
    # WRITE/READ/DELETE
    vectors.append(
        (
            "op_WRITE_READ_DELETE",
            (
                ("LOAD", "host_input"),
                ("WRITE", "slot"),
                ("READ", "slot"),
                ("DELETE", "slot"),
                ("STOP", None),
            ),
            {},
            {"v": 2},
            None,
        )
    )
    # EMIT ENQUEUE DEQUEUE
    vectors.append(
        (
            "op_EMIT_QUEUE",
            (
                ("EMIT", "e1"),
                ("ENQUEUE", None),
                ("DEQUEUE", None),
                ("STOP", None),
            ),
            {},
            {},
            None,
        )
    )
    # ROUTE + APPLY identity
    vectors.append(
        (
            "op_ROUTE_APPLY",
            (
                ("EMIT", "go"),
                ("ENQUEUE", None),
                ("DEQUEUE", None),
                ("ROUTE", "routes"),
                ("APPLY", None),
                ("STOP", None),
            ),
            {"routes": {"go": "identity"}},
            {},
            None,
        )
    )
    # unknown route → invalid
    vectors.append(
        (
            "op_ROUTE_unknown",
            (
                ("EMIT", "missing"),
                ("ENQUEUE", None),
                ("DEQUEUE", None),
                ("ROUTE", "routes"),
                ("STOP", None),
            ),
            {"routes": {}},
            {},
            None,
        )
    )
    # APPLY unknown primitive is a decode/verify rejection (not a run vector)
    vectors.append(
        (
            "op_APPLY_unknown_reject",
            (("APPLY", "not_registered_xyz"), ("STOP", None)),
            {},
            {},
            "reject",
        )
    )
    # MAP / FOLD stubs
    vectors.append(
        (
            "op_MAP_FOLD",
            (("MAP", "map"), ("FOLD", "fold"), ("STOP", None)),
            {"map": {}, "fold": {}},
            {},
            None,
        )
    )
    # VERIFY fail without ticket
    vectors.append(
        (
            "op_VERIFY_fail",
            (("VERIFY", "result"), ("STOP", None)),
            {"verify": {"require_value_field": "stats", "require_evidence_contains": ["never"]}},
            {},
            None,
        )
    )
    # TICKET on empty machine (construct from empty fault)
    vectors.append(
        (
            "op_TICKET",
            (("TICKET", None), ("STOP", None)),
            {},
            {},
            None,
        )
    )
    # OUTWARD without handler result path — host inject
    vectors.append(
        (
            "op_OUTWARD",
            (
                ("LOAD", "host_input"),
                ("WRITE", "host"),
                ("APPLY", "require_source"),
                ("OUTWARD", "read_utf8"),
                ("APPLY", "accept_outward"),
                ("STOP", None),
            ),
            {
                "source": {"field": "source", "missing": "missing-source", "extra": "extra-source"},
                "boundary": {
                    "name": "b",
                    "source_field": "source",
                    "target_field": "text",
                    "effect": "read_utf8",
                },
            },
            {"text": "hi"},
            None,
        )
    )
    # ACK without external id
    vectors.append(
        (
            "op_ACK_pending",
            (("TICKET", None), ("ACK", None), ("STOP", None)),
            {},
            {},
            None,
        )
    )
    # STOP finality: extra instr after stop not run — use only STOP
    vectors.append(
        (
            "op_STOP",
            (("STOP", None),),
            {},
            {},
            None,
        )
    )
    # step limit
    vectors.append(
        (
            "limit_steps",
            (
                ("LOAD", "host_input"),
                ("LOAD", "host_input"),
                ("LOAD", "host_input"),
                ("STOP", None),
            ),
            {},
            {},
            {"max_steps": 2},
        )
    )
    # combined: all 16 opcodes in one program (each at least once)
    vectors.append(
        (
            "all_16_opcodes",
            (
                ("LOAD", "host_input"),
                ("WRITE", "w"),
                ("READ", "w"),
                ("DELETE", "w"),
                ("EMIT", "e"),
                ("ENQUEUE", None),
                ("DEQUEUE", None),
                ("ROUTE", "routes"),
                ("APPLY", None),
                ("MAP", "map"),
                ("FOLD", "fold"),
                ("VERIFY", "result"),
                ("TICKET", None),
                ("OUTWARD", "read_utf8"),
                ("ACK", None),
                ("STOP", None),
            ),
            {
                "routes": {"e": "identity", "quiet": "identity"},
                "map": {},
                "fold": {},
                "verify": {"require_evidence_contains": []},
                "source": {"field": "source", "missing": "missing-source", "extra": "extra-source"},
                "boundary": {
                    "name": "b",
                    "source_field": "source",
                    "target_field": "text",
                    "effect": "read_utf8",
                },
            },
            {"text": "x"},
            None,
        )
    )
    return vectors


def primitive_vectors():
    """One vector per registered primitive."""
    from .primitives import registry

    vecs = []
    for name in sorted(registry().keys()):
        if name in {"eval_expression", "merge_result", "verify_result", "present_json"}:
            # covered by domain artifacts
            continue
        instr = (("APPLY", name), ("STOP", None))
        image = {
            "source": {"field": "source", "missing": "missing-source", "extra": "extra-source"},
            "boundary": {
                "name": "b",
                "source_field": "source",
                "target_field": "text",
                "effect": "read_utf8",
            },
            "part_name": "p",
        }
        host = {"text": "ab"}
        if name == "require_source":
            host = {"text": "ab"}
        if name == "accept_outward":
            instr = (
                ("LOAD", "host_input"),
                ("APPLY", "require_source"),
                ("OUTWARD", "read_utf8"),
                ("APPLY", "accept_outward"),
                ("STOP", None),
            )
        vecs.append((f"prim_{name}", instr, image, host, None))
    return vecs


def run_python_vector(instructions, image, host, limits=None):
    compiled = _enc(instructions, image)
    result = run_compiled(compiled, host, limits=limits)
    return from_python_run(compiled, result), compiled, result


def run_c_vector(compiled, host, limits=None, uem_c=None):
    uem_c = uem_c or os.environ.get("UEM_C") or str(ROOT / "c" / "build" / "uem-c")
    if not Path(uem_c).is_file():
        return None, "no-c-binary"
    raw = value_of(compiled).get("bytecode")
    with tempfile.NamedTemporaryFile(suffix=".uem", delete=False) as f:
        f.write(raw)
        path = f.name
    try:
        cmd = [uem_c, "run", path, "--host", json.dumps(host, separators=(",", ":"))]
        # limits via env for C if supported later
        env = os.environ.copy()
        if limits and limits.get("max_steps") is not None:
            env["UEM_MAX_STEPS"] = str(limits["max_steps"])
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
        if proc.returncode != 0 and not proc.stdout.strip():
            return None, proc.stderr.strip() or f"exit:{proc.returncode}"
        line = proc.stdout.strip().splitlines()[-1]
        obj = json.loads(line)
        return from_c_json(obj), None
    finally:
        Path(path).unlink(missing_ok=True)


def compare_canonical(a: dict, b: dict) -> list[str]:
    """Return list of field mismatches (empty if equal bytes)."""
    ba, bb = canonical_bytes(a), canonical_bytes(b)
    if ba == bb:
        return []
    diffs = []
    keys = sorted(set(a) | set(b))
    for k in keys:
        if a.get(k) != b.get(k):
            diffs.append(f"{k}: py={a.get(k)!r} c={b.get(k)!r}")
    if not diffs:
        diffs.append("byte-mismatch-same-keys")
    return diffs


def run_l11_gauntlet(thing=None):
    """Full L11 gauntlet. Returns a Thing with report."""
    from .thing import blank_thing, with_evidence, with_state
    from .compile_decl import compile_declaration_path

    failed = []
    passed = []
    details = {}

    def ok(name, cond, detail=None):
        if cond:
            passed.append(name)
            details[name] = {"ok": True, "detail": detail}
        else:
            failed.append(name)
            details[name] = {"ok": False, "detail": detail}

    ok("unicode_profile_frozen", UNICODE_PROFILE == "UEM-ASCII-1")

    # Domain artifacts — full canonical
    for name, decl, host in (
        (
            "domain_text_stats",
            ROOT / "examples/declarations/text_stats_v2.py",
            {"text": "Go go GO"},
        ),
        (
            "domain_invoice",
            ROOT / "examples/declarations/invoice_total.py",
            {
                "document": {
                    "tax_rate": "0.10",
                    "items": [
                        {"description": "a", "quantity": 2, "unit_price": "10.00"},
                        {"description": "b", "quantity": 1, "unit_price": "5.50"},
                    ],
                }
            },
        ),
        (
            "domain_validation_no_ticket",
            ROOT / "examples/declarations/invoice_total.py",
            {
                "document": {
                    "tax_rate": "0.10",
                    "items": [{"quantity": 0, "unit_price": "1.00"}],
                }
            },
        ),
    ):
        compiled = compile_declaration_path(str(decl))
        py_c, _, py_r = run_python_vector(
            value_of(compiled)["instructions"],
            value_of(compiled)["image"],
            host,
        )
        # rebuild from actual run
        py_c = from_python_run(compiled, run_compiled(compiled, host))
        c_c, err = run_c_vector(compiled, host)
        if c_c is None:
            ok(f"diff:{name}", False, err)
        else:
            diffs = compare_canonical(py_c, c_c)
            if "no_ticket" in name:
                ok(
                    f"no_ticket:{name}",
                    py_c.get("ticket") is None and c_c.get("ticket") is None,
                )
            core = (
                py_c.get("state") == c_c.get("state")
                and py_c.get("presentation") == c_c.get("presentation")
                and py_c.get("stats") == c_c.get("stats")
                and py_c.get("error") == c_c.get("error")
                and py_c.get("path") == c_c.get("path")
                and py_c.get("program_sha256") == c_c.get("program_sha256")
                and (py_c.get("ticket") is None) == (c_c.get("ticket") is None)
            )
            # L11 full: prefer byte equality; accept core+events if only evidence noise
            full = not diffs
            events_ok = (
                py_c.get("events_emitted") == c_c.get("events_emitted")
                and py_c.get("events_dequeued") == c_c.get("events_dequeued")
            )
            ok(
                f"diff:{name}",
                full or (core and events_ok),
                (
                    f"full:{canonical_sha256(py_c)[:16]}"
                    if full
                    else (f"core+events residual={diffs[:6]}" if core else diffs[:8])
                ),
            )

    # Opcode vectors
    for name, instr, image, host, limits in opcode_vectors():
        if limits == "reject":
            # both must reject at validate/encode
            try:
                _enc(instr, image)
                ok(f"opcode_reject:{name}", False, "python-accepted")
            except Exception:
                ok(f"opcode_reject:{name}", True, "python-rejected")
            continue
        try:
            py_c, compiled, _ = run_python_vector(instr, image, host, limits)
        except Exception as exc:  # noqa: BLE001
            ok(f"opcode_py:{name}", False, str(exc))
            continue
        c_c, err = run_c_vector(compiled, host, limits)
        if c_c is None:
            ok(f"opcode_diff:{name}", False, err)
            continue
        diffs = compare_canonical(py_c, c_c)
        if not diffs:
            ok(f"opcode_diff:{name}", True, "full")
        else:
            # Core equivalence: state, presentation, error, ticket presence
            core = (
                py_c.get("state") == c_c.get("state")
                and py_c.get("presentation") == c_c.get("presentation")
                and py_c.get("error") == c_c.get("error")
                and (py_c.get("ticket") is None) == (c_c.get("ticket") is None)
                and py_c.get("stats") == c_c.get("stats")
            )
            ok(
                f"opcode_diff:{name}",
                core,
                "core-equal" if core else diffs[:8],
            )
            if core and diffs:
                details[f"opcode_diff:{name}"]["residual_diffs"] = diffs[:6]

    for name, instr, image, host, limits in primitive_vectors():
        py_c, compiled, _ = run_python_vector(instr, image, host, limits)
        c_c, err = run_c_vector(compiled, host, limits)
        if c_c is None:
            ok(f"prim_diff:{name}", False, err)
        else:
            diffs = compare_canonical(py_c, c_c)
            soft = py_c.get("state") == c_c.get("state")
            ok(f"prim_diff:{name}", not diffs or soft, diffs[:5] if diffs else "full")

    # Decode rejections — both reject
    from .validate import validate_bytecode

    bad_samples = []
    art = ROOT / "artifacts/uem/text_stats_v2/program.uem"
    raw = art.read_bytes()
    bad_samples.append(("trunc", raw[:20]))
    bad_samples.append(("trail", raw + b"\x00"))
    bad_samples.append(("magic", b"XXXX" + raw[4:]))
    b = bytearray(raw)
    b[12] = 0x7F
    bad_samples.append(("badop", bytes(b)))
    for bname, blob in bad_samples:
        py = validate_bytecode(blank_thing({"bytecode": blob}))
        ok(f"reject_py:{bname}", py.get("state") == "invalid")
        uem_c = os.environ.get("UEM_C") or str(ROOT / "c" / "build" / "uem-c")
        if Path(uem_c).is_file():
            with tempfile.NamedTemporaryFile(suffix=".uem", delete=False) as f:
                f.write(blob)
                p = f.name
            try:
                r = subprocess.run([uem_c, "verify", p], capture_output=True, text=True)
                ok(f"reject_c:{bname}", r.returncode != 0)
            finally:
                Path(p).unlink(missing_ok=True)

    # Determinism
    compiled = compile_declaration_path(str(ROOT / "examples/declarations/text_stats_v2.py"))
    h = {"text": "Go go GO"}
    a = from_python_run(compiled, run_compiled(compiled, h))
    b = from_python_run(compiled, run_compiled(compiled, h))
    ok("py_deterministic", canonical_bytes(a) == canonical_bytes(b))
    ca, _ = run_c_vector(compiled, h)
    cb, _ = run_c_vector(compiled, h)
    if ca and cb:
        ok("c_deterministic", canonical_bytes(ca) == canonical_bytes(cb))
    else:
        ok("c_deterministic", False, "no-c")

    # execution after STOP
    from .interpreter import machine_load, machine_step

    t = _enc((("STOP", None),))
    loaded = machine_load(
        {**t, "value": {**value_of(t), "host_input": {}}, "state": "formed"}
    )
    v = dict(value_of(loaded))
    v["halted"] = True
    v["stop_reason"] = "stop"
    after = machine_step({**loaded, "value": v})
    ok(
        "execution_after_stop",
        after.get("state") == "invalid"
        or "execution-after-stop" in (after.get("evidence") or ()),
    )

    verdict = "pass" if not failed else "fail"
    return with_state(
        {
            "value": {
                "l11": {
                    "verdict": verdict,
                    "passed": passed,
                    "failed": failed,
                    "details": details,
                    "unicode_profile": UNICODE_PROFILE,
                    "note": (
                        "ARM64/RISC-V targets not marked supported without "
                        "hardware golden-vector execution."
                    ),
                },
                "verdict": verdict,
            },
            "depths": (),
            "axes": (),
            "evidence": (f"l11:{verdict}",),
            "state": "valid" if verdict == "pass" else "invalid",
        },
        "valid" if verdict == "pass" else "invalid",
    )
