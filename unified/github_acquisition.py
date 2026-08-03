"""Read-only GitHub corpus OUTWARD boundary.

The canonical request is supplied explicitly.  Credentials are supplied only
at the host boundary and are never read from the environment, returned, or
included in evidence.  Transport responses remain separate from the semantic
snapshot produced by :mod:`unified.github_corpus`.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from .boundary import inward
from .github_corpus import (
    FIXTURE_PAGE_VERSION,
    SNAPSHOT_VERSION,
    audited_identify_snapshot_primitive,
    audited_invalid_primitive,
    audited_request_errors_primitive,
    canonical_request_payload,
    replay_fixture_pack,
)
from .machine.canonical import canonical_sha256
from .thing import is_thing


ACQUISITION_VERSION = "UC-GITHUB-ACQUISITION-1"
REPLAY_PACK_VERSION = "UC-GITHUB-RAW-REPLAY-PACK-1"
GITHUB_API_ORIGIN = "https://api.github.com"
EXPECTED_OUTCOMES = frozenset(
    {"complete", "partial", "rate_limited", "unavailable", "unauthorized", "malformed"}
)


def _result(thing, value, mark, state="valid"):
    return {
        **thing,
        "value": value,
        "evidence": (*thing.get("evidence", ()), mark),
        "state": state,
    }


def audited_invalid_boundary_primitive(thing, subject, errors, mark):
    base = thing if is_thing(thing) else {
        "value": None,
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": "invalid",
    }
    return _result(
        base,
        {subject: None, "errors": tuple(errors), "ticket": None},
        mark,
        "invalid",
    )


def audited_redacted_ticket_primitive(error):
    identity = canonical_sha256(
        {
            "error_type": type(error).__name__,
            "operation": "github-corpus-acquisition",
        }
    )[:16]
    return {
        "acked": False,
        "error_type": type(error).__name__,
        "message": "[redacted-message]",
        "operation": "github-corpus-acquisition",
        "ticket_id": identity,
    }


def audited_acquisition_input_errors_primitive(value):
    if not isinstance(value, dict):
        return ("acquisition:type",)
    expected = {"credential", "observed_at", "page_limit", "request"}
    errors = []
    if set(value) != expected:
        errors.append("acquisition:fields")
    errors.extend(audited_request_errors_primitive(value.get("request")))
    credential = value.get("credential")
    if not isinstance(credential, dict) or set(credential) != {"kind", "value"}:
        errors.append("credential:fields")
    elif credential.get("kind") not in {"anonymous", "bearer"}:
        errors.append("credential:kind")
    elif credential.get("kind") == "anonymous" and credential.get("value") is not None:
        errors.append("credential:anonymous-value")
    elif credential.get("kind") == "bearer" and not isinstance(credential.get("value"), str):
        errors.append("credential:bearer-value")
    elif credential.get("kind") == "bearer" and not credential.get("value"):
        errors.append("credential:bearer-value")
    page_limit = value.get("page_limit")
    if not isinstance(page_limit, int) or isinstance(page_limit, bool) or page_limit < 1:
        errors.append("acquisition:page-limit")
    observed_at = value.get("observed_at")
    if not isinstance(observed_at, str) or not observed_at.endswith("Z"):
        errors.append("acquisition:observed-at")
    return tuple(errors)


def audited_rest_url_primitive(request, cursor):
    page = 1
    if isinstance(cursor, str) and cursor.startswith("rest:page:"):
        page = int(cursor.rsplit(":", 1)[1])
    variables = {
        key: value
        for key, value in request["variables"].items()
        if key not in {"page", "per_page", "q"}
    }
    query = {
        **variables,
        "page": page,
        "per_page": request["page_size"],
        "q": request["query"],
    }
    return f"{GITHUB_API_ORIGIN}{request['endpoint']}?{urlencode(query)}"


def audited_graphql_request_primitive(request, cursor):
    variables = {
        **request["variables"],
        "after": cursor,
        "first": request["page_size"],
        "query": request["variables"].get("query", request["query"]),
    }
    return (
        f"{GITHUB_API_ORIGIN}{request['endpoint']}",
        json.dumps(
            {"query": request["query"], "variables": variables},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8"),
    )


def audited_headers_primitive(request, credential):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "unified-code-github-corpus/1",
        "X-GitHub-Api-Version": request["api_version"],
    }
    if credential["kind"] == "bearer":
        headers["Authorization"] = f"Bearer {credential['value']}"
    return headers


def audited_http_outcome_primitive(status, headers, body):
    remaining = headers.get("x-ratelimit-remaining")
    if status in {429} or status == 403 and remaining == "0":
        return "rate_limited"
    if status in {401, 403}:
        return "unauthorized"
    if status >= 500:
        return "unavailable"
    if status < 200 or status >= 300:
        return "malformed"
    try:
        decoded = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return "malformed"
    return "success" if isinstance(decoded, dict) else "malformed"


def audited_next_rest_cursor_primitive(headers):
    link = headers.get("link", "")
    for item in link.split(","):
        if 'rel="next"' not in item:
            continue
        target = item.split(";", 1)[0].strip().strip("<>")
        page = parse_qs(urlparse(target).query).get("page", ())
        if page and page[0].isdigit():
            return f"rest:page:{int(page[0])}"
    return None


def audited_transport_request_primitive(request, credential, cursor):
    headers = audited_headers_primitive(request, credential)
    if request["transport"] == "rest":
        url = audited_rest_url_primitive(request, cursor)
        return Request(url, headers=headers, method="GET"), url
    url, body = audited_graphql_request_primitive(request, cursor)
    return Request(url, data=body, headers=headers, method="POST"), url


def audited_outward_read_github_page_primitive(thing):
    """Physical host control flow for exactly one public read operation."""
    if not is_thing(thing):
        return audited_invalid_boundary_primitive(
            thing, "github_page", ("thing:invalid",), "github:page-invalid"
        )
    value = thing.get("value")
    if not isinstance(value, dict) or set(value) != {"credential", "cursor", "request"}:
        return audited_invalid_boundary_primitive(
            thing, "github_page", ("github:page-input",), "github:page-invalid"
        )
    request = value["request"]
    credential = value["credential"]
    try:
        transport_request, source_url = audited_transport_request_primitive(
            request, credential, value["cursor"]
        )
        with urlopen(transport_request, timeout=30) as response:
            body_bytes = response.read()
            status = int(response.status)
            headers = {key.lower(): value for key, value in response.headers.items()}
    except HTTPError as error:
        body_bytes = error.read()
        status = int(error.code)
        headers = {key.lower(): value for key, value in error.headers.items()}
        source_url = error.url
    except URLError:
        return _result(
            thing,
            {
                "body": None,
                "headers": {},
                "outcome": "unavailable",
                "source_url": None,
                "status_code": None,
                "ticket": None,
            },
            "github:page-unavailable",
        )
    except Exception as error:
        ticket = audited_redacted_ticket_primitive(error)
        return _result(
            thing,
            {
                "body": None,
                "headers": {},
                "outcome": "unhandled",
                "source_url": None,
                "status_code": None,
                "ticket": ticket,
            },
            "github:page-unhandled",
            "invalid",
        )
    body = body_bytes.decode("utf-8", errors="replace")
    outcome = audited_http_outcome_primitive(status, headers, body)
    return _result(
        thing,
        {
            "body": body,
            "headers": {
                key: headers[key]
                for key in ("link", "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset")
                if key in headers
            },
            "outcome": outcome,
            "source_url": source_url,
            "status_code": status,
            "ticket": None,
        },
        f"github:page-{outcome}",
    )


def outward_read_github_page(thing):
    """Public OUTWARD Part: one page request Thing in, one Thing out."""
    return audited_outward_read_github_page_primitive(thing)


def audited_select_payload_primitive(record, fields):
    aliases = {"source_url": "url"}
    return {
        field: record.get(field, record.get(aliases.get(field, field)))
        for field in fields
    }


def audited_decode_records_primitive(request, body):
    try:
        document = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return (), None, ("github:response-json",)
    if request["transport"] == "rest":
        records = document.get("items")
        next_cursor = None
    else:
        search = ((document.get("data") or {}).get("search") or {})
        records = search.get("nodes")
        page_info = search.get("pageInfo") or {}
        next_cursor = page_info.get("endCursor") if page_info.get("hasNextPage") else None
    if not isinstance(records, list):
        return (), None, ("github:response-records",)
    projected = []
    errors = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"github:record:{index}:type")
            continue
        identity = record.get("id")
        if identity is None:
            errors.append(f"github:record:{index}:identity")
            continue
        payload = audited_select_payload_primitive(record, request["record_fields"])
        missing = tuple(field for field, value in payload.items() if value is None)
        if missing:
            errors.append(f"github:record:{index}:fields")
            continue
        projected.append(
            {
                "payload": payload,
                "source_identity": f"github:repository:{identity}",
            }
        )
    return tuple(projected), next_cursor, tuple(errors)


def audited_acquisition_outcome_primitive(thing, outcome, pages, raw_pages, attempts, started_ns):
    value = thing["value"]
    duration_ns = value.get(
        "_duration_ns", max(0, time.monotonic_ns() - started_ns)
    )
    evidence = {
        "acquisition_mode": value.get("_acquisition_mode", "live"),
        "attempts": attempts,
        "duration_ns": duration_ns,
        "observed_at": value["observed_at"],
    }
    if outcome in {"unauthorized", "malformed"}:
        return _result(
            thing,
            {
                "acquisition_version": ACQUISITION_VERSION,
                "errors": (f"github:{outcome}",),
                "outcome": outcome,
                "raw_pages": tuple(raw_pages),
                "snapshot_sha256": None,
                "ticket": None,
            },
            f"github:acquisition-{outcome}",
        )
    status = outcome
    reason = {
        "complete": "exhausted",
        "partial": "page_limit",
        "rate_limited": "rate_limit",
        "unavailable": "provider_unavailable",
    }[status]
    snapshot_pages = pages if status != "unavailable" else []
    snapshot = {
        "completion": {
            "reason": reason,
            "records_observed": sum(len(page["records"]) for page in snapshot_pages),
        },
        "evidence": evidence,
        "format_version": SNAPSHOT_VERSION,
        "pages": snapshot_pages,
        "request": value["request"],
        "status": status,
    }
    identified = audited_identify_snapshot_primitive(
        {**thing, "value": {"snapshot": snapshot}}
    )
    if identified["state"] == "invalid":
        return identified
    return _result(
        thing,
        {
            **identified["value"],
            "acquisition_version": ACQUISITION_VERSION,
            "errors": (),
            "outcome": outcome,
            "raw_pages": tuple(raw_pages),
        },
        f"github:acquisition-{outcome}",
    )


def audited_acquire_github_corpus_primitive(thing):
    """Audited orchestration of explicit cursor traversal."""
    if not is_thing(thing):
        return audited_invalid_boundary_primitive(
            thing, "acquisition", ("thing:invalid",), "github:acquisition-invalid"
        )
    errors = audited_acquisition_input_errors_primitive(thing.get("value"))
    if errors:
        return audited_invalid_boundary_primitive(
            thing, "acquisition", errors, "github:acquisition-invalid"
        )
    value = thing["value"]
    request = canonical_request_payload(value["request"])
    cursor = request["initial_cursor"]
    seen = set()
    pages = []
    raw_pages = []
    attempts = []
    started_ns = time.monotonic_ns()
    for page_index in range(value["page_limit"]):
        if cursor in seen:
            return audited_invalid_boundary_primitive(
                thing,
                "acquisition",
                ("github:pagination-repeated-cursor",),
                "github:acquisition-invalid",
            )
        seen.add(cursor)
        page_result = outward_read_github_page(
            inward(
                {
                    "credential": value["credential"],
                    "cursor": cursor,
                    "request": request,
                }
            )
        )
        outcome = page_result["value"]["outcome"]
        attempts.append(
            {
                "outcome": "transport_error" if outcome in {"unauthorized", "malformed", "unhandled"} else outcome,
                "page_index": page_index,
                "retry_ordinal": 0,
            }
        )
        if outcome == "unhandled":
            return _result(
                thing,
                {
                    "acquisition_version": ACQUISITION_VERSION,
                    "errors": ("github:unhandled",),
                    "outcome": "unhandled",
                    "raw_pages": tuple(raw_pages),
                    "snapshot_sha256": None,
                    "ticket": page_result["value"]["ticket"],
                },
                "github:acquisition-unhandled",
                "invalid",
            )
        if outcome in {"unauthorized", "malformed", "unavailable", "rate_limited"}:
            return audited_acquisition_outcome_primitive(
                thing, outcome, pages, raw_pages, attempts, started_ns
            )
        body = page_result["value"]["body"]
        records, graph_cursor, decode_errors = audited_decode_records_primitive(request, body)
        if decode_errors:
            return audited_acquisition_outcome_primitive(
                thing, "malformed", pages, raw_pages, attempts, started_ns
            )
        next_cursor = (
            audited_next_rest_cursor_primitive(page_result["value"]["headers"])
            if request["transport"] == "rest"
            else graph_cursor
        )
        if request["transport"] == "rest" and next_cursor is not None:
            current_page = 1 if cursor is None else int(cursor.rsplit(":", 1)[1])
            if next_cursor != f"rest:page:{current_page + 1}":
                return audited_invalid_boundary_primitive(
                    thing,
                    "acquisition",
                    ("github:pagination-skipped-cursor",),
                    "github:acquisition-invalid",
                )
        raw_sha256 = sha256(body.encode("utf-8")).hexdigest()
        pages.append(
            {
                "index": page_index,
                "next_cursor": next_cursor,
                "raw_sha256": raw_sha256,
                "records": list(records),
                "request_cursor": cursor,
            }
        )
        raw_pages.append(
            {
                "body": body,
                "content_sha256": raw_sha256,
                "index": page_index,
                "next_cursor": next_cursor,
                "request_cursor": cursor,
                "source_url": page_result["value"]["source_url"],
            }
        )
        if next_cursor is None:
            return audited_acquisition_outcome_primitive(
                thing, "complete", pages, raw_pages, attempts, started_ns
            )
        cursor = next_cursor
    return audited_acquisition_outcome_primitive(
        thing, "partial", pages, raw_pages, attempts, started_ns
    )


def acquire_github_corpus(thing):
    """Public Part: acquire one pinned corpus Thing through the OUTWARD boundary."""
    return audited_acquire_github_corpus_primitive(thing)


def audited_raw_replay_errors_primitive(pack):
    if not isinstance(pack, dict):
        return ("raw-replay:type",)
    expected = {"format_version", "observed_at", "pages", "page_limit", "request"}
    errors = []
    if set(pack) != expected:
        errors.append("raw-replay:fields")
    if pack.get("format_version") != REPLAY_PACK_VERSION:
        errors.append("raw-replay:format-version")
    errors.extend(audited_request_errors_primitive(pack.get("request")))
    if not isinstance(pack.get("pages"), list) or not pack.get("pages"):
        errors.append("raw-replay:pages")
    return tuple(errors)


def audited_replay_raw_acquisition_primitive(thing):
    if not is_thing(thing):
        return audited_invalid_primitive(
            thing, "raw_replay", ("thing:invalid",), "github:raw-replay-invalid"
        )
    value = thing.get("value")
    pack = value.get("raw_replay") if isinstance(value, dict) else None
    errors = audited_raw_replay_errors_primitive(pack)
    if errors:
        return audited_invalid_primitive(
            thing, "raw_replay", errors, "github:raw-replay-invalid"
        )
    request = canonical_request_payload(pack["request"])
    pages = []
    attempts = []
    seen = set()
    for page in sorted(pack["pages"], key=lambda item: item.get("index", -1)):
        expected = {"body", "content_sha256", "index", "next_cursor", "request_cursor", "source_url"}
        if not isinstance(page, dict) or set(page) != expected:
            errors = (*errors, "raw-replay:page-fields")
            continue
        digest = sha256(page["body"].encode("utf-8")).hexdigest() if isinstance(page.get("body"), str) else None
        if digest != page.get("content_sha256"):
            errors = (*errors, f"raw-replay:page-sha256:{page.get('index')}")
            continue
        if page["request_cursor"] in seen:
            errors = (*errors, "github:pagination-repeated-cursor")
        seen.add(page["request_cursor"])
        records, graph_cursor, decode_errors = audited_decode_records_primitive(request, page["body"])
        errors = (*errors, *decode_errors)
        next_cursor = page["next_cursor"]
        if request["transport"] == "graphql" and graph_cursor != next_cursor:
            errors = (*errors, "raw-replay:next-cursor")
        pages.append(
            {
                "index": page["index"],
                "next_cursor": next_cursor,
                "raw_sha256": page["content_sha256"],
                "records": list(records),
                "request_cursor": page["request_cursor"],
            }
        )
        attempts.append({"outcome": "success", "page_index": page["index"], "retry_ordinal": 0})
    ordered = sorted(pages, key=lambda item: item["index"])
    if ordered and ordered[0]["request_cursor"] != request["initial_cursor"]:
        errors = (*errors, "github:pagination-initial-cursor")
    for previous, current in zip(ordered, ordered[1:]):
        if previous["next_cursor"] != current["request_cursor"]:
            errors = (*errors, "github:pagination-skipped-cursor")
    if errors:
        return audited_invalid_primitive(
            thing, "raw_replay", errors, "github:raw-replay-invalid"
        )
    outcome = "complete" if ordered[-1]["next_cursor"] is None else "partial"
    replay_thing = {
        **thing,
        "value": {
            "_acquisition_mode": "replay",
            "_duration_ns": 0,
            "credential": {"kind": "anonymous", "value": None},
            "observed_at": pack["observed_at"],
            "page_limit": pack["page_limit"],
            "request": request,
        },
    }
    result = audited_acquisition_outcome_primitive(
        replay_thing, outcome, ordered, pack["pages"], attempts, time.monotonic_ns()
    )
    return _result(thing, result["value"], "github:raw-replay-complete", result["state"])


def replay_raw_acquisition(thing):
    """Public Part: authenticate and replay one raw acquisition package."""
    return audited_replay_raw_acquisition_primitive(thing)


def raw_replay_pack(thing):
    """Public Part: project a successful live result into a replay package."""
    return audited_raw_replay_pack_primitive(thing)


def audited_raw_replay_pack_primitive(thing):
    if not is_thing(thing):
        return audited_invalid_primitive(
            thing, "acquisition", ("thing:invalid",), "github:replay-pack-invalid"
        )
    value = thing.get("value")
    acquisition = value.get("acquisition") if isinstance(value, dict) else None
    request = value.get("request") if isinstance(value, dict) else None
    page_limit = value.get("page_limit") if isinstance(value, dict) else None
    observed_at = value.get("observed_at") if isinstance(value, dict) else None
    if not isinstance(acquisition, dict) or acquisition.get("outcome") not in {"complete", "partial"}:
        return audited_invalid_primitive(
            thing, "acquisition", ("replay-pack:acquisition",), "github:replay-pack-invalid"
        )
    pack = {
        "format_version": REPLAY_PACK_VERSION,
        "observed_at": observed_at,
        "page_limit": page_limit,
        "pages": list(acquisition["raw_pages"]),
        "request": canonical_request_payload(request),
    }
    return _result(
        thing,
        {"raw_replay": pack, "raw_replay_sha256": canonical_sha256(pack), "ticket": None},
        "github:replay-pack-formed",
    )


def audited_load_replay_pin_primitive(path):
    pin = json.loads(Path(path).read_text(encoding="utf-8"))
    root = Path(path).resolve().parent.parent
    fixture_path = (root / pin["fixture_pack"]).resolve()
    manifest = json.loads(fixture_path.read_text(encoding="utf-8"))
    page_texts = {
        page["path"]: (fixture_path.parent / page["path"]).read_text(encoding="utf-8")
        for page in manifest["pages"]
    }
    result = replay_fixture_pack(
        inward({"fixture_pack": {"manifest": manifest, "page_texts": page_texts}})
    )
    expected = pin["fixture_pack_sha256"]
    if result["state"] != "valid" or result["value"]["fixture_pack_sha256"] != expected:
        raise ValueError("pinned-fixture-mismatch")
    return result


def audited_load_live_pin_primitive(path, credential_path=None):
    pin_path = Path(path).resolve()
    pin = json.loads(pin_path.read_text(encoding="utf-8"))
    root = pin_path.parent.parent
    request = json.loads((root / pin["live_request"]).read_text(encoding="utf-8"))
    request_sha256 = canonical_sha256(canonical_request_payload(request))
    if request_sha256 != pin["live_request_sha256"]:
        raise ValueError("pinned-live-request-mismatch")
    credential = {"kind": "anonymous", "value": None}
    if credential_path is not None:
        credential = json.loads(Path(credential_path).read_text(encoding="utf-8"))
    return acquire_github_corpus(
        inward(
            {
                "credential": credential,
                "observed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "page_limit": pin["page_limit"],
                "request": request,
            }
        )
    )


def host_main(argv=None):
    """Host CLI. Replay is deterministic; live credentials require an explicit file."""
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    valid_shape = (
        len(arguments) == 2 and arguments[0] in {"acquire", "replay"}
    ) or (
        len(arguments) == 3 and arguments[0] == "acquire"
    )
    if not valid_shape:
        print(
            "usage: python -m unified.github_acquisition "
            "<acquire|replay> <PIN.json> [credential.json]",
            file=sys.stderr,
        )
        return 2
    try:
        result = (
            audited_load_replay_pin_primitive(arguments[1])
            if arguments[0] == "replay"
            else audited_load_live_pin_primitive(
                arguments[1], arguments[2] if len(arguments) == 3 else None
            )
        )
    except Exception:
        print(json.dumps({"error": "pinned-acquisition-failed"}, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["state"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(host_main())
