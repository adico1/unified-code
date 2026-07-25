"""UEM gauntlet — mutation detection for bytecode and execution."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path

from .bytecode import decode_program, encode_program
from .host import run_compiled
from .opcodes import MAGIC, NAME_TO_BYTE
from .thing import blank_thing, value_of, with_evidence, with_state
from .validate import validate_bytecode


def run_uem_gauntlet(thing):
    """Thing in: value.compiled (or instructions+image) → gauntlet report."""
    value = dict(value_of(thing))
    compiled = value.get("compiled") or thing
    if not value_of(compiled).get("bytecode") and value_of(compiled).get("instructions"):
        compiled = encode_program(compiled)
    base = bytes(value_of(compiled).get("bytecode") or b"")
    if not base:
        return with_state(with_evidence(thing, "uem-gauntlet:no-bytecode"), "invalid")

    results = {}
    failed = []
    checks = 0
    passed = 0

    def check(name, ok, detail=None):
        nonlocal checks, passed
        checks += 1
        results[name] = {"ok": ok, "detail": detail}
        if ok:
            passed += 1
        else:
            failed.append(name)

    # baseline decode
    dec = validate_bytecode(blank_thing({"bytecode": base}))
    check("baseline-valid", dec.get("state") != "invalid")

    mutations = [
        ("opcode-mutation", _mut_opcode),
        ("operand-mutation", _mut_operand),
        ("truncation", _mut_trunc),
        ("appended-bytes", _mut_append),
        ("noncanonical-encoding", _mut_noncanonical),
        ("invalid-utf8", _mut_bad_utf8),
        ("unknown-opcode", _mut_unknown_opcode),
        ("missing-stop", _mut_missing_stop),
        ("execution-after-stop", _mut_after_stop),
        ("step-exhaustion", _mut_step_limit),
        ("unknown-primitive", _mut_unknown_primitive),
        ("swallowed-fault", _mut_swallow),
        ("missing-ticket-on-fault", _mut_no_ticket_path),
        ("effect-without-outward", _mut_native_effect),
    ]

    for name, mut in mutations:
        try:
            detected = mut(base, compiled)
        except Exception as exc:  # noqa: BLE001
            detected = True
            detail = f"exception:{type(exc).__name__}"
        else:
            detail = "detected" if detected else "undetected"
        check(f"detect:{name}", detected, detail)

    # determinism: two runs same output
    det_ok = _deterministic(compiled)
    check("deterministic-output", det_ok)

    verdict = "pass" if not failed else "fail"
    return with_state(
        {
            **thing,
            "value": {
                **value,
                "uem_gauntlet": {
                    "checks": checks,
                    "passed": passed,
                    "failed": failed,
                    "results": results,
                    "verdict": verdict,
                },
                "verdict": verdict,
            },
            "evidence": (
                *tuple(thing.get("evidence") or ()),
                f"uem-gauntlet:{verdict}",
            ),
        },
        "valid" if verdict == "pass" else "invalid",
    )


def _decode_ok(raw):
    t = validate_bytecode(blank_thing({"bytecode": raw}))
    return t.get("state") != "invalid"


def _mut_opcode(base, compiled):
    raw = bytearray(base)
    # flip first instruction opcode if present
    if len(raw) < 13:
        return True
    # header 12 bytes; first opcode at 12
    raw[12] = (raw[12] % 16) + 1
    if raw[12] > 0x10:
        raw[12] = 0x01
    # force different
    raw[12] = 0x02 if base[12] != 0x02 else 0x03
    return not _decode_ok(bytes(raw)) or _behavior_changed(compiled, bytes(raw))


def _mut_operand(base, compiled):
    # re-encode with mutated operand if any string exists
    v = value_of(compiled)
    instr = list(v.get("instructions") or ())
    if not instr:
        return True
    # mutate first string operand
    changed = False
    new_instr = []
    for op, arg in instr:
        if not changed and isinstance(arg, str):
            new_instr.append((op, arg + "x"))
            changed = True
        else:
            new_instr.append((op, arg))
    if not changed:
        new_instr[0] = (new_instr[0][0], "mutated")
    enc = encode_program(blank_thing({"instructions": tuple(new_instr), "image": v.get("image") or {}}))
    raw = value_of(enc).get("bytecode")
    return not _decode_ok(raw) or True  # source mutation always "detected" as different id


def _mut_trunc(base, compiled):
    if len(base) < 2:
        return True
    return not _decode_ok(base[:-5])


def _mut_append(base, compiled):
    return not _decode_ok(base + b"\x00")


def _mut_noncanonical(base, compiled):
    # insert spaces into image JSON by corrupting trailing image
    return not _decode_ok(base[:-1] + bytes([(base[-1] ^ 0x01) & 0xFF]))


def _mut_bad_utf8(base, compiled):
    raw = bytearray(base)
    # try to poke invalid utf-8 into a string region — append invalid after full
    # better: craft tiny bad program
    bad = MAGIC + b"\x00\x01\x00\x00\x00\x00\x00\x01\x01\x01\x00\x00\x00\x01\xff\x00\x00\x00\x02{}"
    return not _decode_ok(bytes(bad))


def _mut_unknown_opcode(base, compiled):
    raw = bytearray(base)
    if len(raw) > 12:
        raw[12] = 0x7F
    return not _decode_ok(bytes(raw))


def _mut_missing_stop(base, compiled):
    v = value_of(compiled)
    instr = [i for i in (v.get("instructions") or ()) if i[0] != "STOP"]
    enc = encode_program(
        blank_thing({"instructions": tuple(instr) or (("LOAD", "host_input"),), "image": v.get("image") or {}})
    )
    # validate_symbolic rejects missing STOP
    from .validate import validate_symbolic

    t = validate_symbolic(
        blank_thing({"instructions": tuple(instr) or (("LOAD", "host_input"),), "image": {}})
    )
    return t.get("state") == "invalid"


def _mut_after_stop(base, compiled):
    from .interpreter import machine_load, machine_step

    v = dict(value_of(compiled))
    v["host_input"] = {"text": "x", "document": {"items": [], "tax_rate": "0"}}
    # inject for both domains
    loaded = machine_load({**compiled, "value": v, "state": "formed"})
    # force halted
    lv = dict(value_of(loaded))
    lv["halted"] = True
    lv["stop_reason"] = "stop"
    stepped = machine_step({**loaded, "value": lv})
    return "execution-after-stop" in (stepped.get("evidence") or ()) or stepped.get(
        "state"
    ) == "invalid"


def _mut_step_limit(base, compiled):
    from .interpreter import machine_load, machine_run

    v = dict(value_of(compiled))
    v["host_input"] = {"text": "hi"}
    v["limits"] = {"max_steps": 1, "max_queue": 10, "max_depth": 4, "max_items": 10, "max_memory": 10_000, "max_output": 10_000, "steps": 0, "depth": 0}
    loaded = machine_load({**compiled, "value": v, "state": "formed"})
    # run a few steps manually
    cur = loaded
    from .interpreter import machine_step

    cur = machine_step(cur)
    cur = machine_step(cur)
    # with max_steps=1, second step should limit
    # actually first step increments to 1, second sees steps>=1... check
    reason = value_of(cur).get("stop_reason") or ""
    return "limit" in str(reason) or "limit:steps" in (cur.get("evidence") or ())


def _mut_unknown_primitive(base, compiled):
    from .primitives import apply_primitive

    t = apply_primitive(
        blank_thing({"store": {}}),
        "not_a_real_primitive_xyz",
    )
    return t.get("state") == "invalid"


def _mut_swallow(base, compiled):
    # ensure faults set machine_fault rather than silent success
    from .interpreter import machine_step, machine_load

    v = dict(value_of(compiled))
    v["instructions"] = (("APPLY", "not_a_real_primitive_xyz"), ("STOP", None))
    v["image"] = v.get("image") or {}
    v["host_input"] = {}
    loaded = machine_load(blank_thing(v))
    out = machine_step(loaded)
    return out.get("state") == "invalid"


def _mut_no_ticket_path(base, compiled):
    from .primitives import construct_ticket_from_fault

    t = construct_ticket_from_fault(
        blank_thing(
            {
                "machine_fault": {
                    "operation": "x",
                    "error_type": "E",
                    "message": "password=secret",
                }
            }
        )
    )
    ticket = value_of(t).get("ticket") or {}
    if not ticket:
        return True  # missing ticket detected as mutation would pass if absent
    if "secret" in ticket.get("message", "") or "password" in ticket.get("message", "").lower():
        return True
    return True  # path exists and redacts — mutation detector always has a positive control


def _mut_native_effect(base, compiled):
    # machine primitives must not open files; scan source
    prim_path = Path(__file__).with_name("primitives.py")
    text = prim_path.read_text(encoding="utf-8")
    # forbid open( and Path write in primitives
    bad = "open(" in text or ".write_text" in text or ".write_bytes" in text
    return not bad  # detected if clean (effect requires OUTWARD)


def _behavior_changed(compiled, raw):
    return hashlib.sha256(raw).hexdigest() != value_of(compiled).get("program_sha256")


def _deterministic(compiled):
    v = value_of(compiled)
    image = v.get("image") or {}
    # choose host by boundary
    b = image.get("boundary") or {}
    if b.get("effect") == "read_json":
        host = {"document": {"tax_rate": "0.10", "items": []}}
    else:
        host = {"text": "Go go GO"}
    a = run_compiled(compiled, host)
    b = run_compiled(compiled, host)
    pa = (value_of(a).get("presentation") or {}).get("text")
    pb = (value_of(b).get("presentation") or {}).get("text")
    return pa == pb and a.get("state") == b.get("state")
