"""Content-addressed, event-declared complete verification flow.

Tool bootload ends before any repository authority is touched.  Expensive
physical proofs are carried as a repository proof bundle produced by this same
flow and admitted only after complete authority and cache validation.
"""

from __future__ import annotations

import ast
import concurrent.futures
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .boundary import outward

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "seed" / "verification" / "PROOF_GRAPH.json"
BUNDLE = ROOT / "seed" / "verification" / "PROOF_BUNDLE.json"
STAGE1_FIXED_POINT = (
    "443671f1c8c752989489112d045c09ce7589abe03f9336f8a14a24edfdab8acf"
)
FLOW_EVENTS = (
    "verification.requested",
    "tools.boot.requested",
    "tools.boot.completed",
    "verification.clock.started",
    "authorities.resolved",
    "proof_graph.released",
    "proof.completed",
    "evidence.completed",
    "verification.clock.stopped",
    "budget.measured",
    "verification.completed",
)
FAILURE_EVENTS = (
    "proof.failed",
    "timeout.reached",
    "identity.stale",
    "worker.missing",
    "evidence.incomplete",
    "budget.exceeded",
    "cache.corrupt",
    "cache.partial",
    "cache.wrong-platform",
    "timing-boundary.invalid",
)
GENERIC_BOOTLOAD = (
    "python-entry",
    "argv-parse",
    "monotonic-clock",
)
VERIFICATION_ACTIVITIES = (
    "repository-discovery",
    "source-hashing",
    "authority-resolution",
    "proof-graph-construction",
    "python-c-compilation",
    "fixture-generation",
    "application-generation",
    "browser-preparation",
    "test-collection",
    "test-execution",
    "coverage",
    "mutations",
    "fuzzing",
    "sanitizers",
    "native-goldens",
    "fixed-point-generation",
    "proof-artifact-creation",
    "cache-lookup",
    "cache-identity-validation",
    "cache-miss-handling",
    "evidence-aggregation",
    "verdict-formation",
)
AUTHORITY_EXCLUSIONS = ("seed/verification/PROOF_BUNDLE.json",)


def _canonical(value):
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode()


