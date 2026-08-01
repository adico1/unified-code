"""Timing-boundary, proof-bundle, cache, mutation, and FLOW proofs."""

from __future__ import annotations

import copy
import contextlib
import json
import os
import threading
import time
from pathlib import Path

import unified.verify_flow as flow
from unified.boundary import inward
from unified.generator.cli import _parse_argv
from unified.verify_flow import (
    FAILURE_EVENTS,
    FLOW_EVENTS,
    GENERIC_BOOTLOAD,
    VERIFICATION_ACTIVITIES,
    audited_bundle_identity_primitive,
    audited_bundle_report_primitive,
    audited_graph_report_primitive,
    audited_repository_identity_primitive,
    audited_scheduler_primitive,
    audited_source_report_primitive,
    audited_timing_boundary_report_primitive,
    verify_all,
)


def mini_graph():
    return {
        "format_version": "UC-VERIFY-FLOW-2",
        "budget_seconds": 5.0,
        "scheduler": "parallel-release",
        "release_policy": "dependency",
        "cache_policy": "content-addressed-verified",
        "failure_policy": "propagate",
        "timeout_policy": "fail",
        "terminal_event": "verification.completed",
        "failure_events": list(FAILURE_EVENTS),
        "routes": {
            "verification.requested": "tools.boot.request",
            "tools.boot.requested": "tools.boot.complete",
            "tools.boot.completed": "verification.clock.start",
            "verification.clock.started": "authority.resolve",
            "authorities.resolved": "proof_graph.release",
            "proof_graph.released": "proof.complete",
            "proof.completed": "evidence.complete",
            "evidence.completed": "verification.clock.stop",
            "verification.clock.stopped": "budget.measure",
            "budget.measured": "verification.complete",
            "verification.completed": "terminal",
        },
        "events": list(FLOW_EVENTS),
        "bootload_activities": list(GENERIC_BOOTLOAD),
        "verification_activities": list(VERIFICATION_ACTIVITIES),
        "bundle_path": "seed/verification/PROOF_BUNDLE.json",
        "evidence_nodes": [
            {
                "id": "physical",
                "handler": "command",
                "requires": [],
                "argv": ["{python}", "-c", "print('proof')"],
            }
        ],
        "proof_nodes": [
            {"id": f"proof-{index:02d}", "requires": ["physical"]}
            for index in range(24)
        ],
    }


def request():
    return inward({"command": "verify-all"})


def materialize(monkeypatch, tmp_path, graph):
    source = tmp_path / "source"
    source.mkdir(exist_ok=True)
    monkeypatch.setattr(flow, "ROOT", source)
    monkeypatch.setattr(flow, "BUNDLE", tmp_path / "PROOF_BUNDLE.json")
    monkeypatch.setattr(
        flow,
        "audited_repository_identity_primitive",
        lambda _root: {"identity": "test-authority", "file_count": 0, "files": {}},
    )
    monkeypatch.setenv("UC_VERIFY_MATERIALIZE", "1")
    result = audited_scheduler_primitive(
        request(),
        graph,
        tmp_path / "materialization-cache",
    )
    monkeypatch.delenv("UC_VERIFY_MATERIALIZE")
    return result


def test_empty_and_valid_cache_measure_complete_verification(monkeypatch, tmp_path):
    graph = mini_graph()
    produced = materialize(monkeypatch, tmp_path, graph)
    cache = tmp_path / "acceptance-cache"
    cold = audited_scheduler_primitive(request(), graph, cache)
    warm = audited_scheduler_primitive(request(), graph, cache)
    assert produced["state"] == cold["state"] == warm["state"] == "valid", (
        produced,
        cold,
        warm,
    )
    assert cold["value"]["cache"] == "cold"
    assert warm["value"]["cache"] == "warm"
    assert cold["value"]["verification_seconds"] <= 5.0
    assert warm["value"]["verification_seconds"] <= 5.0
    assert cold["value"]["bootstrap_repository_actions"] == 0
    assert cold["value"]["structure_hash"] == warm["value"]["structure_hash"]
    assert cold["value"]["proofs_passed"] == warm["value"]["proofs_passed"] == 24
    assert cold["value"]["events"] == warm["value"]["events"] == list(FLOW_EVENTS)


