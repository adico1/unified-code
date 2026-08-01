"""Regression gauntlet for semantic convergence instead of additive wrapping."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from unified.generator import assembly
from unified.generator.application_language import declaration_compiler
from unified.generator.application_language.tooling import build_layout
from unified.generator.cli import _parse_argv
from unified import verify_flow


ROOT = Path(__file__).resolve().parents[1]
APPLICATION_LANGUAGE = ROOT / "unified" / "generator" / "application_language"
SEED_ROOT = ROOT / "seed" / "application_language"


def test_provenance_counts_are_measured_instead_of_declared_as_zero():
    compiler = (APPLICATION_LANGUAGE / "seed_compiler.py").read_text(
        encoding="utf-8"
    )
    verifier = (
        APPLICATION_LANGUAGE / "tooling" / "verify_all.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        '"manual_application_files": 0',
        '"manual_test_files": 0',
        '"manual_application_code": 0',
        '"manual_application_tests": 0',
    )
    assert not [token for token in forbidden if token in compiler + verifier]


def test_anti_overfitting_covers_every_permanent_application_surface():
    surfaces = {
        *APPLICATION_LANGUAGE.rglob("*.py"),
        ROOT / "unified" / "generator" / "assembly.py",
        ROOT / "unified" / "generator" / "manifestation.py",
    }
    forbidden = {
        "calculator",
        "todo",
        "pong",
        "paddle",
        "financial",
        "scientific",
        "dashboard",
    }
    hits = {
        (path.relative_to(ROOT).as_posix(), word)
        for path in surfaces
        for word in forbidden
        if word in path.read_text(encoding="utf-8").casefold()
    }
    assert not hits


def test_application_language_has_one_registered_compilation_language():
    assert declaration_compiler.LANGUAGES == (
        "unified-application-declaration-1",
    )


def test_product_source_and_application_do_not_duplicate_bytes(tmp_path):
    leaf = {
        "what": {
            "identity": {
                "canonical": "uc://applications/alignment-probe@1",
                "family": "probe",
                "variation": "alignment-probe",
                "version": 1,
            }
        }
    }
    files = {
        "main.py": b"VALUE = 1\n",
        "test_generated.py": b"def run(): return True\n",
        "traceability.json": b"{}\n",
        "manifest.json": b"{}\n",
    }
    _identity, paths = build_layout.classify(
        tmp_path, leaf, leaf, files, "probes"
    )
    source = paths["source"]
    application = paths["product"] / "main.py"
    assert not (source.exists() and application.exists()) or os.path.samefile(
        source, application
    )


def test_public_projection_moves_runtime_out_of_private_metadata(tmp_path):
    staging = tmp_path / "build"
    metadata = staging / ".unified"
    internal = (
        metadata
        / "application-language"
        / "calculators"
        / "alignment-probe@1"
        / "application"
    )
    internal.mkdir(parents=True)
    (internal / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
    catalog = {
        "applications": [
            {
                "id": "alignment-probe",
                "canonical_identity": "uc://applications/alignment-probe@1",
                "build_group": "calculators",
                "seed": "build/calculators/alignment-probe@1/authority/seed.json",
                "paths": {
                    "application": "build/calculators/alignment-probe@1/application"
                },
            }
        ]
    }
    assembly._public_product_index(
        staging, metadata, [], {}, {}, catalog
    )
    public = (
        staging
        / "calculators"
        / "alignment-probe@1"
        / "application"
        / "main.py"
    )
    assert public.is_file()
    assert not list(metadata.rglob("main.py"))


def test_assembly_cache_does_not_copy_the_complete_output_tree(
    tmp_path, monkeypatch
):
    output = tmp_path / "output"
    output.mkdir()
    (output / "artifact.txt").write_text("artifact", encoding="utf-8")
    monkeypatch.setattr(assembly.tempfile, "tempdir", str(tmp_path))
    assembly._ASSEMBLY_PROOF_CACHE.clear()
    assembly.audited_assembly_cache_publish_boundary("probe", output, {})
    assert not list(tmp_path.glob("uc-assembly-cache-*"))
    assert all(
        "tree" not in record and "owner" not in record
        for record in assembly._ASSEMBLY_PROOF_CACHE.values()
    )


def test_assembly_cache_retains_each_distinct_authority(tmp_path):
    assembly._ASSEMBLY_PROOF_CACHE.clear()
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "artifact.txt").write_text("first", encoding="utf-8")
    (second / "artifact.txt").write_text("second", encoding="utf-8")

    assembly.audited_assembly_cache_publish_boundary("authority-a", first, {})
    assembly.audited_assembly_cache_publish_boundary("authority-b", second, {})

    assert set(assembly._ASSEMBLY_PROOF_CACHE) == {
        "authority-a",
        "authority-b",
    }
    assert assembly._ASSEMBLY_PROOF_CACHE["authority-a"]["output"] == str(first)
    assert assembly._ASSEMBLY_PROOF_CACHE["authority-b"]["output"] == str(second)


def test_generated_application_tests_use_one_self_test_process():
    runner = assembly._run_generated_tests
    source = Path(assembly.__file__).read_text(encoding="utf-8")
    runner_source = source[
        source.index("def _run_generated_tests") : source.index(
            "\ndef _execute_acceptance", source.index("def _run_generated_tests")
        )
    ]
    assert runner.__code__.co_argcount == 1
    assert '"pytest"' not in runner_source
    generated = assembly._generated_test_source("probe_package", None)
    assert "def run():" in generated
    assert "if __name__ == \"__main__\":" in generated


def test_physical_evidence_nodes_execute_concurrently(tmp_path, monkeypatch):
    def slow(node):
        time.sleep(0.15)
        return {"id": node["id"], "returncode": 0}

    graph = {
        "evidence_nodes": [
            {"id": f"evidence-{index}", "handler": "alignment-slow"}
            for index in range(4)
        ],
        "proof_nodes": [
            {"id": f"proof-{index}", "requires": [f"evidence-{index}"]}
            for index in range(4)
        ],
    }
    monkeypatch.setitem(verify_flow.HANDLER_REGISTRY, "alignment-slow", slow)
    monkeypatch.setattr(
        verify_flow, "BUNDLE", tmp_path / "PROOF_BUNDLE.json"
    )
    started = time.monotonic()
    bundle = verify_flow.audited_materialize_bundle_primitive(
        graph, {"identity": "probe", "file_count": 0}
    )
    elapsed = time.monotonic() - started
    assert elapsed < 0.4
    assert bundle["evidence_workers"] == 4
    assert all(item["status"] == "pass" for item in bundle["verdicts"])


def test_missing_checked_registry_is_not_a_seed_generation_blocker(tmp_path):
    seed_root = tmp_path / "seed"
    seed_root.mkdir()
    registry, error = assembly.audited_registry_authority_boundary(tmp_path)
    assert error is None
    assert registry["records"] == []


def test_registry_materialization_is_not_hidden_behind_an_environment_flag():
    source = Path(assembly.__file__).read_text(encoding="utf-8")
    assert "UC_REGISTRY_MATERIALIZE" not in source


def test_derived_catalog_patches_contain_only_differences_from_their_bases():
    missing = object()

    def redundant_paths(base, patch, path=()):
        if not isinstance(patch, dict):
            return [path] if patch == base else []
        source = base if isinstance(base, dict) else {}
        return [
            found
            for key, value in patch.items()
            for found in redundant_paths(source.get(key, missing), value, path + (key,))
        ]

    catalog = json.loads(
        (SEED_ROOT / "catalog.seed.json").read_text(encoding="utf-8")
    )
    redundant = []
    for family in catalog["families"]:
        for profile in family["profiles"]:
            if "derivation" not in profile:
                continue
            derivation = profile["derivation"]
            prototype = json.loads(
                (SEED_ROOT / derivation["prototype"]["path"]).read_text(
                    encoding="utf-8"
                )
            )
            redundant.extend(
                (profile["identity"], ".".join(path))
                for path in redundant_paths(prototype, derivation["patch"])
            )
    assert not redundant


def test_repository_tests_do_not_install_a_global_tmp_path_cleanup_policy():
    conftest = ROOT / "tests" / "conftest.py"
    source = conftest.read_text(encoding="utf-8") if conftest.exists() else ""
    assert "autouse=True" not in source


def test_isolated_python_boundaries_preserve_declared_tool_dependencies():
    sources = (
        Path(verify_flow.__file__).read_text(encoding="utf-8"),
        (ROOT / "unified" / "generator" / "gauntlet.py").read_text(
            encoding="utf-8"
        ),
    )
    assert all('os.environ.get("PYTHONPATH", "")' in source for source in sources)


def test_existing_single_public_assembly_api_is_preserved():
    parsed = _parse_argv(
        [
            "assemble",
            "seed/application_suite.json",
            "--output",
            "build",
            "--build",
            "--install",
            "--verify",
            "--gauntlet-depths",
            "10",
        ]
    )
    assert parsed == {
        "command": "assemble",
        "suite_path": "seed/application_suite.json",
        "output": "build",
        "build": True,
        "install": True,
        "verify": True,
        "gauntlet_depths": 10,
    }
