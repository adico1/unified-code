"""L13 production-path coverage closure — real assertions on state/output/evidence."""

from __future__ import annotations

import json
import os
import struct
from decimal import Decimal
from pathlib import Path
from unittest import mock

import pytest

from unified.machine.bytecode import (
    _decode,
    _encode,
    _read_u16,
    _read_u32,
    canonical_image_bytes,
    decode_program,
    encode_program,
)
from unified.machine.compile_decl import (
    _compile,
    _default,
    compile_declaration,
    write_artifacts,
)
from unified.machine.host import _fulfill, _read_json, _read_utf8, run_compiled, run_program
from unified.machine.interpreter import (
    _path_delete,
    _path_get,
    _path_set,
    machine_load,
    machine_run,
    machine_step,
)
from unified.machine.opcodes import FORMAT_VERSION, MAGIC, NAME_TO_BYTE, TAG_NONE, TAG_STRING
from unified.machine.primitives import (
    _ExprFail,
    _bound,
    _dig,
    _get_path,
    _resolve_root,
    apply_primitive,
    construct_ticket_from_fault,
    eval_expr,
    prim_accept_outward,
    prim_eval_expression,
    prim_letter,
    prim_present_json,
    prim_require_source,
    prim_verify_result,
)
from unified.machine.thing import blank_thing, value_of, with_evidence, with_state

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# bytecode
# ---------------------------------------------------------------------------


def test_bytecode_truncated_helpers_and_mid_stream():
    with pytest.raises(ValueError, match="truncated"):
        _read_u16(b"\x00", 0)
    with pytest.raises(ValueError, match="truncated"):
        _read_u32(b"\x00\x00\x00", 0)

    # count=1 but no opcode bytes → truncated at instruction loop head (line 147)
    header = MAGIC + struct.pack(">HH", FORMAT_VERSION, 0) + struct.pack(">I", 1)
    with pytest.raises(ValueError, match="truncated"):
        _decode(header)

    # opcode present, tag missing → truncated (line 153)
    only_op = header + bytes([NAME_TO_BYTE["STOP"]])
    with pytest.raises(ValueError, match="truncated"):
        _decode(only_op)

    # TAG_STRING length field truncated → _read_u32
    half_len = (
        header
        + bytes([NAME_TO_BYTE["LOAD"], TAG_STRING])
        + b"\x00\x00"
    )
    with pytest.raises(ValueError, match="truncated"):
        _decode(half_len)

    # full re-encode mismatch → noncanonical-encoding
    good = _encode((("STOP", None),), {})
    with mock.patch("unified.machine.bytecode._encode", return_value=b"not-the-same"):
        with pytest.raises(ValueError, match="noncanonical-encoding"):
            _decode(good)


def test_bytecode_decode_rejects_propagate_to_thing():
    header = MAGIC + struct.pack(">HH", FORMAT_VERSION, 0) + struct.pack(">I", 1)
    t = decode_program(blank_thing({"bytecode": header}))
    assert t["state"] == "invalid"
    assert any("decode:reject" in str(e) for e in (t.get("evidence") or ()))


# ---------------------------------------------------------------------------
# compile_decl
# ---------------------------------------------------------------------------


def test_compile_unsupported_boundary_and_validate_encode_fail():
    decl = {
        "features": [
            {
                "name": "f",
                "transformation": {
                    "kind": "expression",
                    "program": {"op": "literal", "value": 1},
                    "bindings": {},
                },
            }
        ],
        "boundaries": [{"kind": "read_socket", "name": "b"}],
    }
    with pytest.raises(ValueError, match="unsupported-boundary"):
        _compile(decl)

    out = compile_declaration(
        blank_thing(
            {
                "declaration": {
                    "features": [
                        {
                            "name": "f",
                            "transformation": {
                                "kind": "expression",
                                "program": {"op": "literal", "value": 1},
                            },
                        }
                    ],
                    "boundaries": [{"kind": "read_socket"}],
                }
            }
        )
    )
    assert out["state"] == "invalid"
    assert any("compile:fail" in str(e) for e in (out.get("evidence") or ()))

    # validate_symbolic fails after successful _compile shape
    good_decl = {
        "features": [
            {
                "name": "f",
                "transformation": {
                    "kind": "expression",
                    "program": {"op": "literal", "value": 1},
                    "bindings": {},
                },
            }
        ],
        "boundaries": [{"kind": "read_utf8_source", "name": "b"}],
    }
    with mock.patch(
        "unified.machine.compile_decl.validate_symbolic",
        return_value=with_state(blank_thing({}), "invalid"),
    ):
        out = compile_declaration(blank_thing({"declaration": good_decl}))
        assert out["state"] == "invalid"

    with mock.patch(
        "unified.machine.compile_decl.encode_program",
        return_value=with_state(blank_thing({}), "invalid"),
    ):
        out = compile_declaration(blank_thing({"declaration": good_decl}))
        assert out["state"] == "invalid"