def test_flow_source_confines_every_control_node_to_audited_primitives():
    source = __import__("pathlib").Path(flow.__file__).read_text()
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
    mutations = (
        "def bad(x):\n    if x:\n        return x\n",
        "def bad(xs):\n    for x in xs:\n        emit(x)\n",
        "def bad(xs):\n    return [emit(x) for x in xs]\n",
        "def bad(x):\n    return x and emit(x)\n",
        "def bad(x):\n    return emit(x) if x else reject(x)\n",
        "def bad(x):\n    try:\n        return emit(x)\n    except ValueError:\n        return x\n",
        "def bad():\n    time.sleep(0.01)\n",
    )
    assert audited_source_report_primitive(valid)["ok"]
    assert all(
        not audited_source_report_primitive(valid + mutation)["ok"]
        for mutation in mutations
    )


def test_graph_routing_mutations_are_all_detected():
    graph = mini_graph()
    assert audited_graph_report_primitive(graph)["ok"]
    mutations = []
    duplicate = copy.deepcopy(graph)
    duplicate["evidence_nodes"].append(copy.deepcopy(duplicate["evidence_nodes"][0]))
    mutations.append(duplicate)
    missing = copy.deepcopy(graph)
    missing["events"].pop()
    mutations.append(missing)
    reordered = copy.deepcopy(graph)
    reordered["events"].reverse()
    mutations.append(reordered)
    handler = copy.deepcopy(graph)
    handler["evidence_nodes"][0]["handler"] = "unknown"
    mutations.append(handler)
    dependency = copy.deepcopy(graph)
    dependency["proof_nodes"][0]["requires"] = ["missing"]
    mutations.append(dependency)
    evidence_dependency = copy.deepcopy(graph)
    evidence_dependency["evidence_nodes"][0]["requires"] = ["missing"]
    mutations.append(evidence_dependency)
    cycle = copy.deepcopy(graph)
    cycle["evidence_nodes"].append(
        {
            "id": "cycle-a",
            "handler": "command",
            "requires": ["cycle-b"],
            "argv": ["{python}", "-c", "print('a')"],
        }
    )
    cycle["evidence_nodes"].append(
        {
            "id": "cycle-b",
            "handler": "command",
            "requires": ["cycle-a"],
            "argv": ["{python}", "-c", "print('b')"],
        }
    )
    mutations.append(cycle)
    sequential = copy.deepcopy(graph)
    sequential["scheduler"] = "sequential"
    mutations.append(sequential)
    premature = copy.deepcopy(graph)
    premature["terminal_event"] = "proof.completed"
    mutations.append(premature)
    suppressed = copy.deepcopy(graph)
    suppressed["failure_policy"] = "ignore"
    mutations.append(suppressed)
    timeout = copy.deepcopy(graph)
    timeout["timeout_policy"] = "ignore"
    mutations.append(timeout)
    cache = copy.deepcopy(graph)
    cache["cache_policy"] = "trust"
    mutations.append(cache)
    assert all(not audited_graph_report_primitive(item)["ok"] for item in mutations)


def test_every_repository_activity_is_rejected_from_bootload():
    graph = mini_graph()
    assert audited_timing_boundary_report_primitive(graph)["ok"]
    mutations = []
    for activity in VERIFICATION_ACTIVITIES:
        mutation = copy.deepcopy(graph)
        mutation["bootload_activities"].append(activity)
        mutations.append(mutation)
    assert len(mutations) == len(VERIFICATION_ACTIVITIES)
    assert all(
        not audited_timing_boundary_report_primitive(item)["ok"]
        for item in mutations
    )


