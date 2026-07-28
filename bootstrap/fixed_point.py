"""Isolated byte-identical Stage-1 fixed-point proof."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FORMAT_VERSION = "UC-STAGE1-FIXED-POINT-1"
STAGE1_FILES = (
    "framework/contract.json",
    "generator/contract.json",
    "stage1-manifest.json",
    "stage1.py",
    "uem/contract.json",
)


def _canonical(value):
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _inventory(root):
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": _sha(path.read_bytes()),
            "size": path.stat().st_size,
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def _tree_sha256(inventory):
    return _sha(
        "".join(
            item["path"] + "\0" + item["sha256"] + "\n"
            for item in sorted(inventory, key=lambda item: item["path"])
        ).encode("utf-8")
    )


def compare_stage1_trees(first, second):
    """Return complete byte-level comparison evidence for two Stage-1 trees."""
    first = Path(first)
    second = Path(second)
    inventory_a = _inventory(first)
    inventory_b = _inventory(second)
    paths_a = [item["path"] for item in inventory_a]
    paths_b = [item["path"] for item in inventory_b]
    mismatches = []
    for path in sorted(set(paths_a) & set(paths_b)):
        raw_a = (first / path).read_bytes()
        raw_b = (second / path).read_bytes()
        if raw_a != raw_b:
            limit = min(len(raw_a), len(raw_b))
            offset = next(
                (index for index in range(limit) if raw_a[index] != raw_b[index]),
                limit,
            )
            mismatches.append(
                {
                    "path": path,
                    "first_differing_byte": offset,
                    "sha256_a": _sha(raw_a),
                    "sha256_b": _sha(raw_b),
                    "size_a": len(raw_a),
                    "size_b": len(raw_b),
                }
            )
    tree_a = _tree_sha256(inventory_a)
    tree_b = _tree_sha256(inventory_b)
    return {
        "inventory_a": inventory_a,
        "inventory_b": inventory_b,
        "missing_from_a": sorted(set(paths_b) - set(paths_a)),
        "missing_from_b": sorted(set(paths_a) - set(paths_b)),
        "mismatches": mismatches,
        "tree_sha256_a": tree_a,
        "tree_sha256_b": tree_b,
        "byte_identical": (
            paths_a == paths_b and not mismatches and tree_a == tree_b
        ),
    }


def _environment():
    return {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "PYTHONDONTWRITEBYTECODE": "1",
        "SOURCE_DATE_EPOCH": "0",
    }


def _run(command, cwd):
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=_environment(),
        capture_output=True,
        check=False,
    )
    try:
        result = json.loads(completed.stdout)
    except (UnicodeError, ValueError):
        result = {"state": "invalid", "value": {"error": "non-canonical-output"}}
    return completed, result


def _atomic_publish(stage, output):
    backup = output.parent / ("." + output.name + ".fixed-point-old")
    if backup.exists():
        shutil.rmtree(backup)
    if output.exists():
        output.rename(backup)
    try:
        stage.rename(output)
    except BaseException:
        if backup.exists() and not output.exists():
            backup.rename(output)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def _invalid(thing, error, evidence, details=None):
    return {
        **thing,
        "value": {
            **(thing.get("value") if isinstance(thing.get("value"), dict) else {}),
            "error": error,
            "fixed_point": False,
            **(details or {}),
        },
        "evidence": (*thing.get("evidence", ()), evidence),
        "state": "invalid",
    }


def prove_stage1_fixed_point(thing):
    """Public Part: Stage0(ROOT.seed) == Stage1-A(ROOT.seed)."""
    value = thing.get("value") if isinstance(thing, dict) else None
    required = {"stage0_path", "contract_path", "input_root", "output"}
    if not isinstance(value, dict) or set(value) != required:
        return _invalid(thing if isinstance(thing, dict) else {}, "contract", "fixed-point:rejected")
    stage0_path = Path(value["stage0_path"]).resolve()
    contract_path = Path(value["contract_path"]).resolve()
    input_root = Path(value["input_root"]).resolve()
    root_seed = input_root / "seed" / "ROOT.seed.json"
    output = Path(value["output"]).resolve()
    stage_parent = output.parent
    stage_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="." + output.name + ".fixed-point-new-", dir=stage_parent))
    try:
        stage1_a = stage / "stage1-a"
        first, first_result = _run(
            [
                sys.executable,
                str(stage0_path),
                "generate",
                "--contract",
                str(contract_path),
                "--input-root",
                str(input_root),
                "--output",
                str(stage1_a),
            ],
            stage,
        )
        if first.returncode or first_result.get("state") != "valid":
            raise ValueError("stage0-generation")
        isolated = stage / "stage1-isolation"
        isolated.mkdir()
        isolated_seed = isolated / "ROOT.seed.json"
        shutil.copyfile(root_seed, isolated_seed)
        stage1_b = stage / "stage1-b"
        second, second_result = _run(
            [
                sys.executable,
                str(stage1_a / "stage1.py"),
                str(isolated_seed),
                str(stage1_b),
            ],
            isolated,
        )
        if second.returncode or second_result.get("state") != "valid":
            raise ValueError("stage1-generation")
        comparison = compare_stage1_trees(stage1_a, stage1_b)
        if tuple(item["path"] for item in comparison["inventory_a"]) != STAGE1_FILES:
            raise ValueError("undeclared-inventory")
        if not comparison["byte_identical"]:
            diagnostic = output.parent / ("." + output.name + ".fixed-point-diagnostics.json")
            diagnostic.write_bytes(_canonical(comparison))
            shutil.rmtree(stage)
            return _invalid(
                thing,
                "stage1-fixed-point-mismatch",
                "fixed-point:mismatch",
                {"comparison": comparison, "diagnostics": str(diagnostic)},
            )
        report = {
            "format_version": FORMAT_VERSION,
            "authority": {
                "contract_sha256": _sha(contract_path.read_bytes()),
                "root_seed_sha256": _sha(root_seed.read_bytes()),
            },
            "producer_a": "trusted-stage0",
            "producer_b": "generated-stage1-a",
            **comparison,
            "fixed_point": True,
            "evidence": [
                "fixed-point:stage0-isolated",
                "fixed-point:stage1-a-generated",
                "fixed-point:stage1-a-isolated",
                "fixed-point:stage1-b-generated",
                "fixed-point:inventories-equal",
                "fixed-point:bytes-equal",
                "fixed-point:bilima",
            ],
        }
        (stage / "fixed-point-report.json").write_bytes(_canonical(report))
        shutil.rmtree(isolated)
        _atomic_publish(stage, output)
        return {
            **thing,
            "value": {
                **value,
                "error": None,
                "fixed_point": True,
                "tree_sha256_a": comparison["tree_sha256_a"],
                "tree_sha256_b": comparison["tree_sha256_b"],
                "report": str(output / "fixed-point-report.json"),
            },
            "evidence": (*thing.get("evidence", ()), *report["evidence"]),
            "state": "valid",
        }
    except (OSError, TypeError, ValueError) as error:
        if stage.exists():
            shutil.rmtree(stage)
        return _invalid(
            thing,
            "fixed-point:" + str(error),
            "fixed-point:rejected",
        )


def main(argv=None):
    args = list(sys.argv if argv is None else argv)
    if len(args) != 9 or args[1::2] != [
        "--stage0",
        "--contract",
        "--input-root",
        "--output",
    ]:
        result = _invalid(
            {"value": {}, "depths": (), "axes": (), "evidence": (), "state": "formed"},
            "usage",
            "fixed-point:cli-rejected",
        )
    else:
        result = prove_stage1_fixed_point(
            {
                "value": {
                    "stage0_path": args[2],
                    "contract_path": args[4],
                    "input_root": args[6],
                    "output": args[8],
                },
                "depths": (),
                "axes": (),
                "evidence": (),
                "state": "formed",
            }
        )
    sys.stdout.buffer.write(_canonical(result))
    return 0 if result["state"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
