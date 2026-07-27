"""Public seed-to-stateful-application contract."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UC = ROOT / ".venv" / "bin" / "uc"
SEED = ROOT / "seed" / "declarations" / "task_ledger.json"


def test_public_unfold_contract(tmp_path):
    output = tmp_path / "uc-task-ledger"
    result = subprocess.run(
        [
            str(UC),
            "unfold",
            "seed/declarations/task_ledger.json",
            "--output",
            str(output),
            "--verify",
            "--run",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    value = report["value"]
    assert report["state"] == "valid"
    assert value["install"] == "ok"
    assert value["run_result"]["restart_verified"] is True
    assert value["python_c_result"]["equal"] is True
    assert value["fixed_point"]["tree_sha256_a"] == value["fixed_point"]["tree_sha256_b"]
    assert not tuple(output.rglob("__pycache__"))
    assert not tuple(output.rglob("*.pyc"))


def test_seed_is_only_task_ledger_application_source():
    assert SEED.is_file()
    assert not (ROOT / "examples" / "seeds" / "task_ledger.py").exists()
    assert not (ROOT / "examples" / "seeds" / "task_ledger.json").exists()


def test_atomic_refusal_preserves_installed_output(tmp_path):
    output = tmp_path / "installed"
    output.mkdir()
    sentinel = output / "sentinel"
    sentinel.write_text("prior\n", encoding="utf-8")
    invalid_seed = tmp_path / "invalid.json"
    invalid_seed.write_text("{}\n", encoding="utf-8")
    result = subprocess.run(
        [
            str(UC),
            "unfold",
            str(invalid_seed),
            "--output",
            str(output),
            "--verify",
            "--run",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode != 0
    assert sentinel.read_text(encoding="utf-8") == "prior\n"
    assert tuple(output.iterdir()) == (sentinel,)


def test_installed_domain_and_composition_are_control_free():
    for path in (
        Path("/tmp/uc-task-ledger/uc_task_ledger/parts.py"),
        Path("/tmp/uc-task-ledger/uc_task_ledger/compose.py"),
    ):
        if not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Match, ast.IfExp)
        assert not any(isinstance(node, forbidden) for node in ast.walk(tree))