def test_corrupt_stale_partial_and_wrong_platform_cache_fail_closed(
    monkeypatch,
    tmp_path,
):
    graph = mini_graph()
    assert materialize(monkeypatch, tmp_path, graph)["state"] == "valid"
    mutations = ("corrupt", "stale", "partial", "wrong-platform")
    errors = []
    for mutation in mutations:
        cache = tmp_path / mutation
        cold = audited_scheduler_primitive(request(), graph, cache)
        assert cold["state"] == "valid"
        evidence_path = next(cache.rglob("validated-evidence.json"))
        if mutation == "corrupt":
            evidence_path.write_text("{")
        elif mutation == "partial":
            evidence_path.unlink()
        else:
            evidence = json.loads(evidence_path.read_text())
            if mutation == "stale":
                evidence["structure_hash"] = "0" * 64
            else:
                evidence["consumer_toolchain"]["system"] = "wrong-platform"
            evidence_path.write_text(json.dumps(evidence))
        rejected = audited_scheduler_primitive(request(), graph, cache)
        assert rejected["state"] == "invalid"
        errors.append(rejected["value"]["error"])
    assert errors == [
        "cache.corrupt",
        "identity.stale",
        "cache.partial",
        "cache.wrong-platform",
    ]


def test_every_physical_and_logical_proof_mutation_is_detected(
    monkeypatch,
    tmp_path,
):
    graph = mini_graph()
    assert materialize(monkeypatch, tmp_path, graph)["state"] == "valid"
    bundle = json.loads(flow.BUNDLE.read_text())
    authority = flow.audited_repository_identity_primitive(
        Path(os.environ.get("UC_VERIFY_AUTHORITY_ROOT", flow.ROOT))
    )
    mutations = []
    for index in range(len(bundle["results"])):
        mutation = copy.deepcopy(bundle)
        mutation["results"][index]["returncode"] = 1
        mutation["bundle_identity"] = audited_bundle_identity_primitive(mutation)
        mutations.append(mutation)
    for index in range(len(bundle["verdicts"])):
        mutation = copy.deepcopy(bundle)
        mutation["verdicts"][index]["status"] = "fail"
        mutation["bundle_identity"] = audited_bundle_identity_primitive(mutation)
        mutations.append(mutation)
    worker_mutation = copy.deepcopy(bundle)
    worker_mutation["evidence_workers"] += 1
    worker_mutation["bundle_identity"] = audited_bundle_identity_primitive(
        worker_mutation
    )
    mutations.append(worker_mutation)
    assert len(mutations) == (
        len(graph["evidence_nodes"]) + len(graph["proof_nodes"]) + 1
    )
    assert all(
        not audited_bundle_report_primitive(item, graph, authority)["ok"]
        for item in mutations
    )


def test_bootload_precedes_verification_clock_without_repository_work(
    monkeypatch,
    tmp_path,
):
    graph = mini_graph()
    assert materialize(monkeypatch, tmp_path, graph)["state"] == "valid"
    started = time.monotonic_ns()
    verification = time.monotonic_ns()
    result = audited_scheduler_primitive(
        request(),
        graph,
        tmp_path / "clock-cache",
        verification,
        (verification - started) / 1_000_000_000,
    )
    assert result["state"] == "valid"
    assert result["value"]["bootload_seconds"] >= 0
    assert result["value"]["bootstrap_repository_actions"] == 0


def test_cli_contract_is_one_canonical_operation():
    assert _parse_argv(["verify-all"]) == {"command": "verify-all"}
    assert _parse_argv(["verify-all", "extra"]) == {
        "command": "verify-all",
        "error": "usage-verify-all",
    }


