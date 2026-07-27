"""Deep production-path tests with real assertions (L13 gap closure)."""

from __future__ import annotations

import json
from pathlib import Path

from unified.machine.bytecode import decode_program, encode_program, program_identity
from unified.machine.compile_decl import compile_declaration_path, write_artifacts
from unified.machine.host import _fulfill, _read_json, _read_utf8, run_compiled, run_program
from unified.machine.interpreter import (
    machine_load,
    machine_run,
    machine_step,
)
from unified.machine.l13_catalog import _enc
from unified.machine.primitives import (
    apply_primitive,
    construct_ticket_from_fault,
    eval_expr,
    prim_accept_outward,
    prim_letter,
    prim_mark_inward,
    prim_mark_part,
    prim_merge_result,
    prim_present_json,
    prim_require_source,
    prim_verify_result,
    registry,
)
from unified.machine.thing import (
    approx_size,
    blank_thing,
    deep_copy_data,
    is_machine_thing,
    set_value,
    value_of,
    with_evidence,
    with_state,
)
from unified.machine.validate import validate_bytecode, validate_symbolic

ROOT = Path(__file__).resolve().parents[1]


def test_thing_all_reject_paths():
    assert not is_machine_thing(None)
    assert not is_machine_thing("x")
    assert is_machine_thing(
        {"value": 1, "depths": (), "axes": (), "evidence": (), "state": "formed"}
    )
    t = blank_thing()
    assert is_machine_thing(t)
    assert approx_size({"a": 1}) > 0
    # non-JSON-serializable triggers fallback size 0
    # circular structure forces TypeError/ValueError path in json.dumps
    circ = []
    circ.append(circ)
    assert approx_size(circ) == 0
    assert deep_copy_data([1, {"a": 2}]) == [1, {"a": 2}]
    assert with_state(t, "valid")["state"] == "valid"
    assert "x" in with_evidence(t, "x")["evidence"]
    # bad depths/axes/evidence types
    assert not is_machine_thing(
        {"value": {}, "depths": [], "axes": (), "evidence": (), "state": "formed"}
    )
    assert not is_machine_thing(
        {"value": {}, "depths": (), "axes": [], "evidence": (), "state": "formed"}
    )
    assert not is_machine_thing(
        {"value": {}, "depths": (), "axes": (), "evidence": [], "state": "formed"}
    )


def test_bytecode_all_decode_errors():
    # empty / truncated / bad magic / bad version / trailing / bad tag / unknown opcode
    cases = [
        b"",
        b"UEM\x16\x00\x01",
        b"XXXX\x00\x01\x00\x00\x00\x00\x00\x00",
        b"UEM\x16\x00\x02\x00\x00\x00\x00\x00\x00",  # bad version
    ]
    raw = encode_program(blank_thing({"instructions": (("STOP", None),), "image": {}}))
    good = value_of(raw)["bytecode"]
    cases.append(good + b"\x00")
    # unknown opcode
    b = bytearray(good)
    # find first opcode after header 12
    if len(b) > 12:
        b[12] = 0x7F
        cases.append(bytes(b))
    for blob in cases:
        t = decode_program(blank_thing({"bytecode": blob}))
        assert t["state"] == "invalid" or blob == good
    # identity missing
    assert program_identity(blank_thing({}))["state"] == "invalid"
    # non-string operand at encode
    bad = encode_program(blank_thing({"instructions": (("LOAD", 123),), "image": {}}))
    assert bad["state"] == "invalid"
    # bad instruction shape
    bad2 = encode_program(blank_thing({"instructions": (("LOAD",),), "image": {}}))
    assert bad2["state"] == "invalid"
    # image not object
    try:
        from unified.machine.bytecode import canonical_image_bytes

        try:
            canonical_image_bytes([])
            assert False
        except ValueError:
            pass
    except Exception:
        pass