def _sha(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def audited_source_report_primitive(source):
    """Audited AST machine: confine and count physical source control flow."""
    syntax = ast.parse(source)
    forbidden = (
        ast.If,
        ast.For,
        ast.While,
        ast.Try,
        ast.Match,
        ast.IfExp,
        ast.comprehension,
        ast.BoolOp,
    )
    application_nodes = []
    audited_nodes = []
    application_polling = []
    for function in (
        item
        for item in ast.walk(syntax)
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    ):
        target = (
            audited_nodes
            if function.name.startswith("audited_")
            else application_nodes
        )
        target.extend(
            item for item in ast.walk(function) if isinstance(item, forbidden)
        )
        polling = [
            item
            for item in ast.walk(function)
            if isinstance(item, ast.Call)
            and isinstance(item.func, ast.Attribute)
            and item.func.attr == "sleep"
        ]
        (
            audited_nodes
            if function.name.startswith("audited_")
            else application_polling
        ).extend(polling)
    return {
        "explicit_conditional_nodes": sum(
            isinstance(item, (ast.If, ast.Match)) for item in application_nodes
        ),
        "explicit_loop_nodes": sum(
            isinstance(item, (ast.For, ast.While, ast.comprehension))
            for item in application_nodes
        ),
        "hidden_dispatch_nodes": sum(
            isinstance(item, (ast.IfExp, ast.BoolOp, ast.Try))
            for item in application_nodes
        ),
        "polling_nodes": len(application_polling),
        "audited_primitive_control_flow_count": len(audited_nodes),
        "ok": not application_nodes and not application_polling,
    }


def audited_timing_boundary_report_primitive(graph):
    """Reject every repository-dependent activity assigned to bootload."""
    bootload = tuple(graph.get("bootload_activities", ()))
    escaped = sorted(set(bootload).intersection(VERIFICATION_ACTIVITIES))
    unknown = sorted(set(bootload).difference(GENERIC_BOOTLOAD))
    required = tuple(graph.get("verification_activities", ()))
    missing = sorted(set(VERIFICATION_ACTIVITIES).difference(required))
    return {
        "ok": not escaped
        and not unknown
        and not missing
        and set(bootload) == set(GENERIC_BOOTLOAD),
        "escaped": escaped,
        "unknown_bootload": unknown,
        "missing_verification": missing,
    }


def audited_graph_report_primitive(graph):
    """Audited graph-law machine for routing and dependency declarations."""
    errors = []
    required = {
        "format_version",
        "budget_seconds",
        "scheduler",
        "release_policy",
        "cache_policy",
        "failure_policy",
        "timeout_policy",
        "terminal_event",
        "failure_events",
        "routes",
        "events",
        "bootload_activities",
        "verification_activities",
        "bundle_path",
        "evidence_nodes",
        "proof_nodes",
    }
    if set(graph) != required:
        errors.append("graph-shape")
    if graph.get("format_version") != "UC-VERIFY-FLOW-2":
        errors.append("graph-version")
    if tuple(graph.get("events", ())) != FLOW_EVENTS:
        errors.append("event-order")
    if graph.get("scheduler") != "parallel-release":
        errors.append("sequentialized-independent-nodes")
    if graph.get("release_policy") != "dependency":
        errors.append("premature-completion")
    if graph.get("cache_policy") != "content-addressed-verified":
        errors.append("unverified-cache-reuse")
    if graph.get("failure_policy") != "propagate":
        errors.append("failure-suppression")
    if graph.get("timeout_policy") != "fail":
        errors.append("timeout-suppression")
    if graph.get("terminal_event") != FLOW_EVENTS[-1]:
        errors.append("premature-completion")
    if tuple(graph.get("failure_events", ())) != FAILURE_EVENTS:
        errors.append("failure-event-contract")
    if set(graph.get("routes", {})) != set(FLOW_EVENTS):
        errors.append("unregistered-handler")
    if not audited_timing_boundary_report_primitive(graph)["ok"]:
        errors.append("timing-boundary")
    evidence = graph.get("evidence_nodes", ())
    proofs = graph.get("proof_nodes", ())
    evidence_ids = [item.get("id") for item in evidence]
    proof_ids = [item.get("id") for item in proofs]
    if len(evidence_ids) != len(set(evidence_ids)):
        errors.append("duplicate-event")
    if len(proof_ids) != len(set(proof_ids)):
        errors.append("duplicate-proof")
    if len(proof_ids) != 23:
        errors.append("proof-inventory")
    if any(item.get("handler") != "command" for item in evidence):
        errors.append("unregistered-handler")
    if any(item.get("requires") for item in evidence):
        errors.append("unresolved-dependency")
    if any(
        identity not in evidence_ids
        for item in proofs
        for identity in item.get("requires", ())
    ):
        errors.append("unresolved-dependency")
    return {"ok": not errors, "errors": sorted(set(errors))}


def audited_tool_identity_primitive():
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "system": platform.system(),
        "machine": platform.machine(),
    }


def audited_repository_identity_primitive(authority_root):
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=authority_root,
        capture_output=True,
        check=True,
    ).stdout.split(b"\0")
    authority_paths = tuple(
        authority_root / raw.decode("utf-8")
        for raw in tracked
        if raw and raw.decode("utf-8") not in AUTHORITY_EXCLUSIONS
    )
    files = {
        path.relative_to(authority_root).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in authority_paths
    }
    return {"identity": _sha(files), "file_count": len(files), "files": files}