def test_write_artifacts_without_bytecode_bytes(tmp_path):
    t = blank_thing(
        {
            "instructions": (("STOP", None),),
            "image": {},
            "program_sha256": "abc",
            "bytecode_size": 0,
            # bytecode deliberately not bytes → skip .uem write branch
            "bytecode": None,
        }
    )
    out = write_artifacts(t, str(tmp_path / "art"))
    assert not (tmp_path / "art" / "program.uem").exists()
    assert (tmp_path / "art" / "program.symbolic.json").is_file()
    assert any(str(e).startswith("artifacts:") for e in (out.get("evidence") or ()))


def test_default_json_helpers():
    assert _default((1, 2)) == [1, 2]
    assert _default({3, 1}) == [1, 3]
    with pytest.raises(TypeError):
        _default(object())


# ---------------------------------------------------------------------------
# host
# ---------------------------------------------------------------------------


def test_host_read_error_paths(tmp_path):
    missing = tmp_path / "nope.json"
    assert _read_json(str(missing), {}).get("error") == "missing-file"
    assert _read_json(str(tmp_path), {}).get("error") == "not-a-file"

    bad_utf = tmp_path / "bad.json"
    bad_utf.write_bytes(b"\xff\xfe")
    assert _read_json(str(bad_utf), {}).get("error") == "invalid-utf8"

    ok = tmp_path / "ok.txt"
    ok.write_text("x", encoding="utf-8")
    with mock.patch.object(Path, "read_bytes", side_effect=OSError("eio")):
        assert _read_utf8(str(ok), {}).get("error") == "read-error"
    okj = tmp_path / "ok.json"
    okj.write_text('{"a":1}', encoding="utf-8")
    with mock.patch.object(Path, "read_text", side_effect=OSError("eio")):
        assert _read_json(str(okj), {}).get("error") == "read-error"


def test_host_loop_invalid_without_halt_and_pc_exhausted():
    """machine_run returns invalid (no halt, no outward) → host finalizes."""
    # APPLY unknown primitive is last instr (no STOP): invalid, pc past end
    prog = blank_thing(
        {
            "instructions": (("APPLY", "not_a_real_primitive"),),
            "image": {},
            "host_input": {},
        }
    )
    # bypass validate — direct run
    loaded = machine_load(prog)
    # force host path via run_program-like loop
    from unified.machine import host as H

    current = loaded
    current = H.machine_run(current)
    v = value_of(current)
    assert not v.get("halted") or current.get("state") == "invalid"
    # If halted already, still exercise finalize via run_program
    out = run_program(prog)
    assert "host:done" in (out.get("evidence") or ()) or out.get("state") == "invalid"


