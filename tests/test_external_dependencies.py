"""Offline acceptance and mutation proofs for dependency provenance."""

from __future__ import annotations

import ast
import copy
import inspect
import json
import shutil
import socket
from pathlib import Path

from unified.boundary import inward
from unified.dependency_provenance import verify_external_dependencies


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "seed/EXTERNAL_DEPENDENCIES.json").read_text())


def _fixture(tmp_path):
    for relative in (
        "c/third_party/cJSON.c",
        "c/third_party/cJSON.h",
        "c/third_party/LICENSE.cJSON",
        "c/third_party/sha256.c",
        "c/third_party/sha256.h",
        "LICENSE",
        "seed/EXTERNAL_DEPENDENCIES.json",
        "seed/ROOT.seed.json",
    ):
        source = ROOT / relative
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return tmp_path


def _verify(root):
    return verify_external_dependencies(inward({"root": str(root)}))


def _write_manifest(root, manifest):
    (root / "seed/EXTERNAL_DEPENDENCIES.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def test_complete_inventory_verifies_offline_and_deterministically(tmp_path, monkeypatch):
    root = _fixture(tmp_path)

    def reject_network(*_arguments, **_keywords):
        raise AssertionError("network boundary entered")

    monkeypatch.setattr(socket, "socket", reject_network)
    first = _verify(root)
    second = _verify(root)
    assert first == second
    assert first["state"] == "valid"
    assert first["value"] == {
        "format_version": "UC-EXTERNAL-DEPENDENCIES-1",
        "manifest_sha256": "0a47ed86825c968d8e24cb18793f41f5e31fa1d6d739cc8117ac6d26366f11a5",
        "dependency_count": 2,
        "artifact_count": 5,
        "artifacts": (
            "c/third_party/cJSON.c",
            "c/third_party/cJSON.h",
            "c/third_party/LICENSE.cJSON",
            "c/third_party/sha256.c",
            "c/third_party/sha256.h",
        ),
        "offline": True,
        "ticket": None,
    }
    assert first["evidence"] == ("boundary:inward", "dependencies:verified")


def test_missing_hash_license_and_undeclared_files_are_rejected(tmp_path):
    cases = []

    missing_root = _fixture(tmp_path / "missing")
    (missing_root / "c/third_party/cJSON.h").unlink()
    cases.append((missing_root, "artifact:c/third_party/cJSON.h:missing"))

    changed_root = _fixture(tmp_path / "changed")
    (changed_root / "c/third_party/cJSON.c").write_text("changed\n")
    cases.append((changed_root, "artifact:c/third_party/cJSON.c:hash-mismatch"))

    license_root = _fixture(tmp_path / "license")
    (license_root / "c/third_party/LICENSE.cJSON").write_text("wrong license\n")
    cases.append((license_root, "license:c/third_party/LICENSE.cJSON:hash-mismatch"))

    undeclared_root = _fixture(tmp_path / "undeclared")
    (undeclared_root / "c/third_party/surprise.c").write_text("unexpected\n")
    cases.append((undeclared_root, "artifact:c/third_party/surprise.c:undeclared"))

    for root, expected in cases:
        first = _verify(root)
        second = _verify(root)
        assert first == second
        assert first["state"] == "invalid"
        assert expected in first["value"]["errors"]
        assert first["value"]["ticket"] is None
        assert "dependencies:verified" not in first["evidence"]
        assert "manifest_sha256" not in first["value"]
        assert _verify(_fixture(root / "recovered"))["state"] == "valid"


def test_incomplete_mutable_duplicate_and_unpinned_records_are_rejected(tmp_path):
    mutations = []

    incomplete = copy.deepcopy(MANIFEST)
    del incomplete["dependencies"][0]["maintenance"]
    mutations.append((incomplete, "dependency:0:fields"))

    mutable = copy.deepcopy(MANIFEST)
    mutable["dependencies"][0]["artifacts"][0]["immutable_source"] = (
        "https://raw.githubusercontent.com/DaveGamble/cJSON/main/cJSON.c"
    )
    mutations.append((mutable, "artifact:c/third_party/cJSON.c:mutable-source"))

    duplicate = copy.deepcopy(MANIFEST)
    duplicate["dependencies"][1]["artifacts"][0]["artifact_id"] = "cjson-source"
    mutations.append((duplicate, "manifest:duplicate-artifact-id"))

    for index, (manifest, expected) in enumerate(mutations):
        root = _fixture(tmp_path / str(index))
        _write_manifest(root, manifest)
        result = _verify(root)
        assert result["state"] == "invalid"
        assert expected in result["value"]["errors"]
        assert result["value"]["ticket"] is None


def test_root_bootstrap_manifest_references_are_enforced(tmp_path):
    root = _fixture(tmp_path)
    root_seed_path = root / "seed/ROOT.seed.json"
    root_seed = json.loads(root_seed_path.read_text())
    root_seed["vendored"][0]["id"] = "wrong-id"
    root_seed["vendored"][1]["license"] = "wrong-license"
    root_seed["vendored"].pop()
    root_seed_path.write_text(json.dumps(root_seed), encoding="utf-8")
    result = _verify(root)
    assert result["state"] == "invalid"
    assert {
        "root-seed:vendored:c/third_party/cJSON.c:id",
        "root-seed:vendored:c/third_party/cJSON.h:license",
        "root-seed:vendored:c/third_party/sha256.h:missing",
    }.issubset(result["value"]["errors"])


def test_dictionary_order_does_not_change_manifest_identity(tmp_path):
    baseline_root = _fixture(tmp_path / "baseline")
    baseline = _verify(baseline_root)
    reordered_root = _fixture(tmp_path / "reordered")
    manifest = copy.deepcopy(MANIFEST)
    manifest = dict(reversed(tuple(manifest.items())))
    manifest["dependencies"] = list(reversed(manifest["dependencies"]))
    manifest["dependencies"] = [
        dict(reversed(tuple(dependency.items())))
        for dependency in manifest["dependencies"]
    ]
    _write_manifest(reordered_root, manifest)
    reordered = _verify(reordered_root)
    assert reordered["state"] == "valid"
    assert reordered["value"]["manifest_sha256"] == baseline["value"][
        "manifest_sha256"
    ]


def test_public_part_is_one_thing_to_one_thing_without_physical_control_flow():
    assert len(inspect.signature(verify_external_dependencies).parameters) == 1
    tree = ast.parse(inspect.getsource(verify_external_dependencies))
    forbidden = (
        ast.If,
        ast.For,
        ast.While,
        ast.Match,
        ast.Try,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )
    assert not [node for node in ast.walk(tree) if isinstance(node, forbidden)]
    assert _verify(ROOT)["state"] == "valid"


def test_missing_manifest_is_expected_invalidity_without_ticket(tmp_path):
    result = _verify(tmp_path)
    assert result["state"] == "invalid"
    assert result["value"] == {"errors": ("manifest:missing", "root-seed:missing"), "ticket": None}
    assert result["evidence"] == ("boundary:inward", "dependencies:rejected")
