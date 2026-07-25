"""UEM-16 v0.1 — machine, bytecode, compile, compatibility, gauntlet."""

from __future__ import annotations

import json
import re
from pathlib import Path

from unified.boundary import inward
from unified.generator import run_build
from unified.machine import (
    compile_declaration,
    decode_program,
    encode_program,
    measure_uem,
    program_identity,
    run_program,
    run_uem_gauntlet,
    validate_bytecode,
    validate_symbolic,
)
from unified.machine.compile_decl import compile_declaration_path, write_artifacts
from unified.machine.host import run_compiled
from unified.machine.thing import blank_thing, value_of


ROOT = Path(__file__).resolve().parents[1]
DECL_TEXT = ROOT / "examples" / "declarations" / "text_stats_v2.py"
DECL_INV = ROOT / "examples" / "declarations" / "invoice_total.py"


def test_opcode_table_has_16():
    from unified.machine.opcodes import OPCODES

    assert len(OPCODES) == 16
    assert set(OPCODES.values()) == {
        "LOAD",
        "READ",
        "WRITE",
        "DELETE",
        "EMIT",
        "ENQUEUE",
        "DEQUEUE",
        "ROUTE",
        "APPLY",
        "MAP",
        "FOLD",
        "VERIFY",
        "TICKET",
        "OUTWARD",
        "ACK",
        "STOP",
    }


def test_encode_decode_roundtrip_and_identity():
    prog = blank_thing(
        {
            "instructions": (
                ("LOAD", "host_input"),
                ("EMIT", "input.received"),
                ("STOP", None),
            ),
            "image": {"k": 1},
        }
    )
    enc = encode_program(prog)
    assert enc["state"] != "invalid"
    raw = value_of(enc)["bytecode"]
    identity = value_of(enc)["program_sha256"]
    dec = decode_program(blank_thing({"bytecode": raw}))
    assert dec["state"] != "invalid"
    assert value_of(dec)["program_sha256"] == identity
    assert value_of(dec)["instructions"][0] == ("LOAD", "host_input")
    # noncanonical: trailing byte
    bad = validate_bytecode(blank_thing({"bytecode": raw + b"\x00"}))
    assert bad["state"] == "invalid"
    # truncated
    bad2 = validate_bytecode(blank_thing({"bytecode": raw[:10]}))
    assert bad2["state"] == "invalid"


def test_missing_stop_rejected():
    t = validate_symbolic(
        blank_thing({"instructions": (("LOAD", "host_input"),), "image": {}})
    )
    assert t["state"] == "invalid"
    assert any("missing-stop" in e for e in t["evidence"])


def test_unknown_opcode_byte_rejected():
    from unified.machine.opcodes import MAGIC

    # version 1, flags 0, 1 instr, opcode 0x7F
    raw = MAGIC + b"\x00\x01\x00\x00\x00\x00\x00\x01\x7f\x00\x00\x00\x00\x02{}"
    # fix image length properly
    img = b"{}"
    raw = (
        MAGIC
        + b"\x00\x01\x00\x00"
        + (1).to_bytes(4, "big")
        + bytes([0x7F, 0x00])
        + len(img).to_bytes(4, "big")
        + img
    )
    t = validate_bytecode(blank_thing({"bytecode": raw}))
    assert t["state"] == "invalid"


def test_compile_text_stats_and_execute():
    compiled = compile_declaration_path(str(DECL_TEXT))
    assert compiled["state"] != "invalid", compiled.get("evidence")
    out = run_compiled(compiled, {"text": "Go go GO"})
    assert out["state"] == "valid", (out.get("state"), out.get("evidence"), value_of(out))
    stats = value_of(out).get("stats")
    assert stats == {
        "characters": 8,
        "lines": 1,
        "words": 3,
        "unique_words": 1,
    }
    pres = value_of(out).get("presentation") or {}
    assert pres["exit_code"] == 0
    assert json.loads(pres["text"]) == stats
    # key order
    assert pres["text"].startswith('{"characters"')


def test_compile_invoice_and_execute():
    compiled = compile_declaration_path(str(DECL_INV))
    assert compiled["state"] != "invalid", compiled.get("evidence")
    doc = {
        "currency": "USD",
        "items": [
            {"description": "a", "quantity": 2, "unit_price": "10.00"},
            {"description": "b", "quantity": 1, "unit_price": "5.50"},
        ],
        "tax_rate": "0.10",
    }
    out = run_compiled(compiled, {"document": doc})
    assert out["state"] == "valid", (out.get("state"), value_of(out), out.get("evidence"))
    stats = value_of(out).get("stats")
    assert stats == {
        "item_count": 2,
        "subtotal": "25.50",
        "tax": "2.55",
        "total": "28.05",
    }