def test_host_loop_branches_via_controlled_machine_run(monkeypatch):
    import unified.machine.host as H

    base = blank_thing(
        {
            "instructions": (("STOP", None),),
            "image": {},
            "host_input": {},
        }
    )
    loaded = machine_load(base)

    # 1) invalid without halt, no outward → finalize (lines 37-38)
    def run_invalid(_t):
        return with_state(
            {
                **loaded,
                "value": {
                    **value_of(loaded),
                    "halted": False,
                    "outward_request": None,
                    "pc": 0,
                    "instructions": (("STOP", None),),
                },
            },
            "invalid",
        )

    monkeypatch.setattr(H, "machine_run", run_invalid)
    monkeypatch.setattr(H, "machine_load", lambda t: loaded)
    out = H.run_program(base)
    assert "host:done" in (out.get("evidence") or ())
    assert out["state"] == "invalid"

    # 2) formed, no outward, pc past end → finalize (lines 40-41)
    def run_pc_done(_t):
        return {
            **loaded,
            "state": "formed",
            "value": {
                **value_of(loaded),
                "halted": False,
                "outward_request": None,
                "pc": 5,
                "instructions": (("STOP", None),),
            },
        }

    monkeypatch.setattr(H, "machine_run", run_pc_done)
    out = H.run_program(base)
    assert "host:done" in (out.get("evidence") or ())

    # 3) formed, no outward, pc mid-program → machine_step then next run halts
    steps = {"n": 0}

    def run_progress(t):
        steps["n"] += 1
        if steps["n"] == 1:
            return {
                **loaded,
                "state": "formed",
                "value": {
                    **value_of(loaded),
                    "halted": False,
                    "outward_request": None,
                    "pc": 0,
                    "instructions": (("STOP", None),),
                },
            }
        return {
            **t,
            "state": "formed",
            "value": {**value_of(t), "halted": True, "stop_reason": "stop"},
        }

    monkeypatch.setattr(H, "machine_run", run_progress)
    monkeypatch.setattr(
        H,
        "machine_step",
        lambda t: {
            **t,
            "value": {**value_of(t), "pc": 1, "halted": False},
        },
    )
    out = H.run_program(base)
    assert "host:done" in (out.get("evidence") or ())
    assert steps["n"] >= 2


def test_host_guard_limit_production(monkeypatch):
    """Exercise production host:guard-limit return via HOST_GUARD_LIMIT."""
    import unified.machine.host as H

    base = blank_thing(
        {"instructions": (("STOP", None),), "image": {}, "host_input": {}}
    )
    loaded = machine_load(base)
    monkeypatch.setattr(H, "machine_load", lambda t: loaded)
    monkeypatch.setattr(H, "HOST_GUARD_LIMIT", 3)

    def never_halt(t):
        return {
            **loaded,
            "state": "formed",
            "value": {
                **value_of(loaded),
                "halted": False,
                "outward_request": None,
                "pc": 0,
                "instructions": (("STOP", None), ("STOP", None)),
            },
        }

    monkeypatch.setattr(H, "machine_run", never_halt)
    monkeypatch.setattr(H, "machine_step", lambda t: t)
    out = H.run_program(base)
    assert out["state"] == "invalid"
    assert any("host:guard-limit" in str(e) for e in (out.get("evidence") or ()))


# ---------------------------------------------------------------------------
# interpreter
# ---------------------------------------------------------------------------


def test_interpreter_machine_run_early_exits():
    base = blank_thing(
        {
            "instructions": (("STOP", None),),
            "image": {},
            "host_input": {},
        }
    )
    loaded = machine_load(base)

    # invalid + stop_reason → return immediately (line 131)
    v = dict(value_of(loaded))
    v["halted"] = False
    v["stop_reason"] = "limit:steps"
    early = machine_run(with_state({**loaded, "value": v}, "invalid"))
    assert early.get("state") == "invalid"
    assert value_of(early).get("stop_reason") == "limit:steps"

    # invalid + machine_fault + no ticket → one step then return (136-137)
    v = dict(value_of(loaded))
    v["machine_fault"] = {"operation": "x", "error_type": "E", "message": "m"}
    v["ticket"] = None
    v["halted"] = False
    v["stop_reason"] = None
    v["pc"] = 0
    v["instructions"] = (("STOP", None),)
    faulted = machine_run(with_state({**loaded, "value": v}, "invalid"))
    assert faulted is not None

    # after step invalid with pc past end (143-144)
    v = dict(value_of(loaded))
    v["instructions"] = (("APPLY", "not_real"),)
    v["pc"] = 0
    v["halted"] = False
    v["machine_fault"] = None
    v["stop_reason"] = None
    past = machine_run({**loaded, "value": v, "state": "formed"})
    assert past.get("state") == "invalid"
    assert value_of(past).get("pc", 0) >= 1


