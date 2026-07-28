"""CI boundary assertion for a completed ``uc verify-all`` Thing."""

from __future__ import annotations

import json
import subprocess


def audited_assertion_boundary():
    completed = subprocess.run(
        ["uc", "verify-all"], capture_output=True, text=True, check=True
    )
    result = json.loads(completed.stdout)
    value = result["value"]
    assert result["state"] == "valid", value
    assert value["cache"] == "warm", value
    assert value["verification_seconds"] <= 5.0, value
    assert value["proofs_passed"] == value["proof_nodes"], value
    assert value["explicit_conditional_nodes"] == 0, value
    assert value["explicit_loop_nodes"] == 0, value
    return value


evidence = audited_assertion_boundary()
print("verify-all warm PASS", evidence["verification_seconds"])
