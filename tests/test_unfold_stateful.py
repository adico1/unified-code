"""Public seed-to-stateful-application contract."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UC = (sys.executable, "-m", "unified.generator.cli")
SEED = ROOT / "seed" / "declarations" / "task_ledger.json"
SECOND_SEED = ROOT / "seed" / "declarations" / "score_board.json"


def test_public_unfold_contract(tmp_path):
    output = tmp_path / "uc-task-ledger"
    result = subprocess.run(
        [
            *UC,
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
    assert value["python_c_result"]["application_equal"] is True
    assert value["python_c_result"]["final_state_equal"] is True
    assert all(
        step["equal"] and step["application_equal"]
        for step in value["python_c_result"]["steps"]
    )
    assert [
        item["output"]
        for item in value["run_result"]["outputs"]
        if item["exit"] != 0
    ] == [
        {"error": "duplicate-title", "state": "invalid"},
        {"error": "task-not-open", "state": "invalid"},
    ]
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
            *UC,
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
        {
            "argv": ["register", "Ada"],
            "exit": 1,
            "output": {"error": "duplicate-player", "state": "invalid"},
        },
        {
            "argv": ["standings"],
            "exit": 0,
            "output": {"players": [{"name": "Ada", "points": 0}]},
        },
        {"argv": ["award", "Ada", "3"], "exit": 0, "output": {"name": "Ada", "points": 3}},
        {
            "argv": ["award", "Grace", "1"],
            "exit": 1,
            "output": {"error": "unknown-player", "state": "invalid"},
        },
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
    assert value["python_c_result"]["application_equal"] is True
    assert value["python_c_result"]["final_state_equal"] is True
    assert all(
        step["equal"] and step["application_equal"]
        for step in value["python_c_result"]["steps"]
    )
    assert value["fixed_point"]["tree_sha256_a"] == value["fixed_point"]["tree_sha256_b"]


def test_generic_generator_has_no_application_vocabulary():
    result = subprocess.run(
        [sys.executable, "-m", "scripts.check_stateful_overfit"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_anti_overfitting_scan_detects_injected_vocabulary(tmp_path):
    from unified.generator.overfit import (
        derive_application_vocabulary,
        vocabulary_hits,
    )

    source = tmp_path / "generator"
    source.mkdir()
    injected = source / "generic.py"
    seeds = (SEED, SECOND_SEED)
    vocabulary = derive_application_vocabulary(seeds)
    assert {
        "add",
        "duplicate-title",
        "task-not-open",
        "duplicate-player",
        "unknown-player",
    } <= set(vocabulary)
    assert vocabulary["add"] == "stateful-command"
    for term, mode in vocabulary.items():
        injected = source / (
            "stateful.py" if mode == "stateful-command" else "generic.py"
        )
        mutation = (
            f'if command == "{term}":\n    pass\n'
            if mode == "stateful-command"
            else f'DOMAIN = "{term}"\n'
        )
        injected.write_text(mutation, encoding="utf-8")
        assert any(
            token == term
            for _, token in vocabulary_hits((source,), seeds, display_root=ROOT)
        )


def test_contextual_add_command_mutation_is_detected_but_expression_is_allowed(
    tmp_path,
):
    from unified.generator.overfit import vocabulary_hits

    seeds = (SEED, SECOND_SEED)
    source = tmp_path / "generic"
    source.mkdir()
    stateful = source / "stateful.py"
    c_stateful = source / "stateful.c"
    expression = source / "expr.py"
    stateful.write_text('if command == "add":\n    pass\n', encoding="utf-8")
    c_stateful.write_text(
        'if (strcmp(command, "add") == 0) { return; }\n',
        encoding="utf-8",
    )
    expression.write_text('EXPRESSION_OPERATORS = {"add"}\n', encoding="utf-8")
    hits = vocabulary_hits((source,), seeds, display_root=ROOT)
    assert any(path.endswith("stateful.py") and term == "add" for path, term in hits)
    assert any(path.endswith("stateful.c") and term == "add" for path, term in hits)
    assert not any(path.endswith("expr.py") and term == "add" for path, term in hits)


def test_atomic_refusal_preserves_installed_output(tmp_path):
    output = tmp_path / "installed"
    output.mkdir()
    sentinel = output / "sentinel"
    sentinel.write_text("prior\n", encoding="utf-8")
    invalid_seed = tmp_path / "invalid.json"
    invalid_seed.write_text("{}\n", encoding="utf-8")
    result = subprocess.run(
        [
            *UC,
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
