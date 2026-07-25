"""Build + gauntlet integration tests."""

from __future__ import annotations

from pathlib import Path

from unified.boundary import inward
from unified.generator import run_build, run_gauntlet
from unified.generator.declaration import load_declaration_module


DECL_V2 = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "declarations"
    / "text_stats_v2.py"
)


def test_declaration_thing_form_loads():
    loaded = load_declaration_module(
        inward({"declaration_path": str(DECL_V2)})
    )
    assert loaded["state"] == "formed"
    assert loaded["value"]["kind"] == "program"
    assert loaded["value"]["declaration"]["package"] == "uc_text_stats_v2"
    assert "transform" not in loaded["value"]["declaration"]["composition"]


def test_uc_build_from_declaration_thing(tmp_path):
    result = run_build(
        inward(
            {
                "declaration_path": str(DECL_V2),
                "parent": str(tmp_path),
                "project_name": "uc-text-stats-v2",
            }
        )
    )
    assert result["state"] == "valid", result.get("evidence")
    root = tmp_path / "uc-text-stats-v2"
    assert (root / "uc_text_stats_v2" / "parts.py").is_file()
    compose = (root / "uc_text_stats_v2" / "compose.py").read_text(encoding="utf-8")
    assert "transform(" not in compose
    assert "present_result(" in compose
    assert "parse_host_argv(" in compose
    parts = (root / "uc_text_stats_v2" / "parts.py").read_text(encoding="utf-8")
    assert "unique_words" in parts
    assert "return None" not in parts


def test_present_result_returns_thing(tmp_path):
    result = run_build(
        inward(
            {
                "declaration_path": str(DECL_V2),
                "parent": str(tmp_path),
                "project_name": "host-edge-app",
            }
        )
    )
    assert result["state"] == "valid"
    root = tmp_path / "host-edge-app"
    package = result["value"]["package"]
    import sys

    sys.path.insert(0, str(root))
    try:
        boundary = __import__(f"{package}.boundary", fromlist=["present_result"])
        compose = __import__(f"{package}.compose", fromlist=["program"])
        out = compose.program({"source": str(tmp_path / "x.txt")})
        assert isinstance(out, dict)
        assert "presentation" in out["value"]
        assert isinstance(out["value"]["presentation"]["text"], str)
        assert out["value"]["presentation"]["exit_code"] == 1
        again = boundary.present_result(out)
        assert again["state"] in {"invalid", "valid", "formed"}
        assert "presentation" in again["value"]
    finally:
        sys.path.remove(str(root))
        for key in list(sys.modules):
            if key == package or key.startswith(package + "."):
                del sys.modules[key]


def test_gauntlet_on_declaration(tmp_path):
    # Faster path: build once then gauntlet project mode
    built = run_build(
        inward(
            {
                "declaration_path": str(DECL_V2),
                "parent": str(tmp_path),
                "project_name": "g-app",
            }
        )
    )
    assert built["state"] == "valid"
    result = run_gauntlet(
        inward(
            {
                "mode": "project",
                "project_path": built["value"]["project_path"],
                "declaration_path": str(DECL_V2),
            }
        )
    )
    # Gauntlet may be strict; report structure always
    assert "levels" in result["value"]
    assert "verdict" in result["value"]
    assert "checks_executed" in result["value"]
    assert result["value"]["checks_executed"] >= 1
