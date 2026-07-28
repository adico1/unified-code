"""Event-flow, cache-identity, mutation, and five-second budget proofs."""

from __future__ import annotations

import copy
import json
import sys

from unified.boundary import inward
from unified.generator.cli import _parse_argv
from unified.verify_flow import (
    FLOW_EVENTS,
    audited_graph_report_primitive,
    audited_scheduler_primitive,
    audited_source_report_primitive,
    verify_all,
)


def mini_graph():
    return {
        "format_version": "UC-VERIFY-FLOW-1",
        "budget_seconds": 5.0,
        "scheduler": "parallel-release",
        "release_policy": "dependency",
        "cache_policy": "content-addressed-verified",
        "failure_policy": "propagate",
        "timeout_policy": "fail",
        "terminal_event": "verification.completed",
        "failure_events": [
            "proof.failed",
            "timeout.reached",
            "identity.stale",
            "worker.missing",
            "evidence.incomplete",
            "budget.exceeded",
        ],
        "routes": {
            "verification.requested": "authority.discover",
            "authority.discovered": "identity.resolve",
            "identities.resolved": "proof_graph.form",
            "proof_graph.formed": "prerequisite.materialize",
            "prerequisites.materialized": "proof.release",
            "proof_nodes.released": "command",
            "proof_nodes.executed": "evidence.collect",
            "evidence.collected": "identity.compare",
            "identities.compared": "budget.measure",
            "budget.measured": "verification.complete",
            "verification.completed": "terminal",
        },
        "events": list(FLOW_EVENTS),
        "bootstrap_nodes": [
            {
                "id": "proof",
                "handler": "command",
                "requires": [],
                "argv": ["{python}", "-c", "print('proof')"],
            }
        ],
        "proof_nodes": [{"id": "proof", "requires": ["proof"]}],
    }


def request():
    return inward({"command": "verify-all"})


def test_cold_and_warm_flow_finish_inside_post_bootstrap_budget(tmp_path):
    graph = mini_graph()
    cold = audited_scheduler_primitive(request(), graph, tmp_path)
    warm = audited_scheduler_primitive(request(), graph, tmp_path)
    assert cold["state"] == warm["state"] == "valid"
    assert cold["value"]["cache"] == "cold"
    assert warm["value"]["cache"] == "warm"
    assert cold["value"]["verification_seconds"] <= 5.0
    assert warm["value"]["verification_seconds"] <= 5.0
    assert cold["value"]["structure_hash"] == warm["value"]["structure_hash"]
    assert cold["value"]["proofs_passed"] == warm["value"]["proofs_passed"] == 1
    assert cold["value"]["events"] == warm["value"]["events"] == list(FLOW_EVENTS)


def test_flow_source_confines_every_control_node_to_audited_primitives():
    source = __import__("pathlib").Path(
        __import__("unified.verify_flow").verify_flow.__file__
    ).read_text()
    report = audited_source_report_primitive(source)
    assert report["ok"]
    assert report["explicit_conditional_nodes"] == 0
    assert report["explicit_loop_nodes"] == 0
    assert report["hidden_dispatch_nodes"] == 0
    assert report["polling_nodes"] == 0
    assert report["audited_primitive_control_flow_count"] > 0
    assert verify_all.__code__.co_argcount == 1


def test_structural_mutations_are_all_detected():
    valid = "def flow(thing):\n    return route(thing)\n"
    assert audited_source_report_primitive(valid)["ok"]
    assert not audited_source_report_primitive(
        valid + "def bad(x):\n    if x:\n        return x\n"
    )["ok"]
    assert not audited_source_report_primitive(
        valid + "def bad(xs):\n    for x in xs:\n        emit(x)\n"
    )["ok"]
    assert not audited_source_report_primitive(
        valid + "def bad(xs):\n    return [emit(x) for x in xs]\n"
    )["ok"]
    assert not audited_source_report_primitive(
        valid + "def bad(x):\n    return x and emit(x)\n"
    )["ok"]
    assert not audited_source_report_primitive(
        valid + "def bad(x):\n    return emit(x) if x else reject(x)\n"
    )["ok"]
    assert not audited_source_report_primitive(
        valid + "def bad(x):\n    try:\n        return emit(x)\n    except ValueError:\n        return x\n"
    )["ok"]
    assert not audited_source_report_primitive(
        valid + "def bad():\n    time.sleep(0.01)\n"
    )["ok"]


def test_graph_routing_mutations_are_all_detected():
    graph = mini_graph()
    assert audited_graph_report_primitive(graph)["ok"]
    duplicate = copy.deepcopy(graph)
    duplicate["bootstrap_nodes"].append(copy.deepcopy(duplicate["bootstrap_nodes"][0]))
    assert not audited_graph_report_primitive(duplicate)["ok"]
    missing = copy.deepcopy(graph)
    missing["events"].pop()
    assert not audited_graph_report_primitive(missing)["ok"]
    reordered = copy.deepcopy(graph)
    reordered["events"].reverse()
    assert not audited_graph_report_primitive(reordered)["ok"]
    handler = copy.deepcopy(graph)
    handler["bootstrap_nodes"][0]["handler"] = "unknown"
    assert not audited_graph_report_primitive(handler)["ok"]
    dependency = copy.deepcopy(graph)
    dependency["proof_nodes"][0]["requires"] = ["missing"]
    assert not audited_graph_report_primitive(dependency)["ok"]
    sequential = copy.deepcopy(graph)
    sequential["scheduler"] = "sequential"
    assert not audited_graph_report_primitive(sequential)["ok"]
    premature = copy.deepcopy(graph)
    premature["terminal_event"] = "proof_nodes.executed"
    assert not audited_graph_report_primitive(premature)["ok"]
    suppressed = copy.deepcopy(graph)
    suppressed["failure_policy"] = "ignore"
    assert not audited_graph_report_primitive(suppressed)["ok"]
    timeout = copy.deepcopy(graph)
    timeout["timeout_policy"] = "ignore"
    assert not audited_graph_report_primitive(timeout)["ok"]
    cache = copy.deepcopy(graph)
    cache["cache_policy"] = "trust"
    assert not audited_graph_report_primitive(cache)["ok"]


def test_unverified_cache_reuse_is_rejected(tmp_path):
    graph = mini_graph()
    cold = audited_scheduler_primitive(request(), graph, tmp_path)
    assert cold["state"] == "valid"
    evidence_path = next(tmp_path.rglob("bootstrap-evidence.json"))
    evidence = json.loads(evidence_path.read_text())
    evidence["results"][0]["returncode"] = 1
    evidence_path.write_text(json.dumps(evidence))
    rejected = audited_scheduler_primitive(request(), graph, tmp_path)
    assert rejected["state"] == "invalid"
    assert rejected["value"]["error"] == "identity.stale"
    assert "identity.stale" in rejected["evidence"]


def test_cli_contract_is_one_canonical_operation():
    assert _parse_argv(["verify-all"]) == {"command": "verify-all"}
    assert _parse_argv(["verify-all", "extra"]) == {
        "command": "verify-all",
        "error": "usage-verify-all",
    }