def test_physical_evidence_releases_dependency_levels_concurrently(
    monkeypatch,
    tmp_path,
):
    released = []
    first_level = threading.Barrier(2)

    def record(node):
        if node["id"].startswith("first-"):
            first_level.wait(timeout=1)
        released.append(node["id"])
        return {"id": node["id"], "returncode": 0}

    graph = mini_graph()
    graph["evidence_nodes"] = [
        {"id": "first-a", "handler": "record", "requires": []},
        {"id": "first-b", "handler": "record", "requires": []},
        {
            "id": "second",
            "handler": "record",
            "requires": ["first-a", "first-b"],
        },
    ]
    graph["proof_nodes"] = [
        {"id": f"proof-{index:02d}", "requires": ["second"]}
        for index in range(24)
    ]
    monkeypatch.setitem(flow.HANDLER_REGISTRY, "record", record)
    monkeypatch.setattr(flow, "BUNDLE", tmp_path / "bundle.json")
    bundle = flow.audited_materialize_bundle_primitive(
        graph,
        {"identity": "authority", "file_count": 0},
    )
    assert set(released[:2]) == {"first-a", "first-b"}
    assert released[-1] == "second"
    assert bundle["evidence_workers"] == 2


def test_command_node_confines_temporary_storage_to_owned_boundary(
    monkeypatch,
    tmp_path,
):
    owned = tmp_path / "owned"

    @contextlib.contextmanager
    def owned_temporary_directory(prefix):
        del prefix
        owned.mkdir()
        try:
            yield str(owned)
        finally:
            import shutil

            shutil.rmtree(owned)

    monkeypatch.setattr(
        flow.tempfile,
        "TemporaryDirectory",
        owned_temporary_directory,
    )
    source = tmp_path / "source"
    source.mkdir()
    monkeypatch.setattr(flow, "ROOT", source)
    monkeypatch.setattr(
        flow,
        "audited_repository_identity_primitive",
        lambda _root: {"identity": "test-authority", "file_count": 0, "files": {}},
    )
    result = flow.audited_command_node_primitive(
        {
            "id": "storage",
            "handler": "command",
            "requires": [],
            "argv": [
                "{python}",
                "-c",
                "import os,tempfile; assert tempfile.gettempdir()==os.environ['TMPDIR']",
            ],
        }
    )
    assert result["returncode"] == 0
    assert result["authority_preserved"]
    assert not owned.exists()


def test_command_node_isolates_repository_writes_from_authority(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        flow,
        "audited_repository_identity_primitive",
        lambda _root: {"identity": "test-authority", "file_count": 0, "files": {}},
    )
    source = tmp_path / "source"
    source.mkdir()
    monkeypatch.setattr(flow, "ROOT", source)
    result = flow.audited_command_node_primitive(
        {
            "id": "no-clone",
            "handler": "command",
            "requires": [],
            "argv": [
                "{python}",
                "-c",
                "from pathlib import Path; Path('isolated.txt').write_text('proof')",
            ],
        }
    )
    assert result["returncode"] == 0
    assert result["authority_preserved"]
    assert result["failure_summary"] is None
    assert not (source / "isolated.txt").exists()


def test_failed_command_retains_bounded_path_redacted_diagnostics(
    monkeypatch,
    tmp_path,
):
    source = tmp_path / "source"
    source.mkdir()
    monkeypatch.setattr(flow, "ROOT", source)
    monkeypatch.setattr(
        flow,
        "audited_repository_identity_primitive",
        lambda _root: {"identity": "test-authority", "file_count": 0, "files": {}},
    )
    result = flow.audited_command_node_primitive(
        {
            "id": "diagnostic",
            "handler": "command",
            "requires": [],
            "argv": [
                "{python}",
                "-c",
                "import pathlib,sys; print(pathlib.Path.cwd(),file=sys.stderr); sys.exit(7)",
            ],
        }
    )
    assert result["returncode"] == 7
    assert "{temporary}/repository" in result["failure_summary"]
    assert len(result["failure_summary"]) <= 2048