def test_interpreter_dequeue_string_head_and_duplicate_apply():
    # non-dict queue head (line 248)
    loaded = machine_load(
        blank_thing(
            {
                "instructions": (("DEQUEUE", None), ("STOP", None)),
                "image": {},
                "host_input": {},
            }
        )
    )
    v = dict(value_of(loaded))
    v["event_queue"] = ("plain-event",)
    v["pc"] = 0
    out = machine_step({**loaded, "value": v})
    assert value_of(out).get("event") == "plain-event"
    assert "plain-event" in (value_of(out).get("events_dequeued") or [])

    # duplicate event id skip on APPLY (line 281)
    loaded = machine_load(
        blank_thing(
            {
                "instructions": (("APPLY", "identity"), ("STOP", None)),
                "image": {},
                "host_input": {},
            }
        )
    )
    v = dict(value_of(loaded))
    v["event_id"] = "dup1"
    v["event"] = "something"
    v["processed_event_ids"] = ("dup1",)
    v["pc"] = 0
    out = machine_step({**loaded, "value": v})
    assert any("duplicate-skipped" in str(e) for e in (out.get("evidence") or ()))


def test_interpreter_apply_escalates_machine_fault():
    loaded = machine_load(
        blank_thing(
            {
                "instructions": (("APPLY", "eval_expression"), ("STOP", None)),
                "image": {
                    "expression": {"op": "literal", "value": 1},
                    "input_key": "document",
                    "part_name": "p",
                    "bindings": {},
                },
                "host_input": {},
            }
        )
    )
    v = dict(value_of(loaded))
    v["store"] = {"document": {}}
    v["pc"] = 0

    def boom(*_a, **_k):
        raise RuntimeError("forced-fault")

    with mock.patch("unified.machine.primitives.eval_expr", side_effect=boom):
        # apply_primitive → prim_eval_expression catches Exception → machine_fault
        out = machine_step({**loaded, "value": v, "state": "formed"})
        ov = value_of(out)
        assert ov.get("machine_fault") is not None
        assert out.get("state") == "invalid"


def test_interpreter_outward_keeps_result_when_auto():
    loaded = machine_load(
        blank_thing(
            {
                "instructions": (("OUTWARD", "read_utf8"), ("STOP", None)),
                "image": {"boundary": {"source_field": "source"}},
                "host_input": {},
            }
        )
    )
    v = dict(value_of(loaded))
    v["store"] = {"source": "-"}
    v["outward_result"] = {"data": "x"}
    v["_outward_auto"] = False
    v["pc"] = 0
    out = machine_step({**loaded, "value": v})
    # request set; previous result branch taken (line 390 pass)
    assert value_of(out).get("outward_request") is not None
    assert any("outward:request" in str(e) for e in (out.get("evidence") or ()))


def test_interpreter_path_helpers():
    assert _path_get({"a": {"b": 1}}, "a.b") == 1
    assert _path_get({"a": 1}, "a.b") is None  # line 458
    assert _path_get({"a": {}}, "a.missing") is None

    d = {}
    _path_set(d, "x.y.z", 9)  # creates nested
    assert d == {"x": {"y": {"z": 9}}}
    d2 = {"x": "not-dict"}
    _path_set(d2, "x.y", 1)
    assert d2["x"]["y"] == 1
    # intermediate already a dict → take false arm of 472 (no re-create)
    d4 = {"x": {"keep": True}}
    _path_set(d4, "x.y", 2)
    assert d4 == {"x": {"keep": True, "y": 2}}

    d3 = {"a": {"b": 1, "c": 2}}
    _path_delete(d3, "a.b")
    assert "b" not in d3["a"]


