"""Behavioral proof for the read-only GitHub corpus OUTWARD adapter."""

from __future__ import annotations

import ast
import copy
import inspect
import json
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError, URLError

import unified.github_acquisition as acquisition
from unified.boundary import inward
from unified.github_acquisition import (
    acquire_github_corpus,
    outward_read_github_page,
    raw_replay_pack,
    replay_raw_acquisition,
)
from unified.github_corpus import replay_fixture_pack
from unified.github_corpus import canonical_request_payload
from unified.machine.canonical import canonical_sha256


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "seed" / "github_corpus"
FIXTURES = CORPUS / "fixtures"
MANIFEST = json.loads((FIXTURES / "PACK.json").read_text())
PAGE_TEXTS = {
    page["path"]: (FIXTURES / page["path"]).read_text()
    for page in MANIFEST["pages"]
}
PIN = json.loads((CORPUS / "acquisition" / "PIN.json").read_text())


def _request():
    request = copy.deepcopy(MANIFEST["request"])
    request["variables"] = {}
    return request


def _body(path):
    page = json.loads(PAGE_TEXTS[path])
    return json.dumps(
        {"items": [record["payload"] for record in page["records"]]},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


class _Response:
    def __init__(self, body, status=200, headers=None):
        self._body = body.encode("utf-8")
        self.status = status
        self.headers = Message()
        for key, value in (headers or {}).items():
            self.headers[key] = value

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _acquire(monkeypatch, responses, credential=None, page_limit=2):
    queue = list(responses)
    monkeypatch.setattr(acquisition, "urlopen", lambda *_args, **_kwargs: queue.pop(0))
    return acquire_github_corpus(
        inward(
            {
                "credential": credential or {"kind": "anonymous", "value": None},
                "observed_at": "2026-08-03T12:00:00Z",
                "page_limit": page_limit,
                "request": _request(),
            }
        )
    )


def _pages():
    link = (
        '<https://api.github.com/search/repositories?page=2>; rel="next", '
        '<https://api.github.com/search/repositories?page=2>; rel="last"'
    )
    return (
        _Response(_body("pages/000.json"), headers={"Link": link}),
        _Response(_body("pages/001.json")),
    )


def test_live_and_raw_replay_have_one_semantic_snapshot_identity(monkeypatch):
    live = _acquire(monkeypatch, _pages())
    assert live["state"] == "valid"
    assert live["value"]["outcome"] == "complete"
    assert live["value"]["ticket"] is None
    assert live["evidence"][-1] == "github:acquisition-complete"

    packed = raw_replay_pack(
        inward(
            {
                "acquisition": live["value"],
                "observed_at": "2026-08-03T12:00:00Z",
                "page_limit": 2,
                "request": _request(),
            }
        )
    )
    assert packed["state"] == "valid"
    replay = replay_raw_acquisition(
        inward({"raw_replay": packed["value"]["raw_replay"]})
    )
    repeated = replay_raw_acquisition(
        inward({"raw_replay": copy.deepcopy(packed["value"]["raw_replay"])})
    )
    assert replay == repeated
    assert replay["state"] == "valid"
    assert replay["value"]["snapshot_sha256"] == live["value"]["snapshot_sha256"]
    assert replay["value"]["request_sha256"] == live["value"]["request_sha256"]
    assert replay["value"]["acquisition_mode"] == "replay"


def test_pagination_skip_repeat_limit_and_raw_tamper_are_detected(monkeypatch):
    live = _acquire(monkeypatch, _pages())
    packed = raw_replay_pack(
        inward(
            {
                "acquisition": live["value"],
                "observed_at": "2026-08-03T12:00:00Z",
                "page_limit": 2,
                "request": _request(),
            }
        )
    )["value"]["raw_replay"]
    cases = []
    skipped = copy.deepcopy(packed)
    skipped["pages"][1]["request_cursor"] = "rest:page:3"
    cases.append((skipped, "github:pagination-skipped-cursor"))
    repeated = copy.deepcopy(packed)
    repeated["pages"][1]["request_cursor"] = None
    cases.append((repeated, "github:pagination-repeated-cursor"))
    tampered = copy.deepcopy(packed)
    tampered["pages"][0]["body"] += " "
    cases.append((tampered, "raw-replay:page-sha256:0"))
    for pack, expected in cases:
        first = replay_raw_acquisition(inward({"raw_replay": pack}))
        second = replay_raw_acquisition(inward({"raw_replay": copy.deepcopy(pack)}))
        assert first == second
        assert first["state"] == "invalid"
        assert expected in first["value"]["errors"]
        assert first["value"]["ticket"] is None
        assert "snapshot_sha256" not in first["value"]

    partial = _acquire(monkeypatch, _pages(), page_limit=1)
    assert partial["state"] == "valid"
    assert partial["value"]["outcome"] == "partial"
    assert partial["value"]["status"] == "partial"

    skipped_link = '<https://api.github.com/search/repositories?page=3>; rel="next"'
    skipped_live = _acquire(
        monkeypatch,
        (_Response(_body("pages/000.json"), headers={"Link": skipped_link}),),
    )
    assert skipped_live["state"] == "invalid"
    assert "github:pagination-skipped-cursor" in skipped_live["value"]["errors"]
    assert skipped_live["value"]["ticket"] is None


def test_expected_external_outcomes_are_distinct_valid_and_ticketless(monkeypatch):
    headers = Message()
    headers["X-RateLimit-Remaining"] = "0"
    cases = (
        (HTTPError("https://api.github.com", 401, "secret-token", Message(), None), "unauthorized"),
        (HTTPError("https://api.github.com", 403, "secret-token", headers, None), "rate_limited"),
        (URLError("secret-token"), "unavailable"),
        (_Response("{not-json"), "malformed"),
    )
    for response, expected in cases:
        def raise_or_return(*_args, **_kwargs):
            if isinstance(response, Exception):
                raise response
            return response

        monkeypatch.setattr(acquisition, "urlopen", raise_or_return)
        result = acquire_github_corpus(
            inward(
                {
                    "credential": {"kind": "bearer", "value": "secret-token"},
                    "observed_at": "2026-08-03T12:00:00Z",
                    "page_limit": 2,
                    "request": _request(),
                }
            )
        )
        assert result["state"] == "valid"
        assert result["value"]["outcome"] == expected
        assert result["value"]["ticket"] is None
        assert "secret-token" not in repr(result)


def test_unhandled_failure_has_one_redacted_deterministic_ticket(monkeypatch):
    class BoundaryFailure(Exception):
        pass

    def fail(*_args, **_kwargs):
        raise BoundaryFailure("secret-token password")

    monkeypatch.setattr(acquisition, "urlopen", fail)
    first = acquire_github_corpus(
        inward(
            {
                "credential": {"kind": "bearer", "value": "secret-token"},
                "observed_at": "2026-08-03T12:00:00Z",
                "page_limit": 2,
                "request": _request(),
            }
        )
    )
    monkeypatch.setattr(acquisition, "urlopen", fail)
    second = acquire_github_corpus(
        inward(
            {
                "credential": {"kind": "bearer", "value": "secret-token"},
                "observed_at": "2026-08-03T12:00:00Z",
                "page_limit": 2,
                "request": _request(),
            }
        )
    )
    assert first == second
    assert first["state"] == "invalid"
    assert first["value"]["ticket"]["message"] == "[redacted-message]"
    assert first["value"]["ticket"]["ticket_id"] == second["value"]["ticket"]["ticket_id"]
    assert "secret-token" not in repr(first)


def test_invalid_boundary_input_never_returns_explicit_credential():
    result = acquire_github_corpus(
        inward(
            {
                "credential": {"kind": "bearer", "value": "secret-token"},
                "observed_at": "not-a-time",
                "page_limit": 0,
                "request": {},
            }
        )
    )
    assert result["state"] == "invalid"
    assert result["value"]["ticket"] is None
    assert "secret-token" not in repr(result)


def test_pin_replays_verified_issue_44_authority_and_rejects_tamper(tmp_path):
    result = acquisition.audited_load_replay_pin_primitive(
        CORPUS / "acquisition" / "PIN.json"
    )
    expected = json.loads((FIXTURES / "EXPECTED.json").read_text())
    assert result["state"] == "valid"
    assert result["value"]["fixture_pack_sha256"] == PIN["fixture_pack_sha256"]
    assert result["value"]["request_sha256"] == PIN["request_sha256"]
    assert result["value"]["snapshot_sha256"] == PIN["snapshot_sha256"]
    assert acquisition.host_main(("replay", str(CORPUS / "acquisition" / "PIN.json"))) == 0
    assert expected["snapshot_sha256"] == PIN["snapshot_sha256"]
    live_request = json.loads(
        (CORPUS / PIN["live_request"]).read_text()
    )
    assert canonical_sha256(canonical_request_payload(live_request)) == PIN[
        "live_request_sha256"
    ]

    altered = copy.deepcopy(MANIFEST)
    altered["completion"]["records_observed"] = 4
    bad = replay_fixture_pack(
        inward({"fixture_pack": {"manifest": altered, "page_texts": PAGE_TEXTS}})
    )
    assert bad["state"] == "invalid"
    assert bad["value"]["ticket"] is None


def test_one_host_command_uses_pinned_live_request_without_hidden_token(monkeypatch, capsys):
    monkeypatch.setattr(
        acquisition,
        "urlopen",
        lambda *_args, **_kwargs: _Response(_body("pages/000.json")),
    )
    code = acquisition.host_main(
        ("acquire", str(CORPUS / "acquisition" / "PIN.json"))
    )
    result = json.loads(capsys.readouterr().out)
    assert code == 0
    assert result["state"] == "valid"
    assert result["value"]["outcome"] == "complete"
    assert result["value"]["request_sha256"] == PIN["live_request_sha256"]
    assert result["value"]["ticket"] is None


def test_public_parts_and_production_surfaces_obey_boundary_laws():
    parts = (
        acquire_github_corpus,
        outward_read_github_page,
        raw_replay_pack,
        replay_raw_acquisition,
    )
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
    for part in parts:
        assert len(inspect.signature(part).parameters) == 1
        tree = ast.parse(inspect.getsource(part))
        assert not [node for node in ast.walk(tree) if isinstance(node, forbidden)]

    source = (ROOT / "unified" / "github_acquisition.py").read_text()
    assert "os.environ" not in source
    assert "getenv" not in source
    assert "requests" not in source
    compiler = "\n".join(
        path.read_text() for path in (ROOT / "unified" / "generator").rglob("*.py")
    )
    assert "github_acquisition" not in compiler
    assert "github-corpus-acquisition" not in compiler