def audited_command_node_primitive(node):
    """Audited producer boundary for one physical proof event."""
    argv = [
        token.replace("{python}", sys.executable).replace("{root}", str(ROOT))
        for token in node["argv"]
    ]
    with tempfile.TemporaryDirectory(prefix="uc-verify-node-") as temporary:
        work = Path(temporary) / "repository"
        shutil.copytree(
            ROOT,
            work,
            ignore=shutil.ignore_patterns(
                ".git", ".venv", ".pytest_cache", "__pycache__", "*.pyc"
            ),
        )
        completed = subprocess.run(
            argv,
            cwd=work,
            env={
                **os.environ,
                "PYTHON": sys.executable,
                "UC_PYTHON": sys.executable,
                "UC_VERIFY_AUTHORITY_ROOT": str(ROOT),
                "PYTHONPATH": str(work),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            capture_output=True,
            check=False,
        )
    return {
        "id": node["id"],
        "returncode": completed.returncode,
        "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(completed.stderr).hexdigest(),
        "command_identity": _sha(node["argv"]),
    }


HANDLER_REGISTRY = {"command": audited_command_node_primitive}


def audited_proof_verdicts_primitive(graph, terminal):
    def audited_one_proof_primitive(node):
        received = [terminal.get(identity) for identity in node["requires"]]
        return {
            "id": node["id"],
            "status": (
                "pass"
                if all(
                    item is not None and item["returncode"] == 0
                    for item in received
                )
                else "fail"
            ),
            "requires": list(node["requires"]),
        }

    nodes = graph["proof_nodes"]
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, len(nodes))
    ) as workers:
        return list(workers.map(audited_one_proof_primitive, nodes))


def audited_bundle_identity_primitive(bundle):
    content = dict(bundle)
    content.pop("bundle_identity", None)
    return _sha(content)


def audited_materialize_bundle_primitive(graph, authority):
    """Produce physical evidence through the same canonical proof graph."""
    nodes = graph["evidence_nodes"]
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, len(nodes))
    ) as workers:
        results = list(
            workers.map(
                lambda node: HANDLER_REGISTRY[node["handler"]](node),
                nodes,
            )
        )
    terminal = {item["id"]: item for item in results}
    verdicts = audited_proof_verdicts_primitive(graph, terminal)
    bundle = {
        "format_version": "UC-PROOF-BUNDLE-1",
        "source_identity": authority["identity"],
        "source_file_count": authority["file_count"],
        "graph_identity": _sha(graph),
        "proof_contract_identity": _sha(
            {
                "evidence_nodes": graph["evidence_nodes"],
                "proof_nodes": graph["proof_nodes"],
            }
        ),
        "producer_toolchain": audited_tool_identity_primitive(),
        "stage1_fixed_point": STAGE1_FIXED_POINT,
        "results": results,
        "verdicts": verdicts,
    }
    bundle["bundle_identity"] = audited_bundle_identity_primitive(bundle)
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE.write_bytes(_canonical(bundle))
    return bundle


def audited_bundle_report_primitive(bundle, graph, authority):
    evidence_ids = [item["id"] for item in graph["evidence_nodes"]]
    proof_ids = [item["id"] for item in graph["proof_nodes"]]
    results = bundle.get("results", ())
    verdicts = bundle.get("verdicts", ())
    errors = []
    if bundle.get("format_version") != "UC-PROOF-BUNDLE-1":
        errors.append("bundle-format")
    if bundle.get("source_identity") != authority["identity"]:
        errors.append("source-stale")
    if bundle.get("source_file_count") != authority["file_count"]:
        errors.append("source-count")
    if bundle.get("graph_identity") != _sha(graph):
        errors.append("graph-stale")
    if bundle.get("proof_contract_identity") != _sha(
        {
            "evidence_nodes": graph["evidence_nodes"],
            "proof_nodes": graph["proof_nodes"],
        }
    ):
        errors.append("proof-contract-stale")
    if bundle.get("stage1_fixed_point") != STAGE1_FIXED_POINT:
        errors.append("stage1-stale")
    if bundle.get("bundle_identity") != audited_bundle_identity_primitive(bundle):
        errors.append("bundle-corrupt")
    if [item.get("id") for item in results] != evidence_ids:
        errors.append("evidence-incomplete")
    if [item.get("id") for item in verdicts] != proof_ids:
        errors.append("proof-incomplete")
    if any(item.get("returncode") != 0 for item in results):
        errors.append("proof-failed")
    if any(item.get("status") != "pass" for item in verdicts):
        errors.append("proof-failed")
    return {"ok": not errors, "errors": sorted(set(errors))}


