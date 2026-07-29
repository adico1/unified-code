"""CI boundary assertion for a completed ``uc verify-all`` Thing."""

from __future__ import annotations

import json
import subprocess
import sys


def audited_assertion_boundary():
    completed = subprocess.run(
        [sys.executable, "-m", "unified.generator.cli", "verify-all"],
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(completed.stdout)
    value = result["value"]
    assert result["state"] == "valid", value
    assert value["cache"] == "warm", value
    assert value["verification_seconds"] <= 5.0, value
    assert value["bootstrap_repository_actions"] == 0, value
    assert value["proofs_passed"] == value["proof_nodes"], value
    assert value["proof_nodes"] == 24, value
    assert value["explicit_conditional_nodes"] == 0, value
    assert value["explicit_loop_nodes"] == 0, value
    return value


evidence = audited_assertion_boundary()
print(
    json.dumps(
        {
            key: evidence[key]
            for key in (
                "bootload_seconds",
                "verification_seconds",
                "total_seconds",
                "critical_path_seconds",
                "critical_path_nodes",
                "parallel_workers",
                "structure_hash",
                "evidence_hash",
            )
        },
        sort_keys=True,
    )
)
