"""L10 kernel contracts — termination, ordering, duplication, tickets, failure."""

from __future__ import annotations

import ast
import json
import sys
import importlib
from pathlib import Path

from unified.boundary import inward
from unified.generator import run_build
from unified.generator.event_emit import PRIMITIVE_CONTRACTS, emit_event_runtime_module


DECL = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "declarations"
    / "text_stats_v2.json"
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
    sys.path.insert(0, str(root))
    for mod in list(sys.modules):
        if mod.startswith("uc_text_stats_v2"):
            del sys.modules[mod]
    return importlib.import_module("uc_text_stats_v2.event_runtime"), root


def _base_thing(**value_extra):
    return {
        "value": {**value_extra},
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": "formed",
    }


def test_contracts_document_exists():
    assert "until_quiet" in PRIMITIVE_CONTRACTS
    assert "construct_ticket" in PRIMITIVE_CONTRACTS
    assert "outward_ticket_store" in PRIMITIVE_CONTRACTS
    src = emit_event_runtime_module()
    for name in (
        "def route",
        "def emit",
        "def until_quiet",
        "def map_event",
        "def fold_event",
        "def construct_ticket",
        "def outward_ticket_store",
        "def reload_unacked_tickets",
        "def call_part",
        "DEFAULT_MAX_STEPS",
    ):
        assert name in src


def test_until_quiet_queue_vs_limit_exhaustion_distinct(tmp_path):
    ert, _ = _load_runtime(tmp_path)

    def ping(thing):
        return ert.emit(thing, "done")

    routes = {
        "ping": ping,
        "done": lambda t: t,
    }
    quiet = ert.until_quiet(
        ert.enqueue(_base_thing(), "ping"),
        routes,
        max_steps=100,
    )
    evidence = quiet["evidence"]
    assert "event:until_quiet:queue_exhausted" in evidence
    assert "event:until_quiet:limit_exhausted" not in evidence
    assert quiet["value"].get("until_quiet_end") == "queue_exhausted"

    # self-reenqueueing handler without progress hits limit
    def loop(thing):
        # same event name, new id each time — still burns steps
        return ert.enqueue(thing, "loop")

    limited = ert.until_quiet(
        ert.enqueue(_base_thing(), "loop"),
        {"loop": loop},
        max_steps=5,
    )
    assert "event:until_quiet:limit_exhausted" in limited["evidence"]
    assert "event:until_quiet:queue_exhausted" not in limited["evidence"]
    assert limited["value"].get("until_quiet_end") == "limit_exhausted"
    assert limited["value"].get("error") == "event-step-limit"
    assert limited["state"] == "invalid"
    # limit must not open a ticket
    assert not limited["value"].get("ticket")


def test_event_identity_skips_duplicate_processing(tmp_path):
    ert, _ = _load_runtime(tmp_path)
    calls = []

    def once(thing):
        calls.append(_event_name(thing, ert))
        return thing

    def _event_name(thing, ert_mod):
        return thing["value"].get("event")

    # enqueue same identity twice
    t = _base_thing()
    t = ert.enqueue(t, "once", event_id="fixed-id-1")
    t = ert.enqueue(t, "once", event_id="fixed-id-1")
    out = ert.until_quiet(t, {"once": once}, max_steps=20)
    assert calls == ["once"]
    assert any("duplicate-skipped" in str(e) for e in out["evidence"])


def test_emit_enqueue_ordering(tmp_path):
    ert, _ = _load_runtime(tmp_path)
    t = _base_thing()
    t = ert.emit(t, "a")
    t = ert.enqueue(t, "b")
    t = ert.enqueue(t, "c")
    t = ert.dequeue(t)
    assert t["value"]["event"] == "b"
    t = ert.dequeue(t)
    assert t["value"]["event"] == "c"
    t = ert.dequeue(t)
    assert t["value"]["event"] == "quiet"
    # evidence order preserves emit then enqueues
    marks = [e for e in t["evidence"] if e.startswith("event:")]
    assert marks[0] == "event:a"
    assert "event:enqueue:b" in marks
    assert "event:enqueue:c" in marks


