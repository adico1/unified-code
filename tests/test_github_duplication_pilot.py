"""Truth gates for the bounded public-code duplication pilot."""

import ast
import copy
import json
from pathlib import Path

from scripts.build_github_duplication_pilot import canonical_bytes, measure, normalized_python_sha256, normalized_python_units, sha256_value


ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "seed/economics/github-duplication-pilot.seed.json"
SNAPSHOT = ROOT / "artifacts/economics/github-duplication-pilot.snapshot.json"
REPORT = ROOT / "artifacts/economics/github-duplication-pilot.json"
SCHEMA = ROOT / "seed/economics/GITHUB_DUPLICATION_PILOT_SCHEMA.json"


def load(path):
    return json.loads(path.read_text())


def test_published_pilot_is_canonical_and_reproducible():
    seed, snapshot, report = load(SEED), load(SNAPSHOT), load(REPORT)
    assert measure(seed, snapshot) == report
    assert REPORT.read_bytes() == canonical_bytes(report) + b"\n"
    identity = report.pop("dataset_sha256")
    assert identity == sha256_value(report)


def test_schema_and_claim_boundary_are_frozen():
    schema, report = load(SCHEMA), load(REPORT)
    assert set(schema["required"]) == set(report)
    assert report["status"] == "bounded-public-pilot"
    unknown = set(report["claim_boundary"]["unknown"])
    assert {"causal development effort", "private repositories", "semantic behavior equivalence", "worldwide savings"} <= unknown
    assert any("trillion-dollar" in claim for claim in report["claim_boundary"]["prohibited"])


def test_every_repository_and_family_is_pinned_and_traceable():
    seed, report = load(SEED), load(REPORT)
    assert len(seed["repositories"]) == 12
    assert {item["family"] for item in seed["repositories"]} == {"calculator", "pong", "todo"}
    assert all(len(item["commit_sha"]) == 40 for item in report["repositories"])
    assert all(item["source_url"].endswith(item["commit_sha"]) for item in report["repositories"])


def test_metrics_are_semantic_assertions_not_line_coverage():
    metrics = load(REPORT)["metrics"]
    assert metrics["measured_source_files"] > 0
    assert metrics["measured_source_bytes"] >= metrics["unique_content_bytes"]
    assert metrics["exact_content_addressable_bytes"] == metrics["measured_source_bytes"] - metrics["unique_content_bytes"]
    assert metrics["measured_structural_units"] > 0
    assert metrics["measured_structural_occurrences"] >= metrics["measured_structural_units"]
    assert metrics["recurrent_structural_occurrences"] >= metrics["normalized_structure_cross_repository_groups"]
    assert metrics["normalized_structure_cross_repository_groups"] >= metrics["normalized_structure_cross_family_groups"]
    assert metrics["minimum_cross_repository_reuse_coordinates"] >= metrics["minimum_cross_family_reuse_coordinates"]
    assert metrics["normalized_structure_cross_repository_groups"] >= 0
    assert metrics["recurrent_dependency_groups"] >= 0


def test_structural_proxy_erases_names_and_literals_but_preserves_operations():
    left = "def add(x):\n y = x + 1\n return y * 2\n"
    renamed = "def אחרת(value):\n result = value + 999\n return result * 77\n"
    different = "def add(x):\n y = x * 1\n return y * 2\n"
    assert normalized_python_sha256(left) == normalized_python_sha256(renamed)
    assert normalized_python_sha256(left) != normalized_python_sha256(different)
    left_units = [item["structure_sha256"] for item in normalized_python_units(left)]
    assert left_units
    assert left_units == [item["structure_sha256"] for item in normalized_python_units(renamed)]


def test_record_order_is_nonsemantic_and_authority_tampering_is_rejected():
    seed, snapshot = load(SEED), load(SNAPSHOT)
    baseline = measure(seed, snapshot)
    reordered = copy.deepcopy(snapshot)
    reordered["repositories"].reverse()
    assert measure(seed, reordered) == baseline

    altered = copy.deepcopy(snapshot)
    altered["repositories"][0]["commit_sha"] = "0" * 40
    try:
        measure(seed, altered)
    except ValueError as error:
        assert str(error) == "snapshot:repository-authority"
    else:
        raise AssertionError("altered repository authority was accepted")


def test_extractor_never_executes_acquired_source():
    tree = ast.parse((ROOT / "scripts/build_github_duplication_pilot.py").read_text())
    forbidden = {"eval", "exec", "compile", "__import__"}
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert not forbidden & calls
    published = REPORT.read_text()
    assert "source_text" not in published
    assert "source_content" not in published