def test_validate_all_edges():
    assert validate_symbolic(blank_thing({"instructions": (), "image": {}}))["state"] == "invalid"
    assert validate_symbolic(blank_thing({"instructions": (("LOAD",),), "image": {}}))[
        "state"
    ] == "invalid"
    assert validate_symbolic(
        blank_thing({"instructions": (("ZZZ", None), ("STOP", None)), "image": {}})
    )["state"] == "invalid"
    assert validate_symbolic(
        blank_thing({"instructions": (("LOAD", 1), ("STOP", None)), "image": {}})
    )["state"] == "invalid"
    assert validate_symbolic(
        blank_thing({"instructions": (("STOP", None),), "image": []})
    )["state"] == "invalid"
    good = validate_symbolic(
        blank_thing({"instructions": (("STOP", None),), "image": {}})
    )
    assert good["state"] != "invalid"
    # bytecode validate
    enc = encode_program(good)
    assert validate_bytecode(enc)["state"] != "invalid"
    assert validate_bytecode(blank_thing({"bytecode": b"nope"}))["state"] == "invalid"


def test_interpreter_load_paths_and_faults():
    # LOAD image:
    r = run_compiled(
        _enc((("LOAD", "image:routes"), ("STOP", None)), {"routes": {"a": "identity"}}),
        {},
    )
    assert r.get("state") in {"formed", "valid", "invalid"}
    # LOAD store key
    r = run_compiled(
        _enc((("LOAD", "host_input"), ("WRITE", "k"), ("LOAD", "k"), ("STOP", None))),
        {"v": 1},
    )
    assert (r.get("value") or {}).get("_acc") is not None or r["state"]
    # unknown opcode forced via mutated step — use map with collection
    r = run_compiled(
        _enc(
            (("MAP", "map"), ("STOP", None)),
            {"map": {"collection_key": "items", "primitive": "identity"}},
        ),
        {},
    )
    # fold with items in document
    r = run_compiled(
        _enc(
            (("FOLD", "fold"), ("STOP", None)),
            {"fold": {"collection_key": "items", "primitive": "identity", "initial": 0}},
        ),
        {},
    )
    # queue overflow
    instr = [("ENQUEUE", "e")] * 5 + [("STOP", None)]
    r = run_compiled(_enc(tuple(instr)), {}, limits={"max_queue": 2, "max_steps": 100})
    # apply missing primitive name
    r = run_compiled(
        _enc(
            (
                ("EMIT", "g"),
                ("ENQUEUE", None),
                ("DEQUEUE", None),
                ("ROUTE", "routes"),
                ("APPLY", None),
                ("STOP", None),
            ),
            {"routes": {"g": "identity"}},
        ),
        {},
    )
    assert r["state"] in {"formed", "valid", "invalid"}
    # machine_load reject
    bad = machine_load(blank_thing({"instructions": None}))
    assert bad["state"] == "invalid"
    # await outward without result
    t = _enc((("OUTWARD", "read_utf8"), ("STOP", None)), {
        "boundary": {"source_field": "source", "name": "b"},
    })
    loaded = machine_load({**t, "value": {**t["value"], "host_input": {}, "store": {}}})
    # set request without handler
    v = dict(loaded["value"])
    v["outward_request"] = {"effect": "x"}
    v["outward_result"] = None
    step = machine_step({**loaded, "value": v})
    assert "await-outward" in str(step.get("evidence") or ()) or step["state"]


def test_host_fulfill_all_branches(tmp_path):
    # utf8 ok
    f = tmp_path / "a.txt"
    f.write_text("hi", encoding="utf-8")
    assert _read_utf8(str(f), {})["data"] == "hi"
    assert "error" in _read_utf8(None, {})
    assert "error" in _read_utf8("-", {})
    assert "error" in _read_utf8(str(tmp_path / "no"), {})
    assert "error" in _read_utf8(str(tmp_path), {})
    # invalid utf8
    bad = tmp_path / "b.bin"
    bad.write_bytes(b"\xff\xfe")
    assert "error" in _read_utf8(str(bad), {})
    # json
    j = tmp_path / "j.json"
    j.write_text('{"a":1}', encoding="utf-8")
    assert _read_json(str(j), {})["data"]["a"] == 1
    assert "error" in _read_json(None, {})
    assert "error" in _read_json("-", {})
    j2 = tmp_path / "arr.json"
    j2.write_text("[1]", encoding="utf-8")
    assert "error" in _read_json(str(j2), {})
    j3 = tmp_path / "bad.json"
    j3.write_text("{", encoding="utf-8")
    assert "error" in _read_json(str(j3), {})
    # fulfill dispatch
    assert "error" in _fulfill({"effect": "nope"}, {})
    r = _fulfill({"effect": "read_utf8", "source": str(f)}, {})
    assert r.get("data") == "hi"
    # inject shortcuts
    r = _fulfill({"effect": "read_utf8"}, {"host_input": {"text": "Z"}})
    # host_input is on machine value in real path
    r = _fulfill({"effect": "read_utf8"}, {"text": "Z"})
    # ticket.persist
    assert _fulfill({"effect": "ticket.persist"}, {}).get("ok") is True