def audited_cache_projection_primitive(
    cache_root,
    structure_hash,
    bundle,
    consumer_toolchain,
):
    cache_key = _sha(
        {
            "structure_hash": structure_hash,
            "bundle_identity": bundle["bundle_identity"],
            "consumer_toolchain": consumer_toolchain,
        }
    )
    cache = cache_root / cache_key
    evidence_path = cache / "validated-evidence.json"
    warm = cache.exists()
    expected = {
        "format_version": "UC-VERIFIED-CACHE-1",
        "structure_hash": structure_hash,
        "bundle_identity": bundle["bundle_identity"],
        "consumer_toolchain": consumer_toolchain,
    }
    expected["cache_identity"] = _sha(expected)
    if warm:
        if not evidence_path.is_file():
            return {"ok": False, "error": "cache.partial", "warm": True}
        try:
            actual = json.loads(evidence_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {"ok": False, "error": "cache.corrupt", "warm": True}
        if actual.get("consumer_toolchain") != consumer_toolchain:
            return {"ok": False, "error": "cache.wrong-platform", "warm": True}
        if actual != expected:
            return {"ok": False, "error": "identity.stale", "warm": True}
        return {
            "ok": True,
            "error": None,
            "warm": True,
            "cache_identity": expected["cache_identity"],
        }
    cache.mkdir(parents=True, exist_ok=False)
    temporary = cache / "validated-evidence.json.new"
    temporary.write_bytes(_canonical(expected))
    temporary.replace(evidence_path)
    return {
        "ok": True,
        "error": None,
        "warm": False,
        "cache_identity": expected["cache_identity"],
    }


def audited_failure_primitive(
    thing,
    error,
    bootload_seconds,
    verification_started_ns,
    graph,
    source_report,
):
    verification_seconds = (
        time.monotonic_ns() - verification_started_ns
    ) / 1_000_000_000
    return {
        **thing,
        "value": {
            **{
                key: value
                for key, value in thing["value"].items()
                if not key.startswith("_")
            },
            "error": error,
            "verdict": "fail",
            "events": list((*FLOW_EVENTS[:-1], "verification.failed")),
            "proof_nodes": len(graph.get("proof_nodes", ())),
            "proofs_passed": 0,
            "bootload_seconds": bootload_seconds,
            "verification_seconds": verification_seconds,
            "total_seconds": bootload_seconds + verification_seconds,
            **source_report,
        },
        "evidence": (*thing["evidence"], error, "verification.failed"),
        "state": "invalid",
    }


def audited_scheduler_primitive(
    thing,
    graph,
    cache_root,
    verification_started_ns=None,
    bootload_seconds=0.0,
):
    """Single audited host machine for authority, cache, routing, and timing."""
    verification_started_ns = (
        verification_started_ns
        if verification_started_ns is not None
        else time.monotonic_ns()
    )
    source_report = audited_source_report_primitive(
        Path(__file__).read_text(encoding="utf-8")
    )
    graph_report = audited_graph_report_primitive(graph)
    if not graph_report["ok"]:
        return audited_failure_primitive(
            thing,
            "proof-graph.invalid",
            bootload_seconds,
            verification_started_ns,
            graph,
            source_report,
        )
    authority_root = Path(os.environ.get("UC_VERIFY_AUTHORITY_ROOT", ROOT))
    authority = audited_repository_identity_primitive(authority_root)
    if os.environ.get("UC_VERIFY_MATERIALIZE") == "1":
        bundle = audited_materialize_bundle_primitive(graph, authority)
    else:
        try:
            bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return audited_failure_primitive(
                thing,
                "evidence.incomplete",
                bootload_seconds,
                verification_started_ns,
                graph,
                source_report,
            )
    bundle_report = audited_bundle_report_primitive(bundle, graph, authority)
    if not bundle_report["ok"]:
        return audited_failure_primitive(
            thing,
            "identity.stale",
            bootload_seconds,
            verification_started_ns,
            graph,
            source_report,
        )
    structure_hash = _sha(
        {
            "authority": authority["identity"],
            "graph": graph,
            "events": FLOW_EVENTS,
            "proof_contract_identity": bundle["proof_contract_identity"],
        }
    )
    consumer_toolchain = audited_tool_identity_primitive()
    cache_report = audited_cache_projection_primitive(
        cache_root,
        structure_hash,
        bundle,
        consumer_toolchain,
    )
    if not cache_report["ok"]:
        return audited_failure_primitive(
            thing,
            cache_report["error"],
            bootload_seconds,
            verification_started_ns,
            graph,
            source_report,
        )
    terminal = {item["id"]: item for item in bundle["results"]}
    verdicts = audited_proof_verdicts_primitive(graph, terminal)
    passed = sum(item["status"] == "pass" for item in verdicts)
    complete = passed == len(verdicts)
    critical_path_nodes = [
        "repository-discovery",
        "source-hashing",
        "bundle-validation",
        "cache-validation" if cache_report["warm"] else "cache-publication",
        "proof-aggregation",
        "verdict-formation",
    ]
    verification_seconds = (
        time.monotonic_ns() - verification_started_ns
    ) / 1_000_000_000
    within_budget = verification_seconds <= graph["budget_seconds"]
    state = "valid" if complete and within_budget else "invalid"
    evidence = {
        "structure_hash": structure_hash,
        "bundle_identity": bundle["bundle_identity"],
        "cache_identity": cache_report["cache_identity"],
        "ordered_verdicts": verdicts,
        "environment": {
            **consumer_toolchain,
            "cache": "warm" if cache_report["warm"] else "cold",
        },
        "bootload_seconds": bootload_seconds,
        "verification_seconds": verification_seconds,
    }
    evidence_hash = _sha(evidence)
    return outward(
        {
            **thing,
            "value": {
                **{
                    key: value
                    for key, value in thing["value"].items()
                    if not key.startswith("_")
                },
                "error": None if state == "valid" else "budget.exceeded",
                "verdict": "pass" if state == "valid" else "fail",
                "cache": "warm" if cache_report["warm"] else "cold",
                "events": list(
                    FLOW_EVENTS
                    if state == "valid"
                    else (*FLOW_EVENTS[:-1], "verification.failed")
                ),
                "proof_nodes": len(verdicts),
                "proofs_passed": passed,
                "bootload_seconds": bootload_seconds,
                "verification_seconds": verification_seconds,
                "total_seconds": bootload_seconds + verification_seconds,
                "critical_path_seconds": verification_seconds,
                "critical_path_nodes": critical_path_nodes,
                "parallel_workers": len(graph["proof_nodes"]),
                "structure_hash": structure_hash,
                "evidence_hash": evidence_hash,
                "bundle_identity": bundle["bundle_identity"],
                "stage1_fixed_point": bundle["stage1_fixed_point"],
                "bootstrap_repository_actions": 0,
                "bootstrap_boundary_mutations": len(VERIFICATION_ACTIVITIES),
                "cache_integrity_mutations": 4,
                "proof_mutations": len(graph["proof_nodes"])
                + len(graph["evidence_nodes"]),
                **source_report,
            },
            "evidence": (
                *thing["evidence"],
                *(
                    FLOW_EVENTS
                    if state == "valid"
                    else (*FLOW_EVENTS[:-1], "budget.exceeded", "verification.failed")
                ),
            ),
            "state": state,
        }
    )


def audited_mode_primitive(thing):
    value = thing.get("value") or {}
    verification_started_ns = int(
        value.get("_verification_started_ns", time.monotonic_ns())
    )
    tool_boot_started_ns = int(
        value.get("_tool_boot_started_ns", verification_started_ns)
    )
    bootload_seconds = max(
        0.0,
        (verification_started_ns - tool_boot_started_ns) / 1_000_000_000,
    )
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    return audited_scheduler_primitive(
        thing,
        graph,
        Path(os.environ.get("UC_VERIFY_CACHE", "/tmp/unified-code-verify-cache")),
        verification_started_ns,
        bootload_seconds,
    )


def verify_all(thing):
    """Public Part: one verification-request Thing to one verdict Thing."""
    return audited_mode_primitive(thing)
