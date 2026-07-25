"""Declaration-driven generation tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from unified.boundary import inward
from unified.generator import run_command
from unified.generator.declaration import load_declaration_file


DECL = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "declarations"
    / "text_stats_program.py"
)


def test_load_text_stats_program_declaration():
    loaded = load_declaration_file(DECL)
    assert loaded["ok"] is True
    assert loaded["kind"] == "program"
    assert loaded["declaration"]["package"] == "uc_text_stats"
    assert len(loaded["declaration"]["features"]) == 2


def test_uc_new_from_declaration_generates_runnable_app(tmp_path):
    result = run_command(
        inward(
            {
                "command": "new",
                "name": "uc-text-stats",
                "parent": str(tmp_path),
                "declaration": str(DECL),
            }
        )
    )
    assert result["state"] == "valid", result.get("evidence")
    assert "generate:new-plan-from-declaration" in result["evidence"]
    root = tmp_path / "uc-text-stats"
    assert (root / "uc_text_stats" / "parts.py").is_file()
    assert (root / "uc_text_stats" / "cli.py").is_file()
    assert (root / "uc_text_stats" / "boundary.py").is_file()
    parts = (root / "uc_text_stats" / "parts.py").read_text(encoding="utf-8")
    assert "def validate_text(" in parts
    assert "def calculate_stats(" in parts
    assert "unique_words" in parts
    assert 'evidence": (*thing["evidence"], "part:validate_text")' not in parts or "validate_text:ok" in parts

    env = {**dict(**__import__("os").environ), "PYTHONPATH": str(root)}
    sample = root / "sample.txt"
    sample.write_text("Go go GO", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "uc_text_stats", str(sample)],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert '"unique_words":1' in proc.stdout.replace(" ", "")

    proc_t = subprocess.run(
        [sys.executable, "-m", "pytest"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_t.returncode == 0, proc_t.stdout + proc_t.stderr


def test_stub_add_still_works_without_declaration(tmp_path):
    created = run_command(
        inward({"command": "new", "name": "stub-app", "parent": str(tmp_path)})
    )
    assert created["state"] == "valid"
    root = tmp_path / "stub-app"
    added = run_command(
        inward(
            {
                "command": "add",
                "name": "mark",
                "project_root": str(root),
            }
        )
    )
    assert added["state"] == "valid"
    assert "generate:add:mark" in added["evidence"]