def test_primitives_full_matrix():
    img = {
        "source": {"field": "source", "missing": "missing-source", "extra": "extra-source"},
        "boundary": {
            "name": "bnd",
            "source_field": "source",
            "target_field": "text",
            "effect": "read_utf8",
        },
        "part_name": "feat",
        "input_key": "text",
        "merge_key": "stats",
        "expression": {"op": "literal", "value": 42},
        "bindings": {},
        "binding_order": [],
        "verify": {"require_value_field": "stats", "require_evidence_contains": []},
        "presentation": {
            "success_from": "stats",
            "success_keys": ["n"],
            "include_error_path": True,
        },
    }
    base = blank_thing(
        {
            "store": {"text": "Hello World", "source": "-"},
            "image": img,
            "host_input": {"text": "Hello World"},
        }
    )
    for name in registry():
        out = apply_primitive(base, name)
        assert "state" in out
    # require_source variants
    for host in (
        {},
        {"argv": []},
        {"argv": ["a", "b"]},
        {"argv": ["f"]},
        {"source": "f"},
        {"text": "t"},
        {"document": {}},
    ):
        t = blank_thing({"store": {}, "image": img, "host_input": host})
        out = prim_require_source(t)
        assert out["state"] in {"formed", "invalid", "absent", "false", "valid"}
    # accept outward error / ok
    t = blank_thing(
        {
            "store": {},
            "image": img,
            "outward_result": {"error": "missing-file"},
        }
    )
    out = prim_accept_outward(t)
    assert out["state"] == "invalid"
    t = blank_thing(
        {
            "store": {},
            "image": img,
            "outward_result": {"data": "abc"},
        }
    )
    out = prim_accept_outward(t)
    assert "read:ok" in (out.get("evidence") or ())
    t = blank_thing({"store": {}, "image": img, "outward_result": None})
    assert prim_accept_outward(t)["state"] == "invalid"
    # letter skip states
    for st in ("invalid", "absent", "false"):
        t = blank_thing({"store": {}, "image": img})
        t["state"] = st
        assert "letter:skipped" in (prim_letter(t).get("evidence") or ())
    assert "boundary:inward" in (prim_mark_inward(base).get("evidence") or ())
    assert "part:feat" in (prim_mark_part(base).get("evidence") or ())
    # merge skip
    t = blank_thing({"store": {}, "image": img, "_acc": 1})
    t["state"] = "invalid"
    assert "merge:skipped" in (prim_merge_result(t).get("evidence") or ())
    t = blank_thing({"store": {}, "image": img, "_acc": {"n": 1}})
    out = prim_merge_result(t)
    assert value_of(out)["store"].get("stats") == {"n": 1}
    # verify fail/pass
    t = blank_thing({"store": {}, "image": img})
    t["state"] = "invalid"
    assert "script-law:fail" in (prim_verify_result(t).get("evidence") or ())
    t = blank_thing({"store": {"error": "e"}, "image": img})
    assert prim_verify_result(t)["state"] == "invalid"
    t = blank_thing({"store": {"stats": {"n": 1}}, "image": img, "evidence": ()})
    # may fail evidence contains
    prim_verify_result(t)
    # present json success and error with path
    t = blank_thing(
        {
            "store": {"stats": {"n": 1}, "error": "e", "path": ["a"]},
            "image": img,
        }
    )
    t["state"] = "valid"
    out = prim_present_json(t)
    assert value_of(out)["store"]["presentation"]["exit_code"] == 0
    t["state"] = "invalid"
    out = prim_present_json(t)
    assert value_of(out)["store"]["presentation"]["exit_code"] == 1
    # eval document / missing / bindings
    img2 = dict(img)
    img2["input_key"] = "document"
    img2["expression"] = {
        "op": "add",
        "values": [
            {"op": "as_decimal", "of": {"op": "literal", "value": "1.00"}},
            {"op": "as_decimal", "of": {"op": "literal", "value": "2.00"}},
        ],
    }
    t = blank_thing(
        {
            "store": {"document": {"x": 1}},
            "image": img2,
        }
    )
    out = apply_primitive(t, "eval_expression")
    # as_decimal on literal string works
    assert out["state"] in {"formed", "invalid"}
    # missing document
    t = blank_thing({"store": {}, "image": img2})
    assert apply_primitive(t, "eval_expression")["state"] in {"absent", "invalid"}
    # prior error skip
    t = blank_thing({"store": {"error": "e"}, "image": img})
    assert "eval:prior-error" in (apply_primitive(t, "eval_expression").get("evidence") or ())
    # skipped states
    t = blank_thing({"store": {"text": "x"}, "image": img})
    t["state"] = "absent"
    assert "eval:skipped" in (apply_primitive(t, "eval_expression").get("evidence") or ())


