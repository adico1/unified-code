"""Public seed-to-stateful-application contract."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UC = ROOT / ".venv" / "bin" / "uc"
SEED = ROOT / "seed" / "declarations" / "task_ledger.json"
SECOND_SEED = ROOT / "seed" / "declarations" / "score_board.json"


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


def test_stateful_seeds_are_the_only_application_sources():
    assert SEED.is_file()
    assert SECOND_SEED.is_file()
    assert not (ROOT / "examples" / "seeds" / "task_ledger.py").exists()
    assert not (ROOT / "examples" / "seeds" / "task_ledger.json").exists()


def test_second_stateful_application_uses_independent_vocabulary(tmp_path):
    output = tmp_path / "uc-score-board"
    result = subprocess.run(
        [
            str(UC),
            "unfold",
            "seed/declarations/score_board.json",
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
    value = json.loads(result.stdout)["value"]
    assert value["run_result"]["outputs"] == [
        {"argv": ["register", "Ada"], "exit": 0, "output": {"name": "Ada", "points": 0}},
        {"argv": ["award", "Ada", "3"], "exit": 0, "output": {"name": "Ada", "points": 3}},
        {
            "argv": ["standings"],
            "exit": 0,
            "output": {"players": [{"name": "Ada", "points": 3}]},
        },
        {
            "argv": ["standings"],
            "exit": 0,
            "output": {"players": [{"name": "Ada", "points": 3}]},
        },
    ]
    assert value["run_result"]["restart_verified"] is True
    assert value["python_c_result"]["equal"] is True
    assert value["fixed_point"]["tree_sha256_a"] == value["fixed_point"]["tree_sha256_b"]


def test_generic_generator_has_no_application_vocabulary():
    result = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), "scripts/check_stateful_overfit.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_anti_overfitting_scan_detects_injected_vocabulary(tmp_path):
    source = tmp_path / "generator"
    source.mkdir()
    (source / "generic.py").write_text('DOMAIN = "task-not-open"\n', encoding="utf-8")
    result = subprocess.run(
        [
            str(ROOT / ".venv" / "bin" / "python"),
            "scripts/check_stateful_overfit.py",
            str(source),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "task-not-open" in result.stdout


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
