"""Isolated Stage1-A/Stage1-B byte fixed-point proofs."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "seed" / "stage0" / "TRUSTED_INPUTS.json"
SPEC = importlib.util.spec_from_file_location(
    "uc_stage1_fixed_point", REPO / "bootstrap" / "fixed_point.py"
)
assert SPEC is not None and SPEC.loader is not None
fixed = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixed)


def canonical(value):
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode()


def copy_trust_tree(target):
    contract = json.loads(CONTRACT.read_text())
    for entry in contract["trusted_inputs"]:
        destination = target / entry["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / entry["path"], destination)
    contract_path = target / "TRUSTED_INPUTS.json"
    contract_path.write_bytes(canonical(contract))
    return contract_path


def request(trust, contract, output):
    return {
        "value": {
            "stage0_path": str(trust / "bootstrap" / "stage0.py"),
            "contract_path": str(contract),
            "input_root": str(trust),
            "output": str(output),
        },
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": "formed",
    }


def tree_bytes(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_isolated_stage1_fixed_point_has_complete_byte_evidence(tmp_path):
    trust = tmp_path / "trust"
    contract = copy_trust_tree(trust)
    output = tmp_path / "proof"
    result = fixed.prove_stage1_fixed_point(request(trust, contract, output))
    assert result["state"] == "valid", result["value"]
    assert result["value"]["fixed_point"] is True
    assert result["value"]["tree_sha256_a"] == result["value"]["tree_sha256_b"]
    assert result["evidence"][-1] == "fixed-point:bilima"
    report = json.loads((output / "fixed-point-report.json").read_text())
    assert report["producer_a"] == "trusted-stage0"
    assert report["producer_b"] == "generated-stage1-a"
    assert report["byte_identical"] is True
    assert report["missing_from_a"] == report["missing_from_b"] == []
    assert report["mismatches"] == []
    assert report["inventory_a"] == report["inventory_b"]
    assert [item["path"] for item in report["inventory_a"]] == list(
        fixed.STAGE1_FILES
    )
    assert tree_bytes(output / "stage1-a") == tree_bytes(output / "stage1-b")


def test_path_locale_clock_and_record_order_do_not_change_fixed_point(
    tmp_path, monkeypatch
):
    first_trust = tmp_path / "first-trust"
    second_trust = tmp_path / "second-trust"
    first_contract = copy_trust_tree(first_trust)
    second_contract = copy_trust_tree(second_trust)
    seed_path = second_trust / "seed" / "ROOT.seed.json"
    seed = json.loads(seed_path.read_text())
    seed_path.write_text(json.dumps(dict(reversed(list(seed.items()))), indent=7))
    monkeypatch.setenv("LANG", "he_IL.UTF-8")
    monkeypatch.setenv("LC_ALL", "he_IL.UTF-8")
    monkeypatch.setenv("TZ", "Asia/Jerusalem")
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "999999999")
    first = fixed.prove_stage1_fixed_point(
        request(first_trust, first_contract, tmp_path / "location-a" / "proof")
    )
    second = fixed.prove_stage1_fixed_point(
        request(second_trust, second_contract, tmp_path / "location-b" / "proof")
    )
    assert first["state"] == second["state"] == "valid"
    assert first["value"]["tree_sha256_a"] == second["value"]["tree_sha256_a"]


def test_stage1_seed_mutation_is_detected_by_byte_comparison(tmp_path):
    trust = tmp_path / "trust"
    contract = copy_trust_tree(trust)
    proof = tmp_path / "proof"
    assert fixed.prove_stage1_fixed_point(request(trust, contract, proof))["state"] == "valid"
    mutated_seed = tmp_path / "ROOT.mutated.json"
    seed = json.loads((trust / "seed" / "ROOT.seed.json").read_text())
    seed["description"] = "deliberate fixed-point mutation"
    mutated_seed.write_bytes(canonical(seed))
    mutated_b = tmp_path / "mutated-b"
    completed = subprocess.run(
        [
            sys.executable,
            str(proof / "stage1-a" / "stage1.py"),
            str(mutated_seed),
            str(mutated_b),
        ],
        cwd=tmp_path,
        env={"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    comparison = fixed.compare_stage1_trees(proof / "stage1-a", mutated_b)
    assert comparison["byte_identical"] is False
    assert comparison["tree_sha256_a"] != comparison["tree_sha256_b"]
    assert [item["path"] for item in comparison["mismatches"]] == [
        "stage1-manifest.json"
    ]


def test_stage1_and_manifest_byte_mutations_have_exact_diagnostics(tmp_path):
    trust = tmp_path / "trust"
    contract = copy_trust_tree(trust)
    proof = tmp_path / "proof"
    assert fixed.prove_stage1_fixed_point(request(trust, contract, proof))["state"] == "valid"
    mutated = tmp_path / "mutated"
    shutil.copytree(proof / "stage1-b", mutated)
    for name in ("stage1.py", "stage1-manifest.json"):
        path = mutated / name
        path.write_bytes(path.read_bytes() + b"\nmutation")
    comparison = fixed.compare_stage1_trees(proof / "stage1-a", mutated)
    assert comparison["byte_identical"] is False
    assert [item["path"] for item in comparison["mismatches"]] == [
        "stage1-manifest.json",
        "stage1.py",
    ]
    assert all(item["first_differing_byte"] > 0 for item in comparison["mismatches"])


def test_failure_cannot_replace_previous_fixed_point_claim(tmp_path):
    trust = tmp_path / "trust"
    contract = copy_trust_tree(trust)
    output = tmp_path / "proof"
    valid = fixed.prove_stage1_fixed_point(request(trust, contract, output))
    assert valid["state"] == "valid"
    before = tree_bytes(output)
    broken = request(trust, contract, output)
    broken["value"]["stage0_path"] = str(tmp_path / "missing-stage0.py")
    rejected = fixed.prove_stage1_fixed_point(broken)
    assert rejected["state"] == "invalid"
    assert rejected["value"]["fixed_point"] is False
    assert tree_bytes(output) == before
    assert not list(tmp_path.glob(".proof.fixed-point-new-*"))


def test_fixed_point_public_part_and_cli(tmp_path):
    assert fixed.prove_stage1_fixed_point.__code__.co_argcount == 1
    malformed = fixed.prove_stage1_fixed_point({"value": {}})
    assert malformed["state"] == "invalid"
    trust = tmp_path / "trust"
    contract = copy_trust_tree(trust)
    output = tmp_path / "proof"
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO / "bootstrap" / "fixed_point.py"),
            "--stage0",
            str(trust / "bootstrap" / "stage0.py"),
            "--contract",
            str(contract),
            "--input-root",
            str(trust),
            "--output",
            str(output),
        ],
        capture_output=True,
        check=False,
    )
    result = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert result["state"] == "valid"
    report = json.loads((output / "fixed-point-report.json").read_text())
    assert report["tree_sha256_a"] == report["tree_sha256_b"]