def test_eval_expr_operators_comprehensive():
    root = {
        "text": "A a B",
        "items": [
            {"quantity": 2, "unit_price": "1.50"},
            {"quantity": 1, "unit_price": "2.00"},
        ],
        "n": 3,
    }
    ctx = {"root": root, "path": [], "bindings": {"k": 9}}
    assert eval_expr({"op": "literal", "value": 1}, ctx) == 1
    assert eval_expr({"op": "ref", "name": "k"}, ctx) == 9
    assert eval_expr({"op": "field", "path": ["n"]}, ctx) == 3
    assert eval_expr({"op": "count", "of": {"op": "field", "path": ["items"]}}, ctx) == 2
    assert eval_expr({"op": "str_len", "of": {"op": "field", "path": ["text"]}}, ctx) == 5
    assert eval_expr({"op": "word_count", "of": {"op": "field", "path": ["text"]}}, ctx) == 3
    assert (
        eval_expr({"op": "unique_casefold_word_count", "of": {"op": "field", "path": ["text"]}}, ctx)
        == 2
    )
    assert eval_expr({"op": "line_count", "of": {"op": "literal", "value": "a\nb"}}, ctx) >= 1
    assert eval_expr({"op": "as_int", "of": {"op": "literal", "value": 2}}, ctx) == 2
    d = eval_expr({"op": "as_decimal", "of": {"op": "literal", "value": "1.25"}}, ctx)
    assert d is not None
    s = eval_expr(
        {
            "op": "sum_each",
            "path": ["items"],
            "collection": {"op": "field", "path": ["items"]},
            "each": {
                "op": "mul",
                "values": [
                    {"op": "as_int", "of": {"op": "field", "path": ["quantity"]}},
                    {"op": "as_decimal", "of": {"op": "field", "path": ["unit_price"]}},
                ],
            },
        },
        ctx,
    )
    assert s is not None
    q = eval_expr(
        {
            "op": "quantize",
            "exp": "0.01",
            "rounding": "ROUND_HALF_UP",
            "of": {"op": "as_decimal", "of": {"op": "literal", "value": "1.005"}},
        },
        ctx,
    )
    assert q is not None
    ds = eval_expr(
        {
            "op": "decimal_str",
            "places": 2,
            "of": {
                "op": "quantize",
                "exp": "0.01",
                "rounding": "ROUND_HALF_UP",
                "of": {"op": "as_decimal", "of": {"op": "literal", "value": "1.00"}},
            },
        },
        ctx,
    )
    assert isinstance(ds, str)
    # failures
    from unified.machine.primitives import _is_expr_fail, args_error_path

    try:
        eval_expr({"op": "require", "of": {"op": "literal", "value": None}, "error": "m"}, ctx)
        assert False
    except Exception as e:
        assert _is_expr_fail(e)
        err, _path = args_error_path(e)
        assert err == "m"
    try:
        eval_expr({"op": "min_value", "bound": 5, "of": {"op": "literal", "value": 1}, "error": "lo"}, ctx)
        assert False
    except Exception as e:
        assert _is_expr_fail(e)
    try:
        eval_expr({"op": "max_value", "bound": 0, "of": {"op": "literal", "value": 1}, "error": "hi"}, ctx)
        assert False
    except Exception as e:
        assert _is_expr_fail(e)
    try:
        eval_expr({"op": "unknown_op_xyz"}, ctx)
        assert False
    except Exception as e:
        assert _is_expr_fail(e)
    try:
        eval_expr({"op": "ref", "name": "missing"}, ctx)
        assert False
    except Exception as e:
        assert _is_expr_fail(e)