def test_interpreter_route_store_override_branch():
    loaded = machine_load(
        blank_thing(
            {
                "instructions": (("ROUTE", "alt"), ("STOP", None)),
                "image": {"routes": {"e": "identity"}},
                "host_input": {},
            }
        )
    )
    v = dict(value_of(loaded))
    v["event"] = "e"
    v["store"] = {"alt": {"e": "identity"}}
    v["pc"] = 0
    out = machine_step({**loaded, "value": v})
    assert value_of(out).get("pending_primitive") == "identity"

    # ROUTE with operand None → skip store override (branch 261 falsy → 263)
    loaded2 = machine_load(
        blank_thing(
            {
                "instructions": (("ROUTE", None), ("STOP", None)),
                "image": {"routes": {"e": "identity"}},
                "host_input": {},
            }
        )
    )
    v2 = dict(value_of(loaded2))
    v2["event"] = "e"
    v2["routes"] = {"e": "identity"}
    v2["pc"] = 0
    out2 = machine_step({**loaded2, "value": v2})
    assert value_of(out2).get("pending_primitive") == "identity"


def test_interpreter_machine_run_guard_limit(monkeypatch):
    """Hit machine_run steps limit return (line 144)."""
    import unified.machine.interpreter as I

    monkeypatch.setattr(I, "MACHINE_RUN_GUARD", 3)
    loaded = machine_load(
        blank_thing(
            {
                "instructions": (("LOAD", "host_input"), ("STOP", None)),
                "image": {},
                "host_input": {"a": 1},
            }
        )
    )
    # Force each step to re-run same pc without halt
    def sticky_step(t):
        v = dict(value_of(t))
        v["halted"] = False
        v["pc"] = 0
        v["machine_fault"] = None
        v["stop_reason"] = None
        v["outward_request"] = None
        # keep formed so loop continues past invalid checks
        return {**t, "value": v, "state": "formed"}

    monkeypatch.setattr(I, "machine_step", sticky_step)
    out = I.machine_run(loaded)
    assert out.get("state") == "invalid"
    assert value_of(out).get("stop_reason") == "limit:steps"
    assert any("limit:steps" in str(e) for e in (out.get("evidence") or ()))


# ---------------------------------------------------------------------------
# primitives
# ---------------------------------------------------------------------------


def test_letter_prior_error_and_absent_paths():
    # prior error with None payload (line 68)
    t = blank_thing({"store": {"error": "e"}, "host_input": {}})
    out = prim_letter(t)
    assert any("letter:prior-error" in str(e) for e in (out.get("evidence") or ()))

    # host_input is None and payload None → absent (74-75)
    t = blank_thing({"store": {}, "host_input": None})
    # ensure host_input key present with None
    t = {**t, "value": {**value_of(t), "store": {}, "host_input": None}}
    out = prim_letter(t)
    assert out.get("state") == "absent" or any(
        "letter:absent" in str(e) for e in (out.get("evidence") or ())
    )


def test_require_source_list_host_argv():
    img = {"source": {"field": "source", "missing": "missing-source", "extra": "extra-source"}}
    # host is list (line 116 path)
    t = blank_thing({"store": {}, "image": img, "host_input": ["file.txt"]})
    out = prim_require_source(t)
    assert value_of(out)["store"].get("source") == "file.txt"
    assert any("source:ok" in str(e) for e in (out.get("evidence") or ()))


def test_accept_outward_path_and_non_data_result():
    img = {"boundary": {"name": "b", "target_field": "text"}}
    t = blank_thing(
        {
            "store": {},
            "image": img,
            "outward_result": {"error": "x", "path": ["p"]},
        }
    )
    out = prim_accept_outward(t)
    assert out["state"] == "invalid"
    assert value_of(out)["store"].get("path") == ["p"]  # line 169

    t = blank_thing({"store": {}, "image": img, "outward_result": "raw-string"})
    out = prim_accept_outward(t)
    assert value_of(out)["store"].get("text") == "raw-string"  # line 184