def test_construct_ticket_pure_no_io(tmp_path):
    ert, _ = _load_runtime(tmp_path)
    outbox = tmp_path / "should_not_exist"
    thing = {
        "value": {
            "exception": {
                "operation": "op.x",
                "error_type": "RuntimeError",
                "message": "password=hunter2 token=abc",
                "occurred_at": "static",
            },
            "ticket_outbox": str(outbox),
        },
        "depths": (),
        "axes": (),
        "evidence": ("a", "b"),
        "state": "invalid",
    }
    built = ert.construct_ticket(thing)
    assert built["value"]["event"] == "ticket.persist.requested"
    assert "event:ticket.construct" in built["evidence"]
    ticket = built["value"]["ticket"]
    assert ticket["message"] == "[redacted-message]"
    assert "hunter2" not in ticket["message"]
    assert ticket["correlation_id"] == ticket["ticket_id"]
    # pure: no files written
    assert not outbox.exists()


def test_ticket_identity_deterministic(tmp_path):
    ert, _ = _load_runtime(tmp_path)
    payload = {
        "value": {
            "exception": {
                "operation": "op",
                "error_type": "Error",
                "message": "same",
                "occurred_at": "static",
            }
        },
        "depths": (),
        "axes": (),
        "evidence": ("e1", "e2"),
        "state": "invalid",
    }
    t1 = ert.construct_ticket(payload)
    t2 = ert.construct_ticket(payload)
    assert t1["value"]["ticket"]["correlation_id"] == t2["value"]["ticket"]["correlation_id"]


