"""Build a privacy-preserving retrospective of Unified Code development.

The extractor reads named local boundaries and emits aggregate evidence. It
never copies prompts, responses, source payloads, paths, environment values,
credentials, or raw session identifiers into the public dataset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


FORMAT = "uc-economic-retrospective-1"
EXTRACTOR_VERSION = "UC-ECONOMIC-RETROSPECTIVE-1"
TOKEN_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
PUBLISHED_EVENTS = (
    "agent_message",
    "custom_tool_call",
    "custom_tool_call_output",
    "function_call",
    "function_call_output",
    "patch_apply_end",
    "task_complete",
    "task_started",
    "user_message",
)


def canonical_bytes(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_value(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def parse_time(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(
        timezone.utc
    )


def under_project(path_value, project_roots):
    try:
        candidate = Path(path_value).resolve()
    except (OSError, TypeError, ValueError):
        return False
    return any(candidate == root or root in candidate.parents for root in project_roots)


def session_projection(path, cutoff, project_roots):
    events = []
    malformed = 0
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for raw in stream:
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                malformed += 1
                continue
            timestamp = event.get("timestamp")
            if not timestamp or parse_time(timestamp) > cutoff:
                continue
            events.append(event)
    contexts = [
        event.get("payload") or {}
        for event in events
        if event.get("type") in {"session_meta", "turn_context"}
    ]
    if not any(under_project(context.get("cwd"), project_roots) for context in contexts):
        return None
    session_meta = next(
        (
            event.get("payload") or {}
            for event in events
            if event.get("type") == "session_meta"
        ),
        {},
    )
    turn_contexts = [
        event.get("payload") or {}
        for event in events
        if event.get("type") == "turn_context"
    ]
    models = sorted(
        {
            str(context.get("model"))
            for context in turn_contexts
            if context.get("model")
        }
    )
    event_counts = Counter(
        str((event.get("payload") or {}).get("type"))
        for event in events
        if (event.get("payload") or {}).get("type") in PUBLISHED_EVENTS
    )
    token_events = [
        event.get("payload") or {}
        for event in events
        if event.get("type") == "event_msg"
        and (event.get("payload") or {}).get("type") == "token_count"
        and (event.get("payload") or {}).get("info")
    ]
    final_usage = (
        token_events[-1].get("info", {}).get("total_token_usage", {})
        if token_events
        else {}
    )
    token_usage = {
        field: int(final_usage.get(field) or 0)
        for field in TOKEN_FIELDS
    }
    timestamps = sorted(parse_time(event["timestamp"]) for event in events)
    identity = session_meta.get("session_id") or session_meta.get("id") or path.name
    return {
        "session_identity_sha256": sha256_value(str(identity)),
        "started_at": timestamps[0].isoformat().replace("+00:00", "Z"),
        "last_observed_at": timestamps[-1].isoformat().replace("+00:00", "Z"),
        "observed_span_seconds": int((timestamps[-1] - timestamps[0]).total_seconds()),
        "provider": str(session_meta.get("model_provider") or "unknown"),
        "models": models,
        "event_counts": {key: event_counts.get(key, 0) for key in PUBLISHED_EVENTS},
        "token_usage": token_usage,
        "malformed_lines": malformed,
    }


def sessions_projection(sessions_root, cutoff, project_roots):
    projected = [
        session_projection(path, cutoff, project_roots)
        for path in sorted(sessions_root.rglob("*.jsonl"))
    ]
    sessions = sorted(
        (item for item in projected if item is not None),
        key=lambda item: item["session_identity_sha256"],
    )
    event_totals = {
        event: sum(session["event_counts"][event] for session in sessions)
        for event in PUBLISHED_EVENTS
    }
    token_totals = {
        field: sum(session["token_usage"][field] for session in sessions)
        for field in TOKEN_FIELDS
    }
    token_totals["uncached_input_tokens"] = (
        token_totals["input_tokens"] - token_totals["cached_input_tokens"]
    )
    semantic = {
        "sessions": sessions,
        "summary": {
            "session_count": len(sessions),
            "malformed_lines": sum(item["malformed_lines"] for item in sessions),
            "observed_span_seconds_sum": sum(
                item["observed_span_seconds"] for item in sessions
            ),
            "event_totals": event_totals,
            "token_totals": token_totals,
        },
    }
    return {**semantic, "projection_sha256": sha256_value(semantic)}


def git_output(repository, *arguments):
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def git_projection(repository, cutoff_text):
    snapshot_commit = git_output(
        repository,
        "rev-list",
        "--all",
        f"--before={cutoff_text}",
        "--max-count=1",
    ).strip()
    raw = git_output(
        repository,
        "log",
        "--all",
        f"--before={cutoff_text}",
        "--format=commit%x09%H%x09%aI%x09%P%x09%s",
        "--numstat",
    )
    commits = []
    current = None
    merge_pull_requests = 0
    for line in raw.splitlines():
        if line.startswith("commit\t"):
            _, commit_sha, authored_at, parents, subject = line.split("\t", 4)
            current = {
                "commit_id": commit_sha,
                "authored_at": authored_at,
                "parent_count": len(parents.split()) if parents else 0,
                "files_changed": 0,
                "lines_added": 0,
                "lines_deleted": 0,
            }
            commits.append(current)
            merge_pull_requests += int(subject.startswith("Merge pull request #"))
            continue
        columns = line.split("\t")
        if current is None or len(columns) != 3 or not columns[0].isdigit() or not columns[1].isdigit():
            continue
        current["files_changed"] += 1
        current["lines_added"] += int(columns[0])
        current["lines_deleted"] += int(columns[1])
    commits.sort(key=lambda item: item["commit_id"])
    semantic = {
        "commits": commits,
        "summary": {
            "snapshot_commit": snapshot_commit,
            "commit_count": len(commits),
            "merge_pull_request_count": merge_pull_requests,
            "numstat_rows": sum(item["files_changed"] for item in commits),
            "lines_added": sum(item["lines_added"] for item in commits),
            "lines_deleted": sum(item["lines_deleted"] for item in commits),
        },
    }
    return {**semantic, "projection_sha256": sha256_value(semantic)}


def snapshot_file(repository, snapshot_commit, path):
    return git_output(repository, "show", f"{snapshot_commit}:{path}").encode("utf-8")


def product_projection(repository, snapshot_commit):
    raw = snapshot_file(repository, snapshot_commit, "build/index.json")
    index = json.loads(raw)
    products = index.get("products") or []
    summary = {
        "product_count": len(products),
        "groups": dict(sorted((index.get("groups") or {}).items())),
        "generated_source_lines": sum(item.get("source_lines") or 0 for item in products),
        "acceptance_cases": sum(
            (item.get("acceptance") or {}).get("total") or 0 for item in products
        ),
        "acceptance_passed": sum(
            (item.get("acceptance") or {}).get("passed") or 0 for item in products
        ),
    }
    return {"index_sha256": hashlib.sha256(raw).hexdigest(), "summary": summary}


def proof_projection(repository, snapshot_commit):
    raw = snapshot_file(
        repository, snapshot_commit, "seed/verification/PROOF_BUNDLE.json"
    )
    bundle = json.loads(raw)
    verdicts = bundle.get("verdicts") or []
    return {
        "bundle_file_sha256": hashlib.sha256(raw).hexdigest(),
        "bundle_identity": bundle.get("bundle_identity"),
        "source_file_count": bundle.get("source_file_count"),
        "proof_count": len(verdicts),
        "proofs_passed": sum(item.get("status") == "pass" for item in verdicts),
        "stage1_fixed_point": bundle.get("stage1_fixed_point"),
    }


def build_retrospective(repository, sessions_root, project_roots, cutoff_text):
    cutoff = parse_time(cutoff_text)
    sessions = sessions_projection(sessions_root, cutoff, project_roots)
    git = git_projection(repository, cutoff_text)
    snapshot_commit = git["summary"]["snapshot_commit"]
    products = product_projection(repository, snapshot_commit)
    proofs = proof_projection(repository, snapshot_commit)
    semantic = {
        "format": FORMAT,
        "extractor_version": EXTRACTOR_VERSION,
        "status": "retrospective-observational",
        "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
        "sources": {
            "codex_sessions": sessions,
            "git": git,
            "generated_products": products,
            "verification": proofs,
        },
        "privacy": {
            "published": [
                "aggregate counters",
                "content hashes",
                "hashed session identities",
                "model and provider identities",
                "event timestamps"
            ],
            "excluded": [
                "conversation content",
                "prompts and responses",
                "tool arguments and outputs",
                "source payloads and patches",
                "personal filesystem paths",
                "environment values",
                "credentials and secrets",
                "raw session identities"
            ]
        },
        "measurement_boundary": {
            "tokens": "Codex cumulative counters; not provider billing receipts",
            "session_forks": "each log is a separate observation; inherited context can be counted again",
            "tool_calls": "recorded events; not equivalent to human effort",
            "session_span": "first-to-last observed event; overlapping spans are not additive wall time",
            "git_churn": "historical additions and deletions; rewrites are counted repeatedly",
            "products": "generated build inventory at extraction; not an economic sample",
            "causality": "no isolated counterfactual arm; causal savings remain unknown"
        },
        "allowed_claim": "The project has measurable retrospective development activity and generated outcomes.",
        "prohibited_claims": [
            "Unified Code caused the observed effort or outcomes",
            "the retrospective proves cost savings",
            "the retrospective proves economy-wide or trillion-dollar savings"
        ]
    }
    return {**semantic, "dataset_sha256": sha256_value(semantic)}


def write_dataset(dataset, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(dataset) + b"\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--sessions", required=True, type=Path)
    parser.add_argument("--project-root", required=True, action="append", type=Path)
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    repository = args.repository.resolve()
    roots = tuple(path.resolve() for path in args.project_root)
    dataset = build_retrospective(
        repository, args.sessions.resolve(), roots, args.cutoff
    )
    write_dataset(dataset, args.output)
    print(json.dumps({
        "dataset_sha256": dataset["dataset_sha256"],
        "output": str(args.output),
        "session_count": dataset["sources"]["codex_sessions"]["summary"]["session_count"],
        "status": dataset["status"]
    }, sort_keys=True))


if __name__ == "__main__":
    main()