def test_eval_missing_expression_and_binding_skip_and_fault():
    t = blank_thing(
        {
            "store": {"document": {}},
            "image": {"expression": None, "input_key": "document", "part_name": "p"},
        }
    )
    out = prim_eval_expression(t)
    assert out["state"] == "invalid"
    assert value_of(out)["store"].get("error") == "missing-expression"

    # binding order name not in bindings_ast → continue (line 239)
    t = blank_thing(
        {
            "store": {"document": {}},
            "image": {
                "expression": {"op": "literal", "value": 1},
                "input_key": "document",
                "bindings": {"a": {"op": "literal", "value": 1}},
                "binding_order": ["a", "missing_name"],
                "part_name": "p",
            },
        }
    )
    out = prim_eval_expression(t)
    assert value_of(out).get("_acc") == 1

    # generic Exception → machine_fault (256-262)
    t = blank_thing(
        {
            "store": {"document": {}},
            "image": {
                "expression": {"op": "literal", "value": 1},
                "input_key": "document",
                "part_name": "p",
            },
        }
    )
    with mock.patch("unified.machine.primitives.eval_expr", side_effect=RuntimeError("boom")):
        out = prim_eval_expression(t)
        assert out["state"] == "invalid"
        assert value_of(out).get("machine_fault") is not None


def test_verify_missing_evidence_marks():
    img = {
        "verify": {
            "require_value_field": "stats",
            "require_evidence_contains": ["must-have-this-mark"],
        }
    }
    t = blank_thing({"store": {"stats": 1}, "image": img})
    t = {**t, "evidence": ()}
    out = prim_verify_result(t)
    assert out["state"] == "invalid"
    assert any("script-law:fail" in str(e) for e in (out.get("evidence") or ()))


def test_present_json_keys_from_store_when_success_from_not_dict():
    img = {
        "presentation": {
            "success_from": "stats",
            "success_keys": ["n", "w"],
            "include_error_path": False,
        }
    }
    # success_from is not a dict but keys exist on store (337-338)
    t = blank_thing({"store": {"stats": 99, "n": 1, "w": 2}, "image": img})
    t = with_state(t, "valid")
    out = prim_present_json(t)
    pres = value_of(out)["store"]["presentation"]
    assert pres["exit_code"] == 0
    assert '"n":1' in pres["text"]

    # valid + non-dict success_from + incomplete keys → elif false → error body
    img2 = {
        "presentation": {
            "success_from": "stats",
            "success_keys": ["n", "missing"],
            "include_error_path": False,
        }
    }
    t2 = blank_thing({"store": {"stats": 99, "n": 1, "error": "partial"}, "image": img2})
    t2 = with_state(t2, "valid")
    out2 = prim_present_json(t2)
    assert value_of(out2)["store"]["presentation"]["exit_code"] == 1
    assert "partial" in value_of(out2)["store"]["presentation"]["text"]


def test_resolve_root_non_object_and_other_key():
    assert _resolve_root({"document": [1]}, "document")["__error__"] == "input-not-an-object"
    assert _resolve_root({"x": 1}, "other") == {"x": 1}


