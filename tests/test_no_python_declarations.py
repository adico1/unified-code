"""Enforcement gate for gap.declarations-as-python (Standard Ten rule 4).

Canonical JSON is the sole authoritative declaration input. Executable Python
declarations survive only as explicitly opt-in legacy compatibility fixtures.
These checks fail if production ever regresses to:

  * executing a host-code (.py) declaration on the default path,
  * falling back from a missing .json declaration to a sibling .py,
  * shipping a non-JSON declaration in the canonical seed.

They are the standing regression guard the migration relies on: clean-room and
fixed-point proofs run with Python declaration loading disabled, so nothing here
may depend on UC_ALLOW_PY_DECLARATIONS being set.
"""

from __future__ import annotations

import json
from pathlib import Path

from unified import selftest

from unified.boundary import inward
from unified.generator.declaration import load_declaration_module

ROOT = Path(__file__).resolve().parents[1]
DECLS = ROOT / "examples" / "declarations"
SEED = ROOT / "seed" / "ROOT.seed.json"
CLEAN_ROOM = ROOT / "scripts" / "clean_room_ten.sh"


def test_python_declaration_denied_by_default(monkeypatch):
    """A .py declaration is refused when no opt-in is set — no execution."""
    monkeypatch.delenv("UC_ALLOW_PY_DECLARATIONS", raising=False)
    loaded = load_declaration_module(
        inward({"declaration_path": str(DECLS / "text_stats_program.py")})
    )
    assert loaded["state"] == "invalid"
    assert loaded["value"]["error"] == "python-declaration-denied"
    assert "load:python-declaration-denied" in loaded["evidence"]
    # It must never have reached execution/normalization of the module.
    assert "load:ok" not in loaded["evidence"]
    assert "declaration" not in loaded["value"]


def test_no_fallback_from_missing_json_to_sibling_python(monkeypatch):
    """A missing .json must fail as not-found, never load a sibling .py.

    text_stats_program.py exists next to a (non-existent) .json target; dispatch
    is purely by the requested suffix, so no fallback may pick up the .py.
    """
    monkeypatch.delenv("UC_ALLOW_PY_DECLARATIONS", raising=False)
    assert (DECLS / "text_stats_program.py").is_file()  # sibling exists
    target = DECLS / "text_stats_program__absent.json"
    assert not target.exists()
    loaded = load_declaration_module(inward({"declaration_path": str(target)}))
    assert loaded["state"] == "invalid"
    assert loaded["value"]["error"] == "declaration-not-found"
    assert "load:ok" not in loaded["evidence"]
    assert "declaration" not in loaded["value"]


def test_seed_declarations_are_all_json():
    """The canonical seed ships no executable-Python declaration."""
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    paths = [d.get("path", "") for d in seed.get("declarations") or ()]
    assert paths, "seed declares no declarations"
    assert all(p.endswith(".json") for p in paths), paths


def test_clean_room_does_not_enable_python_declarations():
    """Fixed-point / clean-room proof must run with Python loading disabled."""
    text = CLEAN_ROOM.read_text(encoding="utf-8")
    assert "UC_ALLOW_PY_DECLARATIONS=1" not in text
    assert "allow_python_declaration" not in text


@selftest.mark.parametrize(
    "stem", ["text_stats_v2", "invoice_total", "text_stats_program"]
)
def test_json_twin_is_authoritative_and_loads_without_optin(monkeypatch, stem):
    """Every maintained declaration has a canonical JSON form that loads clean."""
    monkeypatch.delenv("UC_ALLOW_PY_DECLARATIONS", raising=False)
    decl = DECLS / f"{stem}.json"
    assert decl.is_file(), f"missing canonical JSON for {stem}"
    loaded = load_declaration_module(inward({"declaration_path": str(decl)}))
    assert loaded["state"] == "formed", loaded["value"].get("error")
    assert loaded["value"]["kind"] in {"program", "feature"}