def test_outward_persist_atomic_and_dedup(tmp_path):
    ert, _ = _load_runtime(tmp_path)
    outbox = tmp_path / "tickets"
    thing = {
        "value": {
            "exception": {
                "operation": "feature.x",
                "error_type": "RuntimeError",
                "message": "password=hunter2",
                "occurred_at": "static",
            },
            "ticket_outbox": str(outbox),
        },
        "depths": (),
        "axes": (),
        "evidence": ("a", "b", "c"),
        "state": "invalid",
    }
    constructed = ert.construct_ticket(thing)
    persisted = ert.outward_ticket_store(constructed)
    assert persisted["value"]["event"] == "ticket.persisted"
    assert "boundary:ticket.persist" in persisted["evidence"]
    files = list(outbox.glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert "hunter2" not in data["message"]
    # second persist same id — still one file
    again = ert.outward_ticket_store(persisted)
    assert again["value"]["event"] == "ticket.persisted"
    assert len(list(outbox.glob("*.json"))) == 1


def test_persist_failure_emergency_no_recursive_ticket(tmp_path):
    ert, _ = _load_runtime(tmp_path)
    # outbox path that cannot be created as directory file conflict
    blocked = tmp_path / "blocked"
    blocked.write_text("not-a-dir", encoding="utf-8")
    thing = {
        "value": {
            "exception": {
                "operation": "op",
                "error_type": "Error",
                "message": "boom",
                "occurred_at": "static",
            },
            "ticket_outbox": str(blocked),
        },
        "depths": (),
        "axes": (),
        "evidence": ("e",),
        "state": "invalid",
    }
    constructed = ert.construct_ticket(thing)
    failed = ert.outward_ticket_store(constructed)
    assert failed["value"]["event"] == "ticket.persist.failed"
    assert failed["value"].get("emergency", {}).get("kind") == "ticket-persist-failed"
    assert "emergency:ticket-persist-failed" in failed["evidence"]
    # still has the original ticket; did not invent a second correlation
    assert failed["value"].get("ticket")
    # emergency path must not set exception.unhandled again
    assert failed["value"].get("event") != "exception.unhandled"


def test_ack_requires_real_external_id(tmp_path):
    ert, _ = _load_runtime(tmp_path)
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
    opened = ert.outward_ticket_store(ert.construct_ticket(thing))
    pending = ert.ack_ticket(opened)
    assert pending["value"]["ticket"].get("acked") is False
    assert pending["value"]["event"] == "ticket.ack_pending"
    # empty string not enough
    empty = {
        **opened,
        "value": {**opened["value"], "ticket_external_id": "  "},
    }
    still = ert.ack_ticket(empty)
    assert still["value"]["ticket"].get("acked") is False
    with_id = {
        **opened,
        "value": {**opened["value"], "ticket_external_id": "EXT-1"},
    }
    acked = ert.ack_ticket(with_id)
    assert acked["value"]["ticket"]["acked"] is True
    assert acked["value"]["ticket"]["external_id"] == "EXT-1"


def test_reload_unacked_on_restart(tmp_path):
    ert, _ = _load_runtime(tmp_path)
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
    persisted = ert.outward_ticket_store(ert.construct_ticket(thing))
    reloaded = ert.reload_unacked_tickets(
        {
            "value": {"ticket_outbox": str(outbox)},
            "depths": (),
            "axes": (),
            "evidence": (),
            "state": "formed",
        }
    )
    assert len(reloaded["value"]["unacked_tickets"]) == 1
    assert (
        reloaded["value"]["unacked_tickets"][0]["correlation_id"]
        == persisted["value"]["ticket"]["correlation_id"]
    )
    # after ack, reload returns empty
    acked = ert.ack_ticket(
        {
            **persisted,
            "value": {
                **persisted["value"],
                "ticket_external_id": "EXT-9",
                "ticket_outbox": str(outbox),
            },
        }
    )
    assert acked["value"]["ticket"]["acked"] is True
    reloaded2 = ert.reload_unacked_tickets(
        {
            "value": {"ticket_outbox": str(outbox)},
            "depths": (),
            "axes": (),
            "evidence": (),
            "state": "formed",
        }
    )
    assert reloaded2["value"]["unacked_tickets"] == []


def test_full_ticket_chain_via_routes(tmp_path):
    ert, root = _load_runtime(tmp_path)
    outbox = tmp_path / "chain"
    sys.path.insert(0, str(root))
    compose = importlib.import_module("uc_text_stats_v2.compose")

    def boom(thing):
        raise RuntimeError("token=xyz")

    out = ert.call_part(
        {
            "value": {"ticket_outbox": str(outbox)},
            "depths": (),
            "axes": (),
            "evidence": (),
            "state": "formed",
        },
        boom,
        "step.next",
    )
    assert out["value"]["event"] == "exception.unhandled"
    # drive ticket routes manually
    routes = {
        "exception.unhandled": ert.construct_ticket,
        "ticket.persist.requested": ert.outward_ticket_store,
        "ticket.persisted": ert.fail_with_ticket,
        "ticket.persist.failed": ert.emergency_persist_result,
        "processing.failed": lambda t: t,
    }
    final = ert.until_quiet(out, routes, max_steps=20)
    assert final["value"].get("ticket")
    assert final["value"]["ticket"]["message"] == "[redacted-message]"
    assert list(outbox.glob("*.json"))
    assert "event:processing.failed" in final["evidence"] or final["value"].get(
        "event"
    ) in {"processing.failed", "ticket.persisted", "quiet"}

    # normal path still works; validation does not ticket
    sample = tmp_path / "ok.txt"
    sample.write_text("hi", encoding="utf-8")
    ok = compose.program({"source": str(sample)})
    assert ok["state"] == "valid"
    bad = compose.program({"source": str(tmp_path / "missing-file-xyz")})
    assert bad["state"] != "valid"
    assert not (bad.get("value") or {}).get("ticket")


def test_domain_parts_and_compose_have_zero_explicit_cf(tmp_path):
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
    forbidden = (
        ast.If,
        ast.For,
        ast.While,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
        ast.Try,
    )
    for name in ("parts.py", "compose.py"):
        tree = ast.parse((pkg / name).read_text(encoding="utf-8"))
        hits = [type(n).__name__ for n in ast.walk(tree) if isinstance(n, forbidden)]
        assert hits == [], f"{name} has control flow: {hits}"
    # compose must use split ticket chain
    compose_src = (pkg / "compose.py").read_text(encoding="utf-8")
    assert "construct_ticket" in compose_src
    assert "outward_ticket_store" in compose_src
    assert "ticket.persist.requested" in compose_src


def test_runtime_has_no_hardcoded_domain_field_names():
    """Kernel source must not embed domain vocabulary like text/stats/invoice."""
    src = emit_event_runtime_module()
    # strip strings that are generic errors / contracts
    banned = (
        "missing-text",
        "invalid-text",
        "calculate_stats",
        "invoice",
        "subtotal",
        "unique_words",
        "read_text_source",
    )
    for word in banned:
        assert word not in src, f"domain vocabulary {word!r} in event_runtime"
