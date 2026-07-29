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
from .compile_decl import compile_declaration_path
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
    from .thing import blank_thing, with_state

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
            ROOT / "examples/declarations/text_stats_v2.json",
            {"text": "Go go GO"},
        ),
        (
            "domain_invoice",
            ROOT / "examples/declarations/invoice_total.json",
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
            ROOT / "examples/declarations/invoice_total.json",
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
            # L11 strict: full canonical byte equality required
            full = not diffs
            ok(
                f"diff:{name}",
                full,
                f"full:{canonical_sha256(py_c)[:16]}" if full else diffs[:12],
            )

    # Stateful application semantics — same seed-defined command table, state,
    # command, and raw arguments independently executed by both hosts.
    for seed_path in sorted((ROOT / "seed/declarations").glob("*.json")):
        declaration = json.loads(seed_path.read_text(encoding="utf-8"))
        transitions = [
            feature["transformation"]
            for feature in declaration.get("features") or ()
            if (feature.get("transformation") or {}).get("kind")
            == "stateful_resource"
        ]
        if not transitions:
            continue
        transition = transitions[0]
        image = {
            "stateful": {"commands": transition["commands"]},
            "verify": {
                "require_value_field": "stats",
                "require_evidence_contains": [],
            },
        }
        compiled = _enc(
            (
                ("APPLY", "state_transition"),
                ("VERIFY", "result"),
                ("STOP", None),
            ),
            image,
        )
        state = json.loads(json.dumps(transition["state"]["initial"]))
        all_cases = [
            *[(case, True) for case in transition.get("acceptance") or ()],
            *[(case, False) for case in transition.get("rejections") or ()],
        ]
        for index, (case, sequential) in enumerate(all_cases):
            before = state if sequential else json.loads(
                json.dumps(transition["state"]["initial"])
            )
            argv = list(case.get("argv") or ())
            host = {
                "resource_state": before,
                "command": argv[0] if argv else None,
                "arguments": argv[1:],
            }
            py_c = from_python_run(compiled, run_compiled(compiled, host))
            c_c, err = run_c_vector(compiled, host)
            vector_name = f"stateful:{seed_path.stem}:{index}"
            if c_c is None:
                ok(f"diff:{vector_name}", False, err)
                continue
            diffs = compare_canonical(py_c, c_c)
            envelope = py_c.get("stats") or {}
            expected = case.get("expect") or {}
            rejected = int(case.get("exit", 0)) != 0
            semantic = (
                envelope.get("resource_state") == before
                and envelope.get("state_changed") is False
                and envelope.get("error") == expected.get("error")
                and py_c.get("ticket") is None
                and c_c.get("ticket") is None
            ) if rejected else (
                envelope.get("error") is None
                and envelope.get("result") == expected
            )
            ok(
                f"diff:{vector_name}",
                not diffs and semantic,
                f"full:{canonical_sha256(py_c)[:16]}"
                if not diffs and semantic
                else (diffs[:8] or ["semantic-mismatch"]),
            )
            if sequential and not rejected:
                state = envelope.get("resource_state")

    # Frozen scalar profile — the same boundary values are parsed independently
    # by Python UEM and C UEM before any application guard or action runs.
    scalar_image = {
        "stateful": {
            "commands": {
                "integer": {
                    "arguments": [{"name": "value", "type": "integer"}],
                    "guards": [],
                    "actions": [],
                    "result": {"$arg": "value"},
                },
                "non-empty": {
                    "arguments": [
                        {
                            "name": "value",
                            "type": "string",
                            "non_empty": True,
                        }
                    ],
                    "guards": [],
                    "actions": [],
                    "result": {"$arg": "value"},
                },
            }
        },
        "verify": {
            "require_value_field": "stats",
            "require_evidence_contains": [],
        },
    }
    scalar_compiled = _enc(
        (
            ("APPLY", "state_transition"),
            ("VERIFY", "result"),
            ("STOP", None),
        ),
        scalar_image,
    )
    scalar_vectors = (
        *(
            ("integer", raw, expected, None)
            for raw, expected in (
                ("0", 0),
                ("-0", 0),
                ("1", 1),
                ("-1", -1),
                ("999999999999999", 999999999999999),
                ("-999999999999999", -999999999999999),
            )
        ),
        *(
            ("integer", raw, None, "invalid-argument")
            for raw in (
                "",
                "+1",
                " 1",
                "1 ",
                "01",
                "-01",
                "1_000",
                "١",
                "1000000000000000",
                "-1000000000000000",
                "9999999999999999",
                "10000000000000000",
            )
        ),
        ("non-empty", "", None, "invalid-argument"),
        ("non-empty", " \t\n\v\f\r", None, "invalid-argument"),
        ("non-empty", "\u00a0", "\u00a0", None),
        ("non-empty", "\u2003", "\u2003", None),
        ("non-empty", " x ", " x ", None),
    )
    for index, (command, raw, expected_result, expected_error) in enumerate(
        scalar_vectors
    ):
        host = {
            "resource_state": {},
            "command": command,
            "arguments": [raw],
        }
        py_c = from_python_run(
            scalar_compiled, run_compiled(scalar_compiled, host)
        )
        c_c, err = run_c_vector(scalar_compiled, host)
        vector_name = f"stateful-scalar:{index}"
        if c_c is None:
            ok(f"diff:{vector_name}", False, err)
            continue
        envelope = py_c.get("stats") or {}
        diffs = compare_canonical(py_c, c_c)
        semantic = (
            envelope.get("result") == expected_result
            and envelope.get("error") == expected_error
            and envelope.get("resource_state") == {}
            and envelope.get("state_changed") is False
            and py_c.get("ticket") is None
            and c_c.get("ticket") is None
        )
        ok(
            f"diff:{vector_name}",
            not diffs and semantic,
            f"full:{canonical_sha256(py_c)[:16]}"
            if not diffs and semantic
            else (diffs[:8] or ["semantic-mismatch"]),
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
        ok(
            f"opcode_diff:{name}",
            not diffs,
            "full" if not diffs else diffs[:12],
        )

    for name, instr, image, host, limits in primitive_vectors():
        py_c, compiled, _ = run_python_vector(instr, image, host, limits)
        c_c, err = run_c_vector(compiled, host, limits)
        if c_c is None:
            ok(f"prim_diff:{name}", False, err)
        else:
            diffs = compare_canonical(py_c, c_c)
            ok(f"prim_diff:{name}", not diffs, diffs[:12] if diffs else "full")

    # Decode rejections — both reject
    from .validate import validate_bytecode

    bad_samples = []
    art = ROOT / "artifacts/uem/text_stats_v2/program.uem"
    raw = art.read_bytes()
    bad_samples.append(("trunc", raw[:20]))
    bad_samples.append(("trail", raw + b"\x00"))
    bad_samples.append(("magic", b"XXXX" + raw[4:]))
    bad_version = bytearray(raw)
    bad_version[4:6] = b"\x00\x02"
    bad_samples.append(("version", bytes(bad_version)))
    b = bytearray(raw)
    b[12] = 0x7F
    bad_samples.append(("badop", bytes(b)))
    primitive_compiled = _enc((("APPLY", "identity"), ("STOP", None)))
    primitive_raw = value_of(primitive_compiled)["bytecode"]
    bad_samples.append(
        ("primitive", primitive_raw.replace(b"identity", b"zzzzzzzz", 1))
    )
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
    compiled = compile_declaration_path(str(ROOT / "examples/declarations/text_stats_v2.json"))
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

    # --- Ticket suite: construct, redaction, dedupe, identity ---
    from .primitives import construct_ticket_from_fault

    secret_thing = {
        "value": {
            "machine_fault": {
                "operation": "apply",
                "error_type": "RuntimeError",
                "message": "password=hunter2 token=abc",
            },
            "store": {},
        },
        "depths": (),
        "axes": (),
        "evidence": ("probe",),
        "state": "invalid",
    }
    t1 = construct_ticket_from_fault(secret_thing)
    ticket = value_of(t1).get("ticket") or {}
    ok(
        "ticket_redaction",
        "hunter2" not in ticket.get("message", "")
        and "password" not in ticket.get("message", "").lower(),
        ticket.get("message"),
    )
    t2 = construct_ticket_from_fault(t1)
    ok(
        "ticket_dedupe_same_id",
        value_of(t2).get("ticket", {}).get("correlation_id")
        == ticket.get("correlation_id"),
    )
    # Cross-host ticket identity for empty fault
    py_t, compiled_t, _ = run_python_vector((("TICKET", None), ("STOP", None)), {}, {})
    c_t, err_t = run_c_vector(compiled_t, {})
    if c_t is None:
        ok("ticket_cross_host_identity", False, err_t)
    else:
        ok(
            "ticket_cross_host_identity",
            (py_t.get("ticket") or {}).get("correlation_id")
            == (c_t.get("ticket") or {}).get("correlation_id")
            and (py_t.get("ticket") or {}).get("message")
            == (c_t.get("ticket") or {}).get("message"),
            {
                "py": py_t.get("ticket"),
                "c": c_t.get("ticket"),
            },
        )
        ok(
            "ticket_full_canonical",
            not compare_canonical(py_t, c_t),
            compare_canonical(py_t, c_t)[:6],
        )

    # Validation path must never ticket
    inv = compile_declaration_path(str(ROOT / "examples/declarations/invoice_total.json"))
    bad_host = {
        "document": {
            "tax_rate": "0.10",
            "items": [{"quantity": 0, "unit_price": "1.00"}],
        }
    }
    py_bad = from_python_run(inv, run_compiled(inv, bad_host))
    c_bad, _ = run_c_vector(inv, bad_host)
    ok(
        "validation_no_ticket_both",
        py_bad.get("ticket") is None and (c_bad or {}).get("ticket") is None,
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
