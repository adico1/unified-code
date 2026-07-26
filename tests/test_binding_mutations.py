"""Mutations that must be detected: binding-order corruption, missing vs null.

No invoice vocabulary in core assertions — only generic binding behavior.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from unified.machine.bytecode import encode_program, _decode
from unified.machine.compile_decl import (
    _binding_eval_order,
    compile_declaration_path,
)
from unified.machine.host import run_compiled
from unified.machine.thing import blank_thing, value_of

ROOT = Path(__file__).resolve().parents[1]
UEM_C = os.environ.get("UEM_C", str(ROOT / "c" / "build" / "uem-c"))


def _compile_invoice():
    return compile_declaration_path(str(ROOT / "examples/declarations/invoice_total.py"))


def _host_basic():
    return {
        "document": {
            "tax_rate": "0.10",
            "items": [
                {"description": "a", "quantity": 2, "unit_price": "10.00"},
                {"description": "b", "quantity": 1, "unit_price": "5.50"},
            ],
        }
    }


def test_topo_order_not_alphabetical():
    bindings = {
        "tax": {
            "op": "mul",
            "values": [
                {"op": "ref", "name": "subtotal"},
                {"op": "ref", "name": "tax_rate"},
            ],
        },
        "tax_rate": {"op": "literal", "value": "0.1"},
        "subtotal": {"op": "literal", "value": "1"},
    }
    order = _binding_eval_order(bindings)
    assert order.index("tax_rate") < order.index("tax")
    assert order.index("subtotal") < order.index("tax")


def test_binding_order_mutation_detected():
    compiled = _compile_invoice()
    assert compiled.get("state") != "invalid"
    v = dict(value_of(compiled))
    image = dict(v["image"])
    image["binding_order"] = sorted(image["bindings"].keys())
    assert image["binding_order"] == ["subtotal", "tax", "tax_rate", "total"]
    mutated = encode_program(
        blank_thing({"instructions": v["instructions"], "image": image})
    )
    r = run_compiled(mutated, _host_basic())
    assert r.get("state") == "invalid"
    store = value_of(r).get("store") or {}
    assert store.get("error") == "missing-binding"


def test_unknown_binding_ref_at_compile():
    with pytest.raises(ValueError, match="unknown-binding-ref"):
        _binding_eval_order({"a": {"op": "ref", "name": "does_not_exist"}})


def test_null_binding_distinct_from_missing():
    from unified.machine.primitives import eval_expr, _ExprFail

    assert eval_expr({"op": "ref", "name": "x"}, {"bindings": {"x": None}, "path": []}) is None
    with pytest.raises(_ExprFail) as ei:
        eval_expr({"op": "ref", "name": "x"}, {"bindings": {}, "path": []})
    assert ei.value.error == "missing-binding"


def test_fresh_compile_invoice_valid():
    compiled = _compile_invoice()
    r = run_compiled(compiled, _host_basic())
    assert r.get("state") == "valid"
    text = (value_of(r).get("presentation") or {}).get("text")
    assert text == '{"item_count":2,"subtotal":"25.50","tax":"2.55","total":"28.05"}'


def test_artifact_binding_order_matches_compile():
    bc = (ROOT / "artifacts/uem/invoice_total/program.uem").read_bytes()
    _, image, sid = _decode(bc)
    compiled = _compile_invoice()
    assert sid == value_of(compiled).get("program_sha256")
    assert image["binding_order"] == value_of(compiled)["image"]["binding_order"]
    assert image["binding_order"] == ["subtotal", "tax_rate", "tax", "total"]


def test_c_detects_binding_order_mutation():
    if not Path(UEM_C).is_file():
        pytest.skip("uem-c not built")
    compiled = _compile_invoice()
    v = dict(value_of(compiled))
    image = dict(v["image"])
    image["binding_order"] = sorted(image["bindings"].keys())
    mutated = encode_program(
        blank_thing({"instructions": v["instructions"], "image": image})
    )
    raw = value_of(mutated).get("bytecode")
    assert isinstance(raw, (bytes, bytearray))
    tmp = ROOT / "c" / "tests" / "vectors" / "_mut_bindorder.uem"
    tmp.write_bytes(bytes(raw))
    try:
        out = subprocess.check_output(
            [
                UEM_C,
                "run",
                str(tmp),
                "--host",
                json.dumps(_host_basic(), separators=(",", ":")),
            ],
            text=True,
        )
        d = json.loads(out)
        assert d["state"] == "invalid"
        assert d.get("error") == "missing-binding" or "missing-binding" in (
            (d.get("presentation") or {}).get("text") or ""
        )
    finally:
        if tmp.exists():
            tmp.unlink()
