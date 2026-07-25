"""L10 event runtime — tickets, redaction, determinism."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from unified.boundary import inward
from unified.generator import run_build
from unified.generator.event_emit import emit_event_runtime_module


DECL = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "declarations"
    / "text_stats_v2.py"
)


def _load_runtime(tmp_path: Path):
    built = run_build(
        inward(
            {
                "declaration_path": str(DECL),
                "parent": str(tmp_path),
                "project_name": "ticket-app",
            }
        )
    )
    assert built["state"] == "valid", built.get("evidence")
    root = tmp_path / "ticket-app"
    import sys
    import importlib

    sys.path.insert(0, str(root))
    for mod in list(sys.modules):
        if mod.startswith("uc_text_stats_v2"):
            del sys.modules[mod]
    return importlib.import_module("uc_text_stats_v2.event_runtime"), root


def test_event_runtime_module_has_audited_primitives():
    src = emit_event_runtime_module()
    for name in (
        "def route",
        "def emit",
        "def until_quiet",
        "def map_event",
        "def fold_event",
        "def open_ticket",
        "def call_part",
    ):
        assert name in src


def test_ticket_creation_redaction_dedup_outbox(tmp_path):
    ert, _root = _load_runtime(tmp_path)
    outbox = tmp_path / "tickets"
    thing = {
        "value": {
            "exception": {
                "operation": "feature.x",
                "error_type": "RuntimeError",
                "message": "password=hunter2 token=abc",
                "occurred_at": "static",
            },
            "ticket_outbox": str(outbox),
        },
        "depths": (),
        "axes": (),
        "evidence": ("a", "b", "c"),
        "state": "invalid",
    }
    t1 = ert.open_ticket(thing)
    assert t1["state"] == "invalid"
    ticket = t1["value"]["ticket"]
    assert ticket["kind"] == "unhandled-exception"
    assert "hunter2" not in ticket["message"]
    assert "password" not in ticket["message"].lower() or "[redacted]" in ticket["message"]
    assert ticket["correlation_id"]
    assert "boundary:ticket.open" in t1["evidence"]
    files = list(outbox.glob("*.json"))
    assert len(files) == 1
    # second open — one ticket only
    t2 = ert.open_ticket(t1)
    assert t2["value"]["ticket"]["correlation_id"] == ticket["correlation_id"]
    files2 = list(outbox.glob("*.json"))
    assert len(files2) == 1


def test_ack_requires_external_id(tmp_path):
    ert, _root = _load_runtime(tmp_path)
    outbox = tmp_path / "tickets2"
    thing = {
        "value": {
            "exception": {
                "operation": "op",
                "error_type": "Error",
                "message": "boom",
                "occurred_at": "static",
            },
            "ticket_outbox": str(outbox),
        },
        "depths": (),
        "axes": (),
        "evidence": ("e",),
        "state": "invalid",
    }
    opened = ert.open_ticket(thing)
    pending = ert.ack_ticket(opened)
    assert pending["value"]["ticket"].get("acked") is False
    with_id = {
        **opened,
        "value": {
            **opened["value"],
            "ticket_external_id": "EXT-1",
        },
    }
    acked = ert.ack_ticket(with_id)
    assert acked["value"]["ticket"]["acked"] is True
    assert acked["value"]["ticket"]["external_id"] == "EXT-1"


def test_preserve_for_retry_keeps_outbox(tmp_path):
    ert, _root = _load_runtime(tmp_path)
    outbox = tmp_path / "tickets3"
    thing = {
        "value": {
            "exception": {
                "operation": "op",
                "error_type": "Error",
                "message": "boom",
                "occurred_at": "static",
            },
            "ticket_outbox": str(outbox),
        },
        "depths": (),
        "axes": (),
        "evidence": ("e",),
        "state": "invalid",
    }
    opened = ert.open_ticket(thing)
    preserved = ert.preserve_for_retry(opened)
    assert preserved["value"]["event"] == "ticket.delivery_failed"
    assert list(outbox.glob("*.json"))


def test_call_part_unhandled_exception_routes_to_ticket(tmp_path):
    ert, root = _load_runtime(tmp_path)
    import sys
    import importlib

    sys.path.insert(0, str(root))
    compose = importlib.import_module("uc_text_stats_v2.compose")

    def boom(thing):
        raise RuntimeError("token=xyz should redact later")

    out = ert.call_part(
        {
            "value": {"ticket_outbox": str(tmp_path / "t4")},
            "depths": (),
            "axes": (),
            "evidence": (),
            "state": "formed",
        },
        boom,
        "step.next",
    )
    assert out["value"]["event"] == "exception.unhandled"
    # full program still works for normal path
    sample = tmp_path / "ok.txt"
    sample.write_text("hi", encoding="utf-8")
    ok = compose.program({"source": str(sample)})
    assert ok["state"] == "valid"
    # validation failure must not open a ticket
    bad = compose.program({"source": str(tmp_path / "missing-file-xyz")})
    assert bad["state"] != "valid"
    assert not (bad.get("value") or {}).get("ticket")


def test_domain_parts_and_compose_have_zero_explicit_cf(tmp_path):
    import ast

    built = run_build(
        inward(
            {
                "declaration_path": str(DECL),
                "parent": str(tmp_path),
                "project_name": "cf-app",
            }
        )
    )
    assert built["state"] == "valid"
    pkg = tmp_path / "cf-app" / "uc_text_stats_v2"
    forbidden = (ast.If, ast.For, ast.While, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.Try)
    for name in ("parts.py", "compose.py"):
        tree = ast.parse((pkg / name).read_text(encoding="utf-8"))
        hits = [type(n).__name__ for n in ast.walk(tree) if isinstance(n, forbidden)]
        assert hits == [], f"{name} has control flow: {hits}"