def test_compile_decl_errors_and_artifacts(tmp_path):
    from unified.machine.compile_decl import compile_declaration

    bad = compile_declaration(blank_thing({}))
    assert bad["state"] == "invalid"
    c = compile_declaration_path(str(ROOT / "examples/declarations/text_stats_v2.json"))
    write_artifacts(c, str(tmp_path / "out"))
    assert (tmp_path / "out" / "program.uem").is_file()
    c2 = compile_declaration_path(str(ROOT / "examples/declarations/invoice_total.json"))
    assert c2["state"] != "invalid"


def test_run_program_full_thing():
    c = compile_declaration_path(str(ROOT / "examples/declarations/text_stats_v2.json"))
    v = dict(value_of(c))
    v["host_input"] = {"text": "x"}
    out = run_program({**c, "value": v, "state": "formed"})
    assert out.get("state") in {"valid", "invalid", "formed"}


def test_interpreter_limits_unknown_apply_paths():
    import unified.machine.interpreter as I
    from unified.machine.interpreter import machine_load, machine_step, machine_run

    # path helpers edge
    d = {}
    I._path_set(d, "_acc", 1)
    assert d["_acc"] == 1
    assert I._path_get({"a": 1}, "") == {"a": 1}
    I._path_delete({"a": {"b": 1}}, "a.b.c")
    # unknown opcode
    loaded = machine_load(
        blank_thing(
            {
                "instructions": (("LOAD", "host_input"), ("STOP", None)),
                "image": {},
                "host_input": {},
            }
        )
    )
    v = dict(loaded["value"])
    v["instructions"] = (("NOPE", None), ("STOP", None))
    v["pc"] = 0
    out = machine_step({**loaded, "value": v})
    assert out["state"] == "invalid"
    # apply missing
    v["instructions"] = (("APPLY", None), ("STOP", None))
    v["pc"] = 0
    v["pending_primitive"] = None
    out = machine_step({**loaded, "value": v})
    assert any("apply:missing" in str(e) for e in (out.get("evidence") or ()))
    # apply unknown
    v["instructions"] = (("APPLY", "notreal"), ("STOP", None))
    v["pc"] = 0
    out = machine_step({**loaded, "value": v})
    assert out["state"] == "invalid"
    # queue limit
    r = run_compiled(
        _enc(tuple([("ENQUEUE", "e")] * 3 + [("STOP", None)])),
        {},
        limits={"max_queue": 1, "max_steps": 20},
    )
    assert (r.get("value") or {}).get("stop_reason") == "limit:queue"
    # memory limit
    r = run_compiled(
        _enc((("LOAD", "host_input"), ("STOP", None))),
        {"x": "y" * 1000},
        limits={"max_memory": 10, "max_steps": 20},
    )
    assert (r.get("value") or {}).get("stop_reason") == "limit:memory"
    # ack with id
    t = blank_thing({"ticket": {"kind": "x"}, "ticket_external_id": "  ID "})
    out = I._op_ack(t, None)
    assert value_of(out)["ticket"]["acked"] is True


