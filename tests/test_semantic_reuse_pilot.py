"""Exact assertions for the bounded semantic-reuse pilot."""

import ast
import copy
import json
from pathlib import Path

from scripts.build_semantic_reuse_pilot import REPORT, ROOT, SEED, validate


SEED_DOCUMENT = json.loads(SEED.read_text())
REPORT_DOCUMENT = json.loads(REPORT.read_text())


def test_three_independent_public_witnesses_are_exactly_equivalent_in_scope():
    report = validate(SEED_DOCUMENT, REPORT_DOCUMENT)
    assert len({item["repository"] for item in report["public_witnesses"]}) == 3
    assert {item["actual"] for item in report["public_witnesses"]} == {42}
    assert {item["classification"] for item in report["public_witnesses"]} == {"equivalent"}


def test_two_generated_products_reuse_the_behavior_without_semantic_compiler_change():
    report = validate(SEED_DOCUMENT, REPORT_DOCUMENT)
    assert len({item["identity"] for item in report["generated_projections"]}) == 2
    assert {item["actual"] for item in report["generated_projections"]} == {42}
    assert report["application_behavior_compiler_changes"] == 0
    for projection in report["generated_projections"]:
        assert projection["generated_file"]
        assert len(projection["generated_file_sha256"]) == 64


def test_claim_boundary_keeps_unmeasured_semantics_and_economics_unknown():
    unknown = set(REPORT_DOCUMENT["claim_boundary"]["unknown"])
    assert "equivalence outside the registered vector" in unknown
    assert "equivalent validation and error behavior" in unknown
    assert "historical implementation cost" in unknown
    assert "worldwide economic savings" in unknown
    assert "this pilot proves trillion-dollar savings" in REPORT_DOCUMENT["claim_boundary"]["prohibited"]


def test_report_contains_no_copied_source_or_third_party_runtime_dependency():
    serialized = json.dumps(REPORT_DOCUMENT)
    assert "source_text" not in serialized
    assert "source_content" not in serialized
    assert REPORT_DOCUMENT["source_code_published"] is False
    assert REPORT_DOCUMENT["third_party_runtime_dependencies"] == []


def test_identity_tampering_is_rejected_deterministically():
    altered = copy.deepcopy(REPORT_DOCUMENT)
    altered["public_witnesses"][0]["actual"] = 41
    for _attempt in range(2):
        try:
            validate(SEED_DOCUMENT, altered)
        except ValueError as error:
            assert str(error) == "report:sha256"
        else:
            raise AssertionError("tampered semantic report accepted")


def test_live_boundary_uses_only_standard_library_and_pinned_sources():
    source = (ROOT / "scripts/build_semantic_reuse_pilot.py").read_text()
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports |= {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert imports <= {
        "__future__", "argparse", "ast", "hashlib", "io", "json", "os",
        "pathlib", "re", "subprocess", "sys", "tarfile", "types", "urllib"
    }
    assert all(item["commit_sha"] for item in SEED_DOCUMENT["public_witnesses"])
    assert all(item["selected_ast_sha256"] for item in SEED_DOCUMENT["public_witnesses"])
