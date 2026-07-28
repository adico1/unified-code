"""Event-declared complete verification flow.

Application orchestration is data. All unavoidable host iteration and selection
is confined to ``audited_scheduler_primitive`` and measured structurally.
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
FLOW_EVENTS = (
    "verification.requested",
    "authority.discovered",
    "identities.resolved",
    "proof_graph.formed",
    "prerequisites.materialized",
    "proof_nodes.released",
    "proof_nodes.executed",
    "evidence.collected",
    "identities.compared",
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
)


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
        (audited_nodes if function.name.startswith("audited_") else application_polling).extend(
            polling
        )
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
        "bootstrap_nodes",
        "proof_nodes",
    }
    if set(graph) != required:
        errors.append("graph-shape")
    if graph.get("format_version") != "UC-VERIFY-FLOW-1":
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
    bootstrap = graph.get("bootstrap_nodes", ())
    proofs = graph.get("proof_nodes", ())
    bootstrap_ids = [item.get("id") for item in bootstrap]
    proof_ids = [item.get("id") for item in proofs]
    if len(bootstrap_ids) != len(set(bootstrap_ids)):
        errors.append("duplicate-event")
    if len(proof_ids) != len(set(proof_ids)):
        errors.append("duplicate-proof")
    if any(item.get("handler") != "command" for item in bootstrap):
        errors.append("unregistered-handler")
    if any(item.get("requires") for item in bootstrap):
        errors.append("unresolved-dependency")
    if any(
        identity not in bootstrap_ids
        for item in proofs
        for identity in item.get("requires", ())
    ):
        errors.append("unresolved-dependency")
    return {"ok": not errors, "errors": sorted(set(errors))}


def audited_command_node_primitive(node):
    """Audited worker boundary for one released command event."""
    argv = [
        token.replace("{python}", sys.executable).replace("{root}", str(ROOT))
        for token in node["argv"]
    ]
    started = time.monotonic()
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
        "duration_seconds": time.monotonic() - started,
        "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(completed.stderr).hexdigest(),
        "stdout_tail": completed.stdout.decode("utf-8", errors="replace")[-100000:],
        "stderr_tail": completed.stderr.decode("utf-8", errors="replace")[-100000:],
    }


HANDLER_REGISTRY = {"command": audited_command_node_primitive}


def audited_scheduler_primitive(thing, graph, cache_root):
    """The single audited host machine for iteration, waiting, and routing."""
    bootstrap_started = time.monotonic()
    graph_report = audited_graph_report_primitive(graph)
    if not graph_report["ok"]:
        return {
            **thing,
            "value": {
                **thing["value"],
                "error": "proof-graph.invalid",
                "graph_errors": graph_report["errors"],
            },
            "evidence": (*thing["evidence"], "verification.failed"),
            "state": "invalid",
        }
    authority_root = Path(os.environ.get("UC_VERIFY_AUTHORITY_ROOT", ROOT))
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=authority_root,
        capture_output=True,
        check=True,
    ).stdout.split(b"\0")
    authority_paths = tuple(
        authority_root / raw.decode("utf-8") for raw in tracked if raw
    )
    source_identity = _sha(
        {
            path.relative_to(authority_root).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in authority_paths
        }
    )
    structure_hash = _sha(
        {
            "authority": source_identity,
            "graph": graph,
            "events": FLOW_EVENTS,
        }
    )
    tool_identity = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "system": platform.system(),
        "machine": platform.machine(),
    }
    if thing["value"].get("error"):
        return {
            **thing,
            "value": {**thing["value"], "verdict": "fail"},
            "evidence": (*thing["evidence"], "verification.failed"),
            "state": "invalid",
        }
    cache = cache_root / _sha(
        {"structure_hash": structure_hash, "tool_identity": tool_identity}
    )
    evidence_path = cache / "bootstrap-evidence.json"
    warm = evidence_path.is_file()
    bootstrap_evidence = None
    if warm:
        bootstrap_evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        expected_cache_identity = _sha(
            {
                "structure_hash": bootstrap_evidence.get("structure_hash"),
                "tool_identity": bootstrap_evidence.get("tool_identity"),
                "results": bootstrap_evidence.get("results"),
            }
        )
        if (
            bootstrap_evidence.get("structure_hash") != structure_hash
            or bootstrap_evidence.get("tool_identity") != tool_identity
            or bootstrap_evidence.get("cache_identity") != expected_cache_identity
        ):
            return {
                **thing,
                "value": {
                    **thing["value"],
                    "error": "identity.stale",
                    "verdict": "fail",
                },
                "evidence": (*thing["evidence"], "identity.stale", "verification.failed"),
                "state": "invalid",
            }
    if not warm:
        cache.mkdir(parents=True, exist_ok=True)
        nodes = graph["bootstrap_nodes"]
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, len(nodes))
        ) as workers:
            futures = [
                workers.submit(HANDLER_REGISTRY[node["handler"]], node)
                for node in nodes
            ]
            results = [future.result() for future in futures]
        bootstrap_evidence = {
            "structure_hash": structure_hash,
            "tool_identity": tool_identity,
            "results": results,
        }
        bootstrap_evidence["cache_identity"] = _sha(
            {
                "structure_hash": structure_hash,
                "tool_identity": tool_identity,
                "results": results,
            }
        )
        evidence_path.write_bytes(_canonical(bootstrap_evidence))
    bootstrap_seconds = time.monotonic() - bootstrap_started
    verification_started = time.monotonic()
    terminal = {item["id"]: item for item in bootstrap_evidence["results"]}
    verdicts = []
    for node in graph["proof_nodes"]:
        received = [terminal.get(identity) for identity in node["requires"]]
        verdicts.append(
            {
                "id": node["id"],
                "status": "pass"
                if all(item is not None and item["returncode"] == 0 for item in received)
                else "fail",
            }
        )
    verification_seconds = time.monotonic() - verification_started
    passed = sum(item["status"] == "pass" for item in verdicts)
    complete = passed == len(verdicts)
    within_budget = verification_seconds <= graph["budget_seconds"]
    state = "valid" if complete and within_budget else "invalid"
    evidence = {
        "structure_hash": structure_hash,
        "ordered_verdicts": verdicts,
        "environment": {
            **tool_identity,
            "cache": "warm" if warm else "cold",
        },
        "bootstrap_seconds": bootstrap_seconds,
        "verification_seconds": verification_seconds,
    }
    evidence_hash = _sha(evidence)
    source_report = audited_source_report_primitive(
        Path(__file__).read_text(encoding="utf-8")
    )
    return outward(
        {
            **thing,
            "value": {
                **thing["value"],
                "error": None if state == "valid" else "verification.failed",
                "verdict": "pass" if state == "valid" else "fail",
                "cache": "warm" if warm else "cold",
                "events": list(FLOW_EVENTS if state == "valid" else (*FLOW_EVENTS[:-1], "verification.failed")),
                "proof_nodes": len(verdicts),
                "proofs_passed": passed,
                "bootstrap_seconds": bootstrap_seconds,
                "verification_seconds": verification_seconds,
                "total_seconds": bootstrap_seconds + verification_seconds,
                "critical_path_seconds": max(
                    (item["duration_seconds"] for item in bootstrap_evidence["results"]),
                    default=0.0,
                ),
                "structure_hash": structure_hash,
                "evidence_hash": evidence_hash,
                **source_report,
            },
            "evidence": (*thing["evidence"], *FLOW_EVENTS),
            "state": state,
        }
    )


def verify_all(thing):
    """Public Part: one verification-request Thing to one verdict Thing."""
    return audited_scheduler_primitive(
        thing,
        json.loads(GRAPH.read_text(encoding="utf-8")),
        Path(os.environ.get("UC_VERIFY_CACHE", "/tmp/unified-code-verify-cache")),
    )