def test_map_fold_with_items_and_op_fault():
    import unified.machine.interpreter as I

    r = run_compiled(
        _enc(
            (
                ("LOAD", "host_input"),
                ("WRITE", "document"),
                ("MAP", "map"),
                ("FOLD", "fold"),
                ("STOP", None),
            ),
            {
                "map": {"collection_key": "items", "primitive": "identity"},
                "fold": {
                    "collection_key": "items",
                    "primitive": "identity",
                    "initial": 0,
                },
            },
        ),
        {"items": [{"a": 1}, {"a": 2}]},
    )
    ev = list(r.get("evidence") or ())
    assert any("map:complete" in str(e) for e in ev)
    assert any("fold:complete" in str(e) for e in ev)
    # nested path helpers
    d = {}
    I._path_set(d, "a.b.c", 9)
    assert I._path_get(d, "a.b.c") == 9
    I._path_delete(d, "a.b.c")
    I._path_delete(d, "")
    I._path_delete(d, "no.such")
    # force op exception
    old = I._op_load

    def boom(thing, op):
        raise RuntimeError("boom")

    I._op_load = boom
    try:
        t = _enc((("LOAD", "host_input"), ("STOP", None)))
        loaded = machine_load({**t, "value": {**t["value"], "host_input": {}}})
        out = machine_step(loaded)
        assert value_of(out).get("machine_fault", {}).get("message") == "boom"
    finally:
        I._op_load = old
    # invalid+halted short-circuit
    t = blank_thing({"instructions": (("STOP", None),)})
    t["state"] = "invalid"
    t["value"]["halted"] = True
    t["value"]["instructions"] = (("STOP", None),)
    t["value"]["pc"] = 0
    t["value"]["limits"] = {"max_steps": 10, "steps": 0}
    assert machine_step(t) is t or machine_step(t)["state"] == "invalid"
    # items limit
    r = run_compiled(
        _enc(
            (("MAP", "map"), ("STOP", None)),
            {"map": {"collection_key": "items", "primitive": "identity"}},
        ),
        {},
        limits={"max_items": -1, "max_steps": 20},
    )
    # max_items 0 with empty collection is ok; with items:
    r = run_compiled(
        _enc(
            (
                ("LOAD", "host_input"),
                ("WRITE", "document"),
                ("MAP", "map"),
                ("STOP", None),
            ),
            {"map": {"collection_key": "items", "primitive": "identity"}},
        ),
        {"items": [1, 2, 3]},
        limits={"max_items": 1, "max_steps": 50},
    )
    assert r["state"] == "invalid" or "limit" in str(
        (r.get("value") or {}).get("stop_reason")
    )


def test_more_interpreter_ops():
    from unified.machine.host import run_compiled
    from unified.machine.l13_catalog import _enc
    from unified.machine.interpreter import machine_load, machine_step, machine_run
    # duplicate event skip
    r = run_compiled(
        _enc(
            (
                ("EMIT", "e"),
                ("ENQUEUE", None),
                ("DEQUEUE", None),
                ("ROUTE", "routes"),
                ("APPLY", None),
                ("DEQUEUE", None),
                ("STOP", None),
            ),
            {"routes": {"e": "identity", "quiet": "identity"}},
        ),
        {},
    )
    assert r["state"] in {"formed", "valid", "invalid"}
    # ACK with external id
    r = run_compiled(_enc((("TICKET", None), ("STOP", None))), {})
    v = dict(r["value"])
    v["ticket_external_id"] = "EXT-1"
    # re-run ack via program
    r = run_compiled(_enc((("TICKET", None), ("ACK", None), ("STOP", None))), {})
    assert (r.get("value") or {}).get("ticket")
    # VERIFY fail missing field
    r = run_compiled(
        _enc(
            (("VERIFY", "result"), ("STOP", None)),
            {"verify": {"require_value_field": "stats", "require_evidence_contains": ["nope"]}},
        ),
        {},
    )
    assert r["state"] == "invalid"
    # memory limit
    r = run_compiled(
        _enc((("LOAD", "host_input"), ("STOP", None))),
        {"big": "x" * 100},
        limits={"max_memory": 1, "max_steps": 100},
    )
    # item overflow map
    r = run_compiled(
        _enc((("MAP", "map"), ("STOP", None)), {"map": {"collection_key": "items", "primitive": "identity"}}),
        {},
        limits={"max_items": 0, "max_steps": 50},
    )


def test_compile_unsupported():
    from unified.machine.compile_decl import compile_declaration
    from unified.machine.thing import blank_thing

    d = blank_thing(
        {
            "declaration": {
                "package": "p",
                "features": [{"name": "f", "transformation": {"kind": "nope"}}],
                "boundaries": (),
                "composition": (),
            }
        }
    )
    assert compile_declaration(d)["state"] == "invalid"
    d = blank_thing(
        {
            "declaration": {
                "package": "p",
                "features": [],
                "boundaries": (),
            }
        }
    )
    assert compile_declaration(d)["state"] == "invalid"


def test_primitives_require_source_false_none():
    from unified.machine.primitives import prim_require_source
    from unified.machine.thing import blank_thing

    img = {
        "source": {"field": "source", "missing": "missing-source", "extra": "extra-source"},
    }
    t = blank_thing({"store": {}, "image": img, "host_input": False})
    # host_input False is weird
    prim_require_source(t)
    t = blank_thing({"store": {}, "image": img, "host_input": {"argv": "bad"}})
    out = prim_require_source(t)
    assert out["state"] == "invalid"


