"""Offline behavioral proof for the canonical public-repository fixture pack."""

from __future__ import annotations

import ast
import copy
import inspect
import json
from pathlib import Path

from unified.boundary import inward
from unified.github_corpus import (
    SNAPSHOT_VERSION,
    audited_fixture_page_payload_primitive,
    replay_fixture_pack,
)
from unified.machine.canonical import canonical_sha256


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "seed" / "github_corpus" / "fixtures"
MANIFEST = json.loads((FIXTURES / "PACK.json").read_text())
EXPECTED = json.loads((FIXTURES / "EXPECTED.json").read_text())
VECTORS = json.loads((FIXTURES / "REPLAY_VECTORS.json").read_text())
PAGE_TEXTS = {
    page["path"]: (FIXTURES / page["path"]).read_text()
    for page in MANIFEST["pages"]
}


def _replay(manifest=MANIFEST, page_texts=PAGE_TEXTS):
    return replay_fixture_pack(
        inward(
            {
                "fixture_pack": {
                    "manifest": copy.deepcopy(manifest),
                    "page_texts": copy.deepcopy(page_texts),
                }
            }
        )
    )


def _replace_page(manifest, page_texts, path, page):
    text = json.dumps(page, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    content_sha256 = canonical_sha256(
        audited_fixture_page_payload_primitive(page)
    )
    page_texts[path] = text
    declaration = next(item for item in manifest["pages"] if item["path"] == path)
    declaration["content_sha256"] = content_sha256


def test_fixture_pack_replays_offline_with_frozen_identities_and_metadata():
    result = _replay()
    assert result["state"] == "valid"
    assert result["evidence"] == (
        "boundary:inward",
        "corpus:fixture-replayed",
    )
    for identity in (
        "fixture_pack_sha256",
        "request_sha256",
        "snapshot_sha256",
        "evidence_sha256",
    ):
        assert result["value"][identity] == EXPECTED[identity]
    semantic = result["value"]["semantic_snapshot"]
    records = [
        record
        for page in semantic["pages"]
        for record in page["records"]
    ]
    assert len(records) == EXPECTED["record_count"]
    assert {
        str(page["index"]): [
            record["source_identity"] for record in page["records"]
        ]
        for page in semantic["pages"]
    } == VECTORS["valid"]["canonical_page_records"]
    assert all(
        record["payload"]["source_url"].startswith(
            "https://api.github.com/repos/"
        )
        for record in records
    )
    assert all(
        record["payload"]["license"]["spdx_id"] == "MIT"
        for record in records
    )
    assert all(record["payload"]["license"]["url"] for record in records)
    assert all(
        page["retrieval_contract_version"] == SNAPSHOT_VERSION
        and page["source_url"].startswith("https://api.github.com/")
        and page["content_sha256"] == EXPECTED["page_content_sha256"][page["path"]]
        for page in MANIFEST["pages"]
    )
    source = (ROOT / "unified" / "github_corpus.py").read_text()
    assert not any(
        name in source
        for name in ("import requests", "import socket", "import urllib")
    )


def test_page_record_and_dictionary_order_preserve_semantic_identity():
    baseline = _replay()
    manifest = copy.deepcopy(MANIFEST)
    page_texts = copy.deepcopy(PAGE_TEXTS)
    manifest["pages"].reverse()
    for path, text in tuple(page_texts.items()):
        page = json.loads(text)
        page["records"].reverse()
        page = dict(reversed(tuple(page.items())))
        _replace_page(manifest, page_texts, path, page)
    reordered = _replay(manifest, page_texts)
    assert reordered["state"] == "valid"
    assert (
        reordered["value"]["snapshot_sha256"]
        == baseline["value"]["snapshot_sha256"]
    )
    assert (
        reordered["value"]["fixture_pack_sha256"]
        == baseline["value"]["fixture_pack_sha256"]
    )


def test_missing_duplicate_malformed_and_altered_pages_are_detected_exactly():
    cases = []

    missing = copy.deepcopy(PAGE_TEXTS)
    missing.pop("pages/001.json")
    cases.append((MANIFEST, missing, "fixture:page:missing:pages/001.json"))

    duplicate_manifest = copy.deepcopy(MANIFEST)
    duplicate_pages = copy.deepcopy(PAGE_TEXTS)
    duplicate_page = json.loads(duplicate_pages["pages/001.json"])
    duplicate_page["records"].append(
        copy.deepcopy(json.loads(duplicate_pages["pages/000.json"])["records"][0])
    )
    _replace_page(
        duplicate_manifest,
        duplicate_pages,
        "pages/001.json",
        duplicate_page,
    )
    duplicate_manifest["completion"]["records_observed"] += 1
    cases.append(
        (
            duplicate_manifest,
            duplicate_pages,
            "snapshot:duplicate-record-identity",
        )
    )

    malformed = copy.deepcopy(PAGE_TEXTS)
    malformed["pages/000.json"] = "{not-json"
    cases.append((MANIFEST, malformed, "fixture:page:malformed:pages/000.json"))

    altered = copy.deepcopy(PAGE_TEXTS)
    altered["pages/000.json"] = altered["pages/000.json"].replace(
        "Futura-Py/FluxCalc", "Futura-Py/Altered", 1
    )
    cases.append((MANIFEST, altered, "fixture:page:sha256:pages/000.json"))

    for manifest, page_texts, expected_error in cases:
        first = _replay(manifest, page_texts)
        second = _replay(manifest, page_texts)
        assert first == second
        assert first["state"] == "invalid"
        assert expected_error in first["value"]["errors"]
        assert first["value"]["ticket"] is None
        assert "snapshot_sha256" not in first["value"]
        assert "corpus:fixture-replayed" not in first["evidence"]
        assert _replay()["state"] == "valid"
    assert [expected for _, _, expected in cases] == VECTORS["invalid"]


def test_fixture_replay_part_delegates_control_flow_to_audited_primitives():
    assert len(inspect.signature(replay_fixture_pack).parameters) == 1
    tree = ast.parse(inspect.getsource(replay_fixture_pack))
    forbidden = (
        ast.If,
        ast.For,
        ast.While,
        ast.Match,
        ast.Try,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )
    assert not [node for node in ast.walk(tree) if isinstance(node, forbidden)]