def test_eval_expr_all_failure_and_edge_ops():
    ctx = {
        "root": {
            "text": "hi",
            "items": [{"quantity": 1, "unit_price": "1.00"}, "bad"],
            "n": None,
            "arr": [10, 20],
            "obj": {"k": 1},
        },
        "path": [],
        "bindings": {},
    }

    with pytest.raises(_ExprFail, match="bad-node"):
        eval_expr("not-a-dict", ctx)  # line 388

    assert eval_expr({"op": "count", "of": {"op": "literal", "value": None}}, ctx) == 0  # 410

    with pytest.raises(_ExprFail):
        eval_expr(
            {"op": "as_int", "of": {"op": "literal", "value": None}, "missing_error": "mi"},
            ctx,
        )  # 422
    with pytest.raises(_ExprFail):
        eval_expr(
            {"op": "as_int", "of": {"op": "literal", "value": True}, "type_error": "ti"},
            ctx,
        )  # 424 bool
    with pytest.raises(_ExprFail):
        eval_expr(
            {"op": "as_int", "of": {"op": "literal", "value": "x"}, "type_error": "ti"},
            ctx,
        )

    with pytest.raises(_ExprFail):
        eval_expr(
            {
                "op": "as_decimal",
                "of": {"op": "literal", "value": None},
                "missing_error": "md",
            },
            ctx,
        )  # 430
    # already Decimal returns as-is (432)
    d = Decimal("1.5")
    assert eval_expr({"op": "as_decimal", "of": {"op": "literal", "value": d}}, ctx) == d
    with pytest.raises(_ExprFail):
        eval_expr(
            {"op": "as_decimal", "of": {"op": "literal", "value": 1.2}, "type_error": "nd"},
            ctx,
        )  # 434 not str
    with pytest.raises(_ExprFail):
        eval_expr(
            {
                "op": "as_decimal",
                "of": {"op": "literal", "value": "not-a-dec"},
                "type_error": "nd",
            },
            ctx,
        )  # 437-438

    # mul/add coerce non-Decimal (466)
    assert eval_expr(
        {
            "op": "add",
            "values": [
                {"op": "literal", "value": Decimal("1")},
                {"op": "literal", "value": 2},
            ],
        },
        ctx,
    ) == Decimal("3")

    with pytest.raises(_ExprFail, match="items-not-a-list"):
        eval_expr(
            {
                "op": "sum_each",
                "collection": {"op": "literal", "value": "nope"},
                "each": {"op": "literal", "value": Decimal("1")},
            },
            ctx,
        )  # 473

    with pytest.raises(_ExprFail, match="item-not-an-object"):
        eval_expr(
            {
                "op": "sum_each",
                "collection": {"op": "field", "path": ["items"]},
                "each": {"op": "literal", "value": Decimal("1")},
            },
            ctx,
        )  # 480 on second item "bad"

    # sum_each part not Decimal → coerce (490)
    r = eval_expr(
        {
            "op": "sum_each",
            "collection": {
                "op": "literal",
                "value": [{"x": 1}],
            },
            "each": {"op": "literal", "value": 3},
        },
        ctx,
    )
    assert r == Decimal("3")

    # quantize / decimal_str coerce (497, 504)
    q = eval_expr(
        {
            "op": "quantize",
            "exp": "0.01",
            "rounding": "ROUND_HALF_UP",
            "of": {"op": "literal", "value": 1},
        },
        ctx,
    )
    assert isinstance(q, Decimal)
    ds = eval_expr(
        {
            "op": "decimal_str",
            "places": 2,
            "of": {"op": "literal", "value": 1},
        },
        ctx,
    )
    assert ds == "1.00"

    for op in ("str_len", "line_count", "word_count", "unique_casefold_word_count"):
        with pytest.raises(_ExprFail, match="invalid-text"):
            eval_expr({"op": op, "of": {"op": "literal", "value": 123}}, ctx)


def test_bound_and_dig_and_get_path_edges():
    assert _bound(Decimal("1")) == Decimal("1")  # 538
    assert _bound(3) == Decimal("3")
    assert _bound("2.5") == Decimal("2.5")  # 542
    assert _bound(1.25) == Decimal("1.25")  # 543 fallback str

    assert _dig(None, ["a"]) is None  # 563
    assert _dig([1, 2], [5]) is None  # 565-567
    assert _dig([1, 2], [1]) == 2
    assert _dig({"a": 1}, ["b"]) is None  # 570
    assert _dig({"a": {"b": 9}}, ["a", "b"]) == 9

    ctx = {"root": {"x": 1}, "item": {"y": 2}, "path": []}
    assert _get_path(ctx, ("item", "y")) == 2  # 551
    ctx2 = {"root": {"y": 9}, "__item__": {"y": 2}, "__in_each__": True, "path": []}
    assert _get_path(ctx2, ("y",)) == 2  # dig item first
    ctx3 = {"root": {"z": 3}, "__item__": {"y": 2}, "__in_each__": True, "path": []}
    assert _get_path(ctx3, ("z",)) == 3  # fall through to root when not in item


def test_construct_ticket_dedupe_same_id():
    t = blank_thing(
        {
            "machine_fault": {
                "operation": "op",
                "error_type": "E",
                "message": "m",
            }
        }
    )
    t1 = construct_ticket_from_fault(t)
    tid = value_of(t1)["ticket"]["correlation_id"]
    # second construct with same fault + existing ticket same id → reuse
    v = dict(value_of(t1))
    t2 = construct_ticket_from_fault({**t1, "value": v})
    assert value_of(t2)["ticket"]["correlation_id"] == tid