def test_validation_failure_no_ticket():
    compiled = compile_declaration_path(str(DECL_INV))
    out = run_compiled(
        compiled,
        {"document": {"tax_rate": "0.10", "items": [{"quantity": 0, "unit_price": "1.00"}]}},
    )
    assert out["state"] != "valid"
    assert not value_of(out).get("ticket")


def test_compatibility_matches_generated_app(tmp_path):
    """External JSON matches Python-generated app for the same fixtures."""
    # build classic app
    built = run_build(
        inward(
            {
                "declaration_path": str(DECL_TEXT),
                "parent": str(tmp_path),
                "project_name": "compat-ts",
            }
        )
    )
    assert built["state"] == "valid"
    import sys
    import importlib

    root = tmp_path / "compat-ts"
    sys.path.insert(0, str(root))
    for mod in list(sys.modules):
        if mod.startswith("uc_text_stats_v2"):
            del sys.modules[mod]
    compose = importlib.import_module("uc_text_stats_v2.compose")
    sample = tmp_path / "s.txt"
    sample.write_text("Go go GO", encoding="utf-8")
    classic = compose.program({"source": str(sample)})
    classic_text = classic["value"]["presentation"]["text"]

    compiled = compile_declaration_path(str(DECL_TEXT))
    uem = run_compiled(compiled, {"source": str(sample)})
    uem_text = value_of(uem)["presentation"]["text"]
    assert uem_text == classic_text
    assert uem["state"] == classic["state"]


def test_compatibility_invoice_file(tmp_path):
    built = run_build(
        inward(
            {
                "declaration_path": str(DECL_INV),
                "parent": str(tmp_path),
                "project_name": "compat-inv",
            }
        )
    )
    assert built["state"] == "valid"
    import sys
    import importlib

    root = tmp_path / "compat-inv"
    sys.path.insert(0, str(root))
    for mod in list(sys.modules):
        if mod.startswith("uc_invoice_total"):
            del sys.modules[mod]
    compose = importlib.import_module("uc_invoice_total.compose")
    doc = {"tax_rate": "0.20", "items": []}
    sample = tmp_path / "i.json"
    sample.write_text(json.dumps(doc), encoding="utf-8")
    classic = compose.program({"source": str(sample)})
    classic_text = classic["value"]["presentation"]["text"]

    compiled = compile_declaration_path(str(DECL_INV))
    uem = run_compiled(compiled, {"source": str(sample)})
    assert value_of(uem)["presentation"]["text"] == classic_text
    assert uem["state"] == classic["state"]


def test_machine_source_has_no_domain_vocabulary():
    machine_dir = ROOT / "unified" / "machine"
    # Runtime/host kernel sources — exclude gauntlet harnesses that load declarations.
    banned = (
        "invoice",
        "text_stats",
        "calculate_stats",
        "calculate_totals",
        "unique_words",
        "subtotal",
        "uc_text",
        "uc_invoice",
    )
    skip = {"l11.py", "gauntlet.py", "measure.py"}
    for path in machine_dir.rglob("*.py"):
        if path.name in skip:
            continue
        text = path.read_text(encoding="utf-8")
        for word in banned:
            assert word not in text, f"{path.name} contains {word!r}"


def test_uem_gauntlet_pass():
    compiled = compile_declaration_path(str(DECL_TEXT))
    g = run_uem_gauntlet(blank_thing({"compiled": compiled}))
    assert g["value"]["verdict"] == "pass", g["value"].get("uem_gauntlet")


def test_artifacts_written(tmp_path):
    compiled = compile_declaration_path(str(DECL_TEXT))
    write_artifacts(compiled, str(tmp_path / "uem-out"))
    assert (tmp_path / "uem-out" / "program.uem").is_file()
    assert (tmp_path / "uem-out" / "program.symbolic.json").is_file()
    raw = (tmp_path / "uem-out" / "program.uem").read_bytes()
    dec = decode_program(blank_thing({"bytecode": raw}))
    assert dec["state"] != "invalid"


def test_measure_runs():
    report = measure_uem(
        blank_thing(
            {
                "declaration_paths": [str(DECL_TEXT), str(DECL_INV)],
                "iterations": 5,
            }
        )
    )
    assert report["state"] == "valid"
    ms = report["value"]["measurements"]
    assert len(ms) == 2
    assert ms[0]["bytecode_size"] > 0
    assert ms[0]["compile_p95_ns"] is not None
    cf = report["value"]["control_flow_by_layer"]
    assert "machine" in cf
