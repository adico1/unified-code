"""Generated Stage1-A framework/generator and clean-room handoff proofs."""

from __future__ import annotations

import hashlib
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
    "uc_stage0_stage1", REPO / "bootstrap" / "stage0.py"
)
assert SPEC is not None and SPEC.loader is not None
stage0 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stage0)


def canonical(value):
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()


def thing(contract, root, output):
    return {
        "value": {
            "contract_path": str(contract),
            "input_root": str(root),
            "output": str(output),
        },
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": "formed",
    }


def copy_trust_tree(target):
    contract = json.loads(CONTRACT.read_text())
    for entry in contract["trusted_inputs"]:
        destination = target / entry["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / entry["path"], destination)
    contract_path = target / "TRUSTED_INPUTS.json"
    contract_path.write_bytes(canonical(contract))
    return contract_path, contract


def update_root_hash(contract, root):
    seed = json.loads((root / "seed" / "ROOT.seed.json").read_text())
    digest = hashlib.sha256(canonical(seed)).hexdigest()
    next(
        entry
        for entry in contract["trusted_inputs"]
        if entry["role"] == "root-seed"
    )["sha256"] = digest


def tree_bytes(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def generate(root, contract, output):
    return stage0.stage0_generate(thing(contract, root, output))


def test_stage0_generates_runnable_stage1_with_complete_provenance(tmp_path):
    root = tmp_path / "trust"
    contract, _ = copy_trust_tree(root)
    output = tmp_path / "stage1-a"
    result = generate(root, contract, output)
    assert result["state"] == "valid", result["value"]
    assert result["value"]["stage1_tree_sha256"] == result["value"][
        "stage1_manifest"
    ]["tree_sha256"]
    assert sorted(tree_bytes(output)) == [
        "framework/contract.json",
        "generated/root_surface/ROOT_STATUS.md",
        "generated/root_surface/repository-contract.json",
        "generated/root_surface/watchers.json",
        "generator/contract.json",
        "seed/ROOT.seed.json",
        "stage1-manifest.json",
        "stage1.py",
        "uem/contract.json",
    ]
    manifest = json.loads((output / "stage1-manifest.json").read_text())
    assert manifest["generator_identity"] == "UC-STAGE1-PY-1"
    assert {item["path"] for item in manifest["files"]} == {
        "framework/contract.json",
        "generated/root_surface/ROOT_STATUS.md",
        "generated/root_surface/repository-contract.json",
        "generated/root_surface/watchers.json",
        "generator/contract.json",
        "seed/ROOT.seed.json",
        "stage1.py",
        "uem/contract.json",
    }
    assert all(item["originating_seed_nodes"] for item in manifest["files"])
    assert all("depends_on" in item for item in manifest["files"])
    assert json.loads((output / "seed/ROOT.seed.json").read_text()) == json.loads(
        (root / "seed/ROOT.seed.json").read_text()
    )
    repository = json.loads(
        (output / "generated/root_surface/repository-contract.json").read_text()
    )
    assert repository["format_version"] == "UC-ROOT-REPOSITORY-1"
    assert repository["depths"] == list(range(1, 11))
    assert len(repository["watchers"]) == 10
    assert json.loads(
        (output / "generated/root_surface/watchers.json").read_text()
    ) == repository["watchers"]
    assert (output / "generated/root_surface/ROOT_STATUS.md").read_text() == (
        "\n".join(repository["summary_lines"]) + "\n"
    )
    assert os.access(output / "stage1.py", os.R_OK)


def test_independent_stage0_runs_are_byte_identical_and_path_independent(tmp_path):
    root_a = tmp_path / "trust-a"
    root_b = tmp_path / "trust-b"
    contract_a, _ = copy_trust_tree(root_a)
    contract_b, _ = copy_trust_tree(root_b)
    output_a = tmp_path / "one" / "stage1"
    output_b = tmp_path / "two" / "stage1"
    first = generate(root_a, contract_a, output_a)
    second = generate(root_b, contract_b, output_b)
    assert first["state"] == second["state"] == "valid"
    assert first["value"]["stage1_tree_sha256"] == second["value"][
        "stage1_tree_sha256"
    ]
    assert tree_bytes(output_a) == tree_bytes(output_b)
    raw = b"".join(tree_bytes(output_a).values())
    assert str(root_a).encode() not in raw
    assert str(root_b).encode() not in raw


def test_generated_stage1_evaluates_root_seed_without_repository(tmp_path):
    trust = tmp_path / "trust"
    contract, _ = copy_trust_tree(trust)
    stage1_a = tmp_path / "stage1-a"
    assert generate(trust, contract, stage1_a)["state"] == "valid"
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    seed = isolated / "ROOT.seed.json"
    shutil.copyfile(trust / "seed" / "ROOT.seed.json", seed)
    stage1_b = tmp_path / "stage1-b"
    completed = subprocess.run(
        [sys.executable, str(stage1_a / "stage1.py"), str(seed), str(stage1_b)],
        cwd=isolated,
        env={"PATH": os.environ.get("PATH", "")},
        check=False,
        capture_output=True,
    )
    result = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert result["state"] == "valid"
    assert set(result) == {"value", "depths", "axes", "evidence", "state"}
    assert result["value"]["root_seed_identity"] == "uc-canonical"
    assert tree_bytes(stage1_a) == tree_bytes(stage1_b)
    assert str(REPO).encode() not in b"".join(tree_bytes(stage1_b).values())


def test_untrusted_checkout_files_cannot_change_stage1(tmp_path):
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    contract_a, _ = copy_trust_tree(root_a)
    contract_b, _ = copy_trust_tree(root_b)
    extra_a = root_a / "unified" / "generator" / "opaque.py"
    extra_b = root_b / "unified" / "generator" / "opaque.py"
    extra_a.parent.mkdir(parents=True)
    extra_b.parent.mkdir(parents=True)
    extra_a.write_text("application_specific = 'first'\n")
    extra_b.write_text("application_specific = 'second'\n")
    output_a = tmp_path / "out-a"
    output_b = tmp_path / "out-b"
    assert generate(root_a, contract_a, output_a)["state"] == "valid"
    assert generate(root_b, contract_b, output_b)["state"] == "valid"
    assert tree_bytes(output_a) == tree_bytes(output_b)


def test_unsupported_operation_refuses_and_preserves_installed_stage1(tmp_path):
    root = tmp_path / "trust"
    contract_path, contract = copy_trust_tree(root)
    output = tmp_path / "stage1"
    assert generate(root, contract_path, output)["state"] == "valid"
    before = tree_bytes(output)
    seed_path = root / "seed" / "ROOT.seed.json"
    seed = json.loads(seed_path.read_text())
    seed["stage1"]["generator"]["operations"].append("copy-opaque-source")
    seed_path.write_bytes(canonical(seed))
    update_root_hash(contract, root)
    contract_path.write_bytes(canonical(contract))
    rejected = generate(root, contract_path, output)
    assert rejected["state"] == "invalid"
    assert rejected["value"]["error"] == (
        "stage1.generate:standard.gap:unsupported-stage1-operation"
    )
    assert rejected["value"]["ticket"] is None
    assert tree_bytes(output) == before
    assert not list(tmp_path.glob(".stage1.stage0-new*"))


def test_invalid_stage1_seed_cannot_replace_generated_tree(tmp_path):
    root = tmp_path / "trust"
    contract_path, contract = copy_trust_tree(root)
    output = tmp_path / "stage1"
    assert generate(root, contract_path, output)["state"] == "valid"
    before = tree_bytes(output)
    seed_path = root / "seed" / "ROOT.seed.json"
    seed = json.loads(seed_path.read_text())
    seed["stage1"]["generator"]["outputs"][0]["path"] = "../escape.json"
    seed_path.write_bytes(canonical(seed))
    update_root_hash(contract, root)
    contract_path.write_bytes(canonical(contract))
    rejected = generate(root, contract_path, output)
    assert rejected["state"] == "invalid"
    assert "invalid-path" in rejected["value"]["error"]
    assert tree_bytes(output) == before


def test_invalid_repository_projections_are_rejected_atomically(tmp_path):
    cases = [
        (
            lambda seed: seed["repository"]["projections"][0].update(
                {"renderer": "copy-source"}
            ),
            "unsupported-output-declaration",
        ),
        (
            lambda seed: seed["repository"]["projections"][0].update(
                {"depends_on": ["missing-output.json"]}
            ),
            "unsupported-output-declaration",
        ),
        (
            lambda seed: seed["repository"]["projections"][0].update(
                {"path": "framework/contract.json"}
            ),
            "unsupported-output-declaration",
        ),
        (
            lambda seed: seed["repository"].update({"depths": list(range(9))}),
            "unsupported-repository-declaration",
        ),
        (
            lambda seed: seed["repository"]["watchers"][9].update(
                {"id": "authority"}
            ),
            "unsupported-repository-declaration",
        ),
    ]
    for index, (mutate, error) in enumerate(cases):
        root = tmp_path / f"trust-{index}"
        contract_path, contract = copy_trust_tree(root)
        output = tmp_path / f"stage1-{index}"
        assert generate(root, contract_path, output)["state"] == "valid"
        before = tree_bytes(output)
        seed_path = root / "seed" / "ROOT.seed.json"
        seed = json.loads(seed_path.read_text())
        mutate(seed)
        seed_path.write_bytes(canonical(seed))
        update_root_hash(contract, root)
        contract_path.write_bytes(canonical(contract))
        rejected = generate(root, contract_path, output)
        assert rejected["state"] == "invalid"
        assert rejected["value"]["error"] == "stage1.generate:" + error
        assert rejected["value"]["ticket"] is None
        assert tree_bytes(output) == before


def test_invalid_framework_and_uem_declarations_are_rejected(tmp_path):
    cases = [
        (
            lambda seed: seed["stage1"]["framework"]["thing_states"].reverse(),
            "unsupported-framework-declaration",
        ),
        (
            lambda seed: seed["stage1"]["uem"]["opcodes"][0].update(
                {"code": 99}
            ),
            "unsupported-uem-declaration",
        ),
        (
            lambda seed: seed["stage1"]["uem"]["primitives"].append("identity"),
            "unsupported-uem-declaration",
        ),
    ]
    for index, (mutate, error) in enumerate(cases):
        root = tmp_path / f"trust-{index}"
        contract_path, contract = copy_trust_tree(root)
        seed_path = root / "seed" / "ROOT.seed.json"
        seed = json.loads(seed_path.read_text())
        mutate(seed)
        seed_path.write_bytes(canonical(seed))
        update_root_hash(contract, root)
        contract_path.write_bytes(canonical(contract))
        result = generate(root, contract_path, tmp_path / f"out-{index}")
        assert result["state"] == "invalid"
        assert result["value"]["error"] == "stage1.generate:" + error
        assert result["value"]["ticket"] is None


def test_stage1_source_is_generic_and_has_no_opaque_checkout_payload():
    seed = json.loads((REPO / "seed" / "ROOT.seed.json").read_text())
    stage1 = seed["stage1"]
    assert set(stage1) == {"format_version", "framework", "generator", "uem"}
    raw = canonical(stage1).lower()
    for forbidden in (
        b"source_blob",
        b"repository_source",
        b"unified/generator/",
        b"task-ledger",
        b"file-reader",
        b"pong-game",
    ):
        assert forbidden not in raw
    source = (REPO / "bootstrap" / "stage0.py").read_text()
    assert "eval(" not in source
    assert "exec(" not in source
    assert "dynamic import" not in source.lower()


def test_stage0_generate_public_part_and_cli_contract(tmp_path):
    assert stage0.stage0_generate.__code__.co_argcount == 1
    malformed = stage0.stage0_generate({"value": {}})
    assert malformed["state"] == "invalid"
    completed = subprocess.run(
        [sys.executable, str(REPO / "bootstrap" / "stage0.py"), "bad"],
        check=False,
        capture_output=True,
    )
    result = json.loads(completed.stdout)
    assert completed.returncode != 0
    assert result["value"]["error"] == "stage0.cli:usage"
