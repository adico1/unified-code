"""ROOT-authoritative UEM surface and independent-host generation proofs."""

from __future__ import annotations

import ast
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

from bootstrap.uem_surface import (
    TEN_WATCHERS,
    audited_render_primitive,
)
from generated.uem_surface.unified.machine import generated_surface
from unified.verify_flow import audited_source_report_primitive

ROOT = Path(__file__).resolve().parents[1]
CHECKED = ROOT / "generated" / "uem_surface"
FIXED_HASH = "6d2b6ce26ee8e543f6d0a3d9fcbe121f0f1f9db2686327ce3ce2ea06b7782e34"
PERMANENT_HOSTS = (
    ROOT / "unified" / "machine",
    ROOT / "c" / "core",
    ROOT / "c" / "host",
)


def tree_bytes(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }


def generate_stage1(tmp_path):
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


def isolated_generate(tmp_path, root_seed, stage1_uem, name):
    isolation = tmp_path / (name + "-isolation")
    isolation.mkdir()
    script = isolation / "uem_surface.py"
    seed = isolation / "ROOT.seed.json"
    contract = isolation / "uem.contract.json"
    shutil.copyfile(ROOT / "bootstrap" / "uem_surface.py", script)
    shutil.copyfile(root_seed, seed)
    shutil.copyfile(stage1_uem, contract)
    output = tmp_path / name
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--root-seed",
            str(seed),
            "--stage1-uem-contract",
            str(contract),
            "--output",
            str(output),
        ],
        cwd=isolation,
        env={"PATH": "", "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return output


def test_root_to_stage1_to_independent_hosts_is_clean_room_fixed_point(tmp_path):
    stage1 = generate_stage1(tmp_path)
    first = isolated_generate(
        tmp_path,
        ROOT / "seed" / "ROOT.seed.json",
        stage1 / "uem" / "contract.json",
        "surface-a",
    )
    second = isolated_generate(
        tmp_path,
        ROOT / "seed" / "ROOT.seed.json",
        stage1 / "uem" / "contract.json",
        "surface-b",
    )
    assert tree_bytes(first) == tree_bytes(second) == tree_bytes(CHECKED)
    manifest = json.loads((first / "uem-surface-manifest.json").read_text())
    assert manifest["tree_sha256"] == "ef231c4615dd4fe9824e95f84e6e5ff9f202e152a3c5da4ff2bb910802ff5881"
    assert manifest["independent_hosts"] == {
        "python": "unified.machine.host",
        "c": "c/core",
        "oracle_relation": "none",
    }
    assert [item["depth"] for item in manifest["watchers"]] == list(range(1, 11))
    assert [item["watcher"] for item in manifest["watchers"]] == list(TEN_WATCHERS)
    assert all(item["verdict"] == "pass" for item in manifest["watchers"])


def test_generated_flow_has_no_public_control_and_no_application_vocabulary():
    manifest = json.loads((CHECKED / "uem-surface-manifest.json").read_text())
    assert manifest["control_flow"]["generated_public_conditionals"] == 0
    assert manifest["control_flow"]["generated_public_loops"] == 0
    vocabulary = set()
    for seed_path in sorted((ROOT / "seed" / "applications").glob("*.json")):
        seed = json.loads(seed_path.read_text())
        if "application" not in seed:
            continue
        vocabulary.update(
            (
                seed["application"]["name"],
                seed["application"]["package"],
            )
        )
    for seed_path in sorted((ROOT / "seed" / "declarations").glob("*.json")):
        seed = json.loads(seed_path.read_text())
        application = seed.get("application") or {}
        vocabulary.update(
            item
            for item in (application.get("name"), application.get("package"))
            if item
        )
    complete = "\n".join(
        (
            (ROOT / "bootstrap" / "uem_surface.py").read_text(),
            *(
                path.read_text(errors="replace")
                for path in CHECKED.rglob("*")
                if path.is_file()
            ),
            *(
                path.read_text(errors="replace")
                for root in PERMANENT_HOSTS
                for path in root.rglob("*")
                if path.is_file() and path.suffix in (".c", ".h", ".py")
            ),
        )
    ).lower()
    assert not vocabulary.intersection(complete)
    source = (ROOT / "bootstrap" / "uem_surface.py").read_text()
    report = audited_source_report_primitive(source)
    assert report["explicit_conditional_nodes"] == 0
    assert report["explicit_loop_nodes"] == 0
    assert report["hidden_dispatch_nodes"] == 0
    assert report["polling_nodes"] == 0


def test_generated_registries_and_vectors_are_complete_and_consumed():
    opcodes = json.loads((CHECKED / "registry" / "opcodes.json").read_text())
    primitives = json.loads((CHECKED / "registry" / "primitives.json").read_text())
    vectors = json.loads((CHECKED / "vectors" / "l11-surface.json").read_text())
    c_surface = (CHECKED / "c" / "include" / "uem_generated_surface.h").read_text()
    assert generated_surface.OPCODES == {
        item["code"]: item["name"] for item in opcodes["opcodes"]
    }
    assert generated_surface.PRIMITIVES == tuple(primitives["primitives"])
    assert all(
        f"#define UEM_OPCODE_{item['name']} {item['code']}u" in c_surface
        for item in opcodes["opcodes"]
    )
    assert len(vectors["vectors"]) == (
        len(opcodes["opcodes"]) + len(primitives["primitives"]) + 4
    )
    assert {
        item["id"]
        for item in vectors["vectors"]
        if item["kind"] == "rejection-equivalence"
    } == {
        "reject:unknown-opcode",
        "reject:unknown-primitive",
        "reject:unknown-version",
        "reject:noncanonical-encoding",
    }


def test_python_and_c_surfaces_are_seed_traced_and_mutation_sensitive(tmp_path):
    root_seed = json.loads((ROOT / "seed" / "ROOT.seed.json").read_text())
    uem = root_seed["stage1"]["uem"]
    files, manifest = audited_render_primitive(root_seed, uem)
    assert files["unified/machine/generated_surface.py"] == (
        CHECKED / "unified" / "machine" / "generated_surface.py"
    ).read_bytes()
    assert files["c/include/uem_generated_surface.h"] == (
        CHECKED / "c" / "include" / "uem_generated_surface.h"
    ).read_bytes()
    python_mutation = dict(files)
    python_mutation["unified/machine/generated_surface.py"] += b"\nOPCODES = {}\n"
    c_mutation = dict(files)
    c_mutation["c/include/uem_generated_surface.h"] += b"\n#define UEM_FORMAT_VERSION 99\n"
    assert python_mutation["unified/machine/generated_surface.py"] != files[
        "unified/machine/generated_surface.py"
    ]
    assert c_mutation["c/include/uem_generated_surface.h"] != files[
        "c/include/uem_generated_surface.h"
    ]
    assert manifest["authority"]["stage1_uem_sha256"] == (
        json.loads((CHECKED / "uem-surface-manifest.json").read_text())["authority"][
            "stage1_uem_sha256"
        ]
    )


def test_generated_public_hosts_are_one_thing_and_independent():
    python_path = CHECKED / "unified" / "machine" / "generated_host.py"
    syntax = ast.parse(python_path.read_text())
    public = next(
        item for item in syntax.body if isinstance(item, ast.FunctionDef)
    )
    assert public.name == "run"
    assert len(public.args.args) == 1
    assert "c/" not in python_path.read_text().lower()
    c_source = (
        CHECKED / "c" / "host" / "generated" / "uem_generated_host.c"
    ).read_text()
    public_c = c_source.split(
        "uem_generated_thing *uem_generated_host(uem_generated_thing *thing) {", 1
    )[1]
    assert all(token not in public_c for token in ("if (", "for (", "while ("))
    assert "python" not in c_source.lower()


def test_target_adapters_make_no_unverified_support_claim():
    targets = [
        json.loads(path.read_text())
        for path in sorted((CHECKED / "targets").glob("*.json"))
    ]
    assert targets
    assert all(target["status"] == "declared-unverified" for target in targets)
    assert all(target["support_claim"] is False for target in targets)
    physical = json.loads(
        (ROOT / "c" / "targets" / "manifests" / "l12_report_x86_64.json").read_text()
    )
    statuses = {item["status"] for item in physical["targets"]}
    assert "native-pass" in statuses
    assert "unavailable" in statuses
    assert "compile-only" in statuses


def test_existing_stage1_fixed_point_identity_is_unchanged(tmp_path):
    specification = importlib.util.spec_from_file_location(
        "fixed", ROOT / "bootstrap" / "fixed_point.py"
    )
    fixed = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(fixed)
    result = fixed.prove_stage1_fixed_point(
        {
            "value": {
                "stage0_path": str(ROOT / "bootstrap" / "stage0.py"),
                "contract_path": str(
                    ROOT / "seed" / "stage0" / "TRUSTED_INPUTS.json"
                ),
                "input_root": str(ROOT),
                "output": str(tmp_path / "fixed"),
            },
            "depths": (),
            "axes": (),
            "evidence": (),
            "state": "formed",
        }
    )
    assert result["state"] == "valid"
    assert result["value"]["tree_sha256_a"] == result["value"]["tree_sha256_b"]
    assert result["value"]["tree_sha256_a"] == FIXED_HASH
