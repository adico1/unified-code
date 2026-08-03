"""ROOT-authoritative verification-surface generation proofs."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from unified.verify_flow import audited_source_report_primitive

ROOT = Path(__file__).resolve().parents[1]
CHECKED = ROOT / "generated" / "verification_surface"
GENERATOR = ROOT / "bootstrap" / "verification_surface.py"
STAGE1_FIXED = "6d2b6ce26ee8e543f6d0a3d9fcbe121f0f1f9db2686327ce3ce2ea06b7782e34"
UEM_FIXED = "ef231c4615dd4fe9824e95f84e6e5ff9f202e152a3c5da4ff2bb910802ff5881"
DOC_TARGETS = (
    "README.md",
    "LAW.md",
    "SPEC.md",
    "UEM_SPEC.md",
    "docs/DEVELOPER_WORKFLOW.md",
)


def tree_bytes(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }


def stage1(tmp_path):
    output = tmp_path / "stage1"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "bootstrap" / "stage0.py"),
            "generate",
            "--contract",
            str(ROOT / "seed" / "stage0" / "TRUSTED_INPUTS.json"),
            "--input-root",
            str(ROOT),
            "--output",
            str(output),
        ],
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return output


def generate(stage1_root, output, obligation=None, project_docs=None):
    command = [
        sys.executable,
        str(GENERATOR),
        "--root-seed",
        str(ROOT / "seed" / "ROOT.seed.json"),
        "--stage1-framework",
        str(stage1_root / "framework" / "contract.json"),
        "--stage1-uem",
        str(stage1_root / "uem" / "contract.json"),
        "--uem-manifest",
        str(ROOT / "generated" / "uem_surface" / "uem-surface-manifest.json"),
        "--proof-graph",
        str(ROOT / "seed" / "verification" / "PROOF_GRAPH.json"),
        "--obligation",
        str(
            obligation
            or ROOT / "seed" / "verification" / "SYNTHETIC_OBLIGATION.json"
        ),
        "--source-root",
        str(ROOT),
        "--output",
        str(output),
    ]
    if project_docs is not None:
        command.extend(("--project-docs", str(project_docs)))
    return subprocess.run(command, capture_output=True, check=False)


def test_isolated_generation_is_byte_identical_and_preserves_prior_fixed_points(
    tmp_path,
):
    contracts = stage1(tmp_path)
    first = tmp_path / "surface-a"
    second = tmp_path / "surface-b"
    assert generate(contracts, first).returncode == 0
    assert generate(contracts, second).returncode == 0
    assert tree_bytes(first) == tree_bytes(second) == tree_bytes(CHECKED)
    manifest = json.loads((first / "verification-manifest.json").read_text())
    uem = json.loads(
        (
            ROOT / "generated" / "uem_surface" / "uem-surface-manifest.json"
        ).read_text()
    )
    assert manifest["fixed_point"]["verdict"] == "pass"
    assert manifest["tree_sha256"] == json.loads(
        (second / "verification-manifest.json").read_text()
    )["tree_sha256"]
    assert uem["tree_sha256"] == UEM_FIXED
    assert STAGE1_FIXED == (
        "6d2b6ce26ee8e543f6d0a3d9fcbe121f0f1f9db2686327ce3ce2ea06b7782e34"
    )


def test_generated_surface_proves_ten_depths_watchers_and_behavioral_mutations():
    manifest = json.loads((CHECKED / "verification-manifest.json").read_text())
    mutation = json.loads((CHECKED / "mutations" / "manifest.json").read_text())
    assert [item["depth"] for item in manifest["depths"]] == list(range(1, 11))
    assert len(manifest["watchers"]) == 10
    assert all(item["verdict"] == "pass" for item in manifest["watchers"])
    assert manifest["generated_mutations"] == manifest["mutations_detected"]
    assert all(item["behavioral"] for item in mutation["items"])
    report = audited_source_report_primitive(GENERATOR.read_text())
    assert report["explicit_conditional_nodes"] == 0
    assert report["explicit_loop_nodes"] == 0
    assert report["hidden_dispatch_nodes"] == 0


def test_renamed_obligation_requires_no_generator_vocabulary(tmp_path):
    contracts = stage1(tmp_path)
    renamed = tmp_path / "RENAMED.json"
    renamed.write_text(
        json.dumps(
            {
                "identity": "horizon-balance@9",
                "fields": ["horizon", "balance"],
                "evidence": ["horizon:observed", "balance:verified"],
                "relations": {
                    "valid": "balance equals declared horizon magnitude",
                    "invalid": "missing horizon remains invalid",
                    "boundary": "horizon source remains outside computation",
                    "temporal_event": "observation precedes verification",
                },
            }
        )
    )
    output = tmp_path / "renamed"
    completed = generate(contracts, output, obligation=renamed)
    assert completed.returncode == 0, completed.stderr
    original = json.loads((CHECKED / "verification-manifest.json").read_text())
    changed = json.loads((output / "verification-manifest.json").read_text())
    fields = (
        "canonical_fact_count",
        "generated_test_partitions",
        "generated_mutations",
        "mutations_detected",
        "goldens_verified",
        "documentation_claims_verified",
        "audit_obligations_verified",
    )
    assert {field: original[field] for field in fields} == {
        field: changed[field] for field in fields
    }
    source = GENERATOR.read_text().lower()
    assert not {"signal", "measure", "horizon", "balance"}.intersection(source)


def test_generated_region_tamper_is_refused_without_replacing_output(
    tmp_path,
):
    contracts = stage1(tmp_path)
    project = tmp_path / "project"
    for relative in DOC_TARGETS:
        destination = project / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    output = tmp_path / "surface"
    shutil.copytree(CHECKED, output)
    baseline = tree_bytes(output)
    readme = project / "README.md"
    readme.write_text(
        readme.read_text().replace(
            "Generated verification status", "tampered verification status", 1
        )
    )
    completed = generate(contracts, output, project_docs=project)
    result = json.loads(completed.stdout)
    assert completed.returncode != 0
    assert result["state"] == "invalid"
    assert "generated-region-tamper:README.md" in result["value"]["error"]
    assert tree_bytes(output) == baseline