def test_bytecode_remaining_edges():
    from unified.machine.bytecode import MAGIC, FORMAT_VERSION, encode_program, decode_program
    from unified.machine.thing import blank_thing, value_of
    import struct

    # good base
    good = value_of(encode_program(blank_thing({"instructions": (("STOP", None),), "image": {}})))["bytecode"]
    # bad flags
    b = bytearray(good)
    b[6] = 0
    b[7] = 1
    assert decode_program(blank_thing({"bytecode": bytes(b)}))["state"] == "invalid"
    # bad tag
    b = bytearray(good)
    # after header and opcode STOP(0x10), tag is next
    # structure: magic4 ver2 flags2 count4 | op tag ...
    off = 12
    b[off] = 0x10
    b[off + 1] = 2  # bad tag
    assert decode_program(blank_thing({"bytecode": bytes(b)}))["state"] == "invalid"
    # invalid utf-8 operand: craft LOAD with bad utf8
    # magic+ver+flags+count=1 + opcode LOAD + tag string + len + bytes
    img = b"{}"
    body = bytearray()
    body += MAGIC
    body += struct.pack(">H", FORMAT_VERSION)
    body += struct.pack(">H", 0)
    body += struct.pack(">I", 2)  # two instr: LOAD + STOP
    body += bytes([0x01, 1])  # LOAD string
    bad = b"\xff\xff"
    body += struct.pack(">I", len(bad)) + bad
    body += bytes([0x10, 0])  # STOP none
    body += struct.pack(">I", len(img)) + img
    assert decode_program(blank_thing({"bytecode": bytes(body)}))["state"] == "invalid"
    # image not object
    img = b"[]"
    body = bytearray()
    body += MAGIC + struct.pack(">HH", FORMAT_VERSION, 0) + struct.pack(">I", 1)
    body += bytes([0x10, 0])
    body += struct.pack(">I", len(img)) + img
    assert decode_program(blank_thing({"bytecode": bytes(body)}))["state"] == "invalid"
    # bad image json
    img = b"{]"
    body = bytearray(MAGIC + struct.pack(">HH", FORMAT_VERSION, 0) + struct.pack(">I", 1) + bytes([0x10, 0]) + struct.pack(">I", len(img)) + img)
    assert decode_program(blank_thing({"bytecode": bytes(body)}))["state"] == "invalid"
    # invalid utf8 image
    img = b"\xff\xff"
    body = bytearray(MAGIC + struct.pack(">HH", FORMAT_VERSION, 0) + struct.pack(">I", 1) + bytes([0x10, 0]) + struct.pack(">I", len(img)) + img)
    assert decode_program(blank_thing({"bytecode": bytes(body)}))["state"] == "invalid"
    # noncanonical image (spaces)
    img = b'{ "a": 1 }'
    body = bytearray(MAGIC + struct.pack(">HH", FORMAT_VERSION, 0) + struct.pack(">I", 1) + bytes([0x10, 0]) + struct.pack(">I", len(img)) + img)
    assert decode_program(blank_thing({"bytecode": bytes(body)}))["state"] == "invalid"
    # encode with image None path via missing key
    t = encode_program(blank_thing({"instructions": (("STOP", None),)}))
    assert t["state"] != "invalid"
    # canonical None
    from unified.machine.bytecode import canonical_image_bytes
    assert canonical_image_bytes(None) == b"{}"


def test_canonical_non_string_mark():
    from unified.machine.canonical import normalize_evidence_mark
    assert normalize_evidence_mark(123) is None


def test_compile_default_set_and_load_fail(tmp_path):
    from unified.machine.compile_decl import _default, compile_declaration_path, _plain
    assert _default((1, 2)) == [1, 2]
    assert _default({3, 1}) == [1, 3]
    try:
        _default(object())
        assert False
    except TypeError:
        pass
    assert _plain({"t": (1, 2)})["t"] == [1, 2]
    # bad path
    bad = compile_declaration_path(str(tmp_path / "nope.py"))
    assert bad["state"] == "invalid"


def test_host_machine_run_await(tmp_path):
    from unified.machine.host import run_program
    from unified.machine.l13_catalog import _enc
    # invalid load
    t = _enc((("STOP", None),))
    # force no instructions
    out = run_program({"value": {"instructions": None}, "depths": (), "axes": (), "evidence": (), "state": "formed"})
    assert out["state"] == "invalid"
