"""Standard Ten governing contract — gap only, no conventional fallback."""

from __future__ import annotations

from pathlib import Path

from unified.standard import (
    STANDARD_VERSION,
    load_seed,
    make_stamp,
    refuse_conventional,
    standard_gap,
)
from unified.standard_generate import (
    generate_all_seed_declarations,
    load_declaration_json,
    request_feature,
)

ROOT = Path(__file__).resolve().parents[1]


def test_standard_ten_md_exists():
    text = (ROOT / "STANDARD_TEN.md").read_text(encoding="utf-8")
    assert "One Thing" in text
    assert "Conventional development is not an authorized fallback" in text
    assert "standard.gap" in text


def test_seed_loads():
    r = load_seed(
        {"value": {}, "depths": (), "axes": (), "evidence": (), "state": "formed"}
    )
    assert r["state"] == "formed"
    assert r["value"]["seed"]["standard_version"] == STANDARD_VERSION
    assert r["value"]["seed"]["standard_ten"] is True
    assert len(r["value"]["seed_sha256"]) == 64


def test_standard_gap_opens_ticket():
    g = standard_gap(
        {
            "value": {
                "gap_id": "gap.unit",
                "rule": "5",
                "summary": "no OOP",
                "paths": ["x.py"],
            },
            "depths": (),
            "axes": (),
            "evidence": (),
            "state": "formed",
        }
    )
    assert g["state"] == "invalid"
    assert "standard.gap" in g["evidence"]
    assert g["value"]["gap"]["kind"] == "standard.gap"
    assert g["value"]["ticket"]["kind"] == "standard.gap"
    assert g["value"]["error"] == "standard.gap"


def test_refuse_conventional():
    r = refuse_conventional(
        {
            "value": {"summary": "add a class hierarchy"},
            "depths": (),
            "axes": (),
            "evidence": (),
            "state": "formed",
        }
    )
    assert r["state"] == "invalid"
    assert "standard.gap" in r["evidence"]


def test_unsupported_feature_is_gap_not_impl():
    r = request_feature(
        {
            "value": {"kind": "rest_api_framework"},
            "depths": (),
            "axes": (),
            "evidence": (),
            "state": "formed",
        }
    )
    assert r["state"] == "invalid"
    assert r["value"]["error"] == "standard.gap"


def test_load_seed_declaration_json():
    path = ROOT / "seed" / "declarations" / "text_stats_v2.json"
    r = load_declaration_json(
        {
            "value": {"declaration_path": str(path)},
            "depths": (),
            "axes": (),
            "evidence": (),
            "state": "formed",
        }
    )
    assert r["state"] == "formed"
    assert "features" in r["value"]["declaration"]
    assert len(r["value"]["declaration_sha256"]) == 64


def test_generate_uem_from_seed():
    r = generate_all_seed_declarations()
    assert r["state"] == "formed"
    gens = r["value"]["generated"]
    assert len(gens) >= 2
    for g in gens:
        assert g["state"] == "formed"
        out = Path(g["out_dir"])
        assert (out / "program.uem").is_file()
        assert (out / "program.uem.stamp.json").is_file()


def test_stamp_fields():
    t = make_stamp(
        {
            "value": {
                "seed_sha256": "a" * 64,
                "generator_sha256": "b" * 64,
                "declaration_sha256": "c" * 64,
                "artifact_bytes": b"hello",
            },
            "depths": (),
            "axes": (),
            "evidence": (),
            "state": "formed",
        }
    )
    s = t["value"]["stamp"]
    assert s["standard_version"] == STANDARD_VERSION
    assert s["artifact_sha256"]
    assert s["seed_sha256"] == "a" * 64
