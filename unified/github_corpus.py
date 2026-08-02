"""Canonical GitHub corpus request and snapshot contract.

No network operation occurs here.  Future live acquisition and offline replay
must both enter through these pure Parts after their named OUTWARD boundary has
produced a snapshot document.
"""

from __future__ import annotations

import json
import re

from .machine.canonical import canonical_sha256
from .thing import is_thing


REQUEST_VERSION = "UC-GITHUB-CORPUS-REQUEST-1"
SNAPSHOT_VERSION = "UC-GITHUB-CORPUS-SNAPSHOT-1"
FIXTURE_PACK_VERSION = "UC-GITHUB-CORPUS-FIXTURE-PACK-1"
FIXTURE_PAGE_VERSION = "UC-GITHUB-CORPUS-FIXTURE-PAGE-1"
TRANSPORTS = frozenset({"graphql", "rest"})
VISIBILITY_SCOPES = frozenset({"organization-public", "public"})
SNAPSHOT_STATUSES = frozenset(
    {"complete", "partial", "rate_limited", "unavailable"}
)
STATUS_REASONS = {
    "complete": frozenset({"exhausted"}),
    "partial": frozenset({"operator_limit", "page_limit", "unknown"}),
    "rate_limited": frozenset({"rate_limit"}),
    "unavailable": frozenset({"provider_unavailable"}),
}
ATTEMPT_OUTCOMES = frozenset(
    {"success", "rate_limited", "unavailable", "transport_error"}
)
RFC3339_UTC_RE = re.compile(
    r"^[0-9]{4}-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])T"
    r"([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]+)?Z$"
)


def _result(thing, value, mark, state):
    return {
        **thing,
        "value": value,
        "evidence": (*thing.get("evidence", ()), mark),
        "state": state,
    }


def audited_invalid_primitive(thing, subject, errors, mark):
    current = thing.get("value") if isinstance(thing, dict) else thing
    base = thing if is_thing(thing) else {
        "value": current,
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": "invalid",
    }
    return _result(
        base,
        {
            subject: current.get(subject) if isinstance(current, dict) else None,
            "errors": tuple(errors),
            "ticket": None,
        },
        mark,
        "invalid",
    )


def audited_is_sha256_primitive(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(letter in "0123456789abcdef" for letter in value)
    )


def audited_request_errors_primitive(request):
    """Host control flow for the frozen request schema."""
    errors = []
    if not isinstance(request, dict):
        return ("request:type",)
    expected = {
        "api_version",
        "endpoint",
        "format_version",
        "initial_cursor",
        "page_size",
        "provider",
        "query",
        "record_fields",
        "transport",
        "variables",
        "visibility_scope",
    }
    if set(request) != expected:
        errors.append("request:fields")
    if request.get("format_version") != REQUEST_VERSION:
        errors.append("request:format-version")
    if request.get("provider") != "github":
        errors.append("request:provider")
    if request.get("transport") not in TRANSPORTS:
        errors.append("request:transport")
    if not isinstance(request.get("api_version"), str) or not request.get(
        "api_version"
    ):
        errors.append("request:api-version")
    if not isinstance(request.get("endpoint"), str) or not request.get("endpoint"):
        errors.append("request:endpoint")
    if not isinstance(request.get("query"), str) or not request.get("query"):
        errors.append("request:query")
    if not isinstance(request.get("variables"), dict):
        errors.append("request:variables")
    if request.get("visibility_scope") not in VISIBILITY_SCOPES:
        errors.append("request:visibility-scope")
    if not isinstance(request.get("page_size"), int) or isinstance(
        request.get("page_size"), bool
    ) or not 1 <= request.get("page_size", 0) <= 100:
        errors.append("request:page-size")
    if request.get("initial_cursor") is not None and not isinstance(
        request.get("initial_cursor"), str
    ):
        errors.append("request:initial-cursor")
    fields = request.get("record_fields")
    if not isinstance(fields, list) or not fields or not all(
        isinstance(field, str) and field for field in fields
    ) or len(fields) != len(set(fields or ())):
        errors.append("request:record-fields")
    return tuple(errors)


def canonical_request_payload(request):
    return {
        "api_version": request["api_version"],
        "endpoint": request["endpoint"],
        "format_version": request["format_version"],
        "initial_cursor": request["initial_cursor"],
        "page_size": request["page_size"],
        "provider": request["provider"],
        "query": request["query"],
        "record_fields": sorted(request["record_fields"]),
        "transport": request["transport"],
        "variables": request["variables"],
        "visibility_scope": request["visibility_scope"],
    }


def audited_identify_request_primitive(thing):
    """Validate and identify one request through a named audited primitive."""
    if not is_thing(thing):
        return audited_invalid_primitive(
            thing, "request", ("thing:invalid",), "corpus:request-invalid"
        )
    value = thing.get("value")
    request = value.get("request") if isinstance(value, dict) else None
    errors = audited_request_errors_primitive(request)
    if errors:
        return audited_invalid_primitive(
            thing, "request", errors, "corpus:request-invalid"
        )
    canonical = canonical_request_payload(request)
    return _result(
        thing,
        {
            "request": canonical,
            "request_sha256": canonical_sha256(canonical),
            "errors": (),
            "ticket": None,
        },
        "corpus:request-identified",
        "valid",
    )


def identify_request(thing):
    """Public Part: one Thing in, one Thing out."""
    return audited_identify_request_primitive(thing)


def audited_record_errors_primitive(record, page_index):
    if not isinstance(record, dict):
        return (f"page:{page_index}:record:type",)
    if set(record) != {"payload", "source_identity"}:
        return (f"page:{page_index}:record:fields",)
    errors = []
    if not isinstance(record.get("source_identity"), str) or not record.get(
        "source_identity"
    ):
        errors.append(f"page:{page_index}:record:source-identity")
    if not isinstance(record.get("payload"), dict):
        errors.append(f"page:{page_index}:record:payload")
    return tuple(errors)


def audited_page_errors_primitive(page):
    if not isinstance(page, dict):
        return ("page:type",)
    index = page.get("index")
    prefix = f"page:{index}" if isinstance(index, int) else "page:unknown"
    expected = {"index", "next_cursor", "raw_sha256", "records", "request_cursor"}
    errors = []
    if set(page) != expected:
        errors.append(f"{prefix}:fields")
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        errors.append("page:index")
    if page.get("request_cursor") is not None and not isinstance(
        page.get("request_cursor"), str
    ):
        errors.append(f"{prefix}:request-cursor")
    if page.get("next_cursor") is not None and not isinstance(
        page.get("next_cursor"), str
    ):
        errors.append(f"{prefix}:next-cursor")
    if not audited_is_sha256_primitive(page.get("raw_sha256")):
        errors.append(f"{prefix}:raw-sha256")
    records = page.get("records")
    if not isinstance(records, list):
        errors.append(f"{prefix}:records")
    else:
        for record in records:
            errors.extend(audited_record_errors_primitive(record, index))
        identities = [
            record.get("source_identity")
            for record in records
            if isinstance(record, dict)
        ]
        if len(identities) != len(set(identities)):
            errors.append(f"{prefix}:duplicate-record-identity")
    return tuple(errors)


def audited_evidence_errors_primitive(evidence):
    if not isinstance(evidence, dict):
        return ("evidence:type",)
    expected = {"acquisition_mode", "attempts", "duration_ns", "observed_at"}
    errors = []
    if set(evidence) != expected:
        errors.append("evidence:fields")
    if evidence.get("acquisition_mode") not in {"live", "replay"}:
        errors.append("evidence:acquisition-mode")
    observed_at = evidence.get("observed_at")
    if not isinstance(observed_at, str) or not RFC3339_UTC_RE.fullmatch(
        observed_at
    ):
        errors.append("evidence:observed-at")
    if not isinstance(evidence.get("duration_ns"), int) or isinstance(
        evidence.get("duration_ns"), bool
    ) or evidence.get("duration_ns", -1) < 0:
        errors.append("evidence:duration-ns")
    attempts = evidence.get("attempts")
    if not isinstance(attempts, list):
        errors.append("evidence:attempts")
    else:
        for attempt_index, attempt in enumerate(attempts):
            prefix = f"evidence:attempt:{attempt_index}"
            if not isinstance(attempt, dict):
                errors.append(f"{prefix}:type")
                continue
            if set(attempt) != {"outcome", "page_index", "retry_ordinal"}:
                errors.append(f"{prefix}:fields")
            page_index = attempt.get("page_index")
            if not isinstance(page_index, int) or isinstance(
                page_index, bool
            ) or page_index < 0:
                errors.append(f"{prefix}:page-index")
            retry_ordinal = attempt.get("retry_ordinal")
            if not isinstance(retry_ordinal, int) or isinstance(
                retry_ordinal, bool
            ) or retry_ordinal < 0:
                errors.append(f"{prefix}:retry-ordinal")
            if attempt.get("outcome") not in ATTEMPT_OUTCOMES:
                errors.append(f"{prefix}:outcome")
    return tuple(errors)


def audited_snapshot_errors_primitive(snapshot):
    """Host control flow for schema and cross-page invariant validation."""
    if not isinstance(snapshot, dict):
        return ("snapshot:type",)
    expected = {
        "completion",
        "evidence",
        "format_version",
        "pages",
        "request",
        "status",
    }
    errors = []
    if set(snapshot) != expected:
        errors.append("snapshot:fields")
    if snapshot.get("format_version") != SNAPSHOT_VERSION:
        errors.append("snapshot:format-version")
    errors.extend(audited_request_errors_primitive(snapshot.get("request")))
    status = snapshot.get("status")
    if status not in SNAPSHOT_STATUSES:
        errors.append("snapshot:status")
    completion = snapshot.get("completion")
    if not isinstance(completion, dict) or set(completion) != {
        "reason",
        "records_observed",
    }:
        errors.append("snapshot:completion")
    else:
        records_observed = completion.get("records_observed")
        if not isinstance(records_observed, int) or isinstance(
            records_observed, bool
        ) or records_observed < 0:
            errors.append("snapshot:records-observed-type")
        if status in STATUS_REASONS and completion.get(
            "reason"
        ) not in STATUS_REASONS[status]:
            errors.append("snapshot:status-reason")
    pages = snapshot.get("pages")
    if not isinstance(pages, list):
        errors.append("snapshot:pages")
        pages = []
    for page in pages:
        errors.extend(audited_page_errors_primitive(page))
    record_identities = [
        record.get("source_identity")
        for page in pages
        if isinstance(page, dict) and isinstance(page.get("records"), list)
        for record in page["records"]
        if isinstance(record, dict)
    ]
    if len(record_identities) != len(set(record_identities)):
        errors.append("snapshot:duplicate-record-identity")
    ordered = sorted(
        (page for page in pages if isinstance(page, dict)),
        key=lambda page: page.get("index", -1),
    )
    indices = [page.get("index") for page in ordered]
    if indices != list(range(len(ordered))):
        errors.append("snapshot:page-order")
    if ordered and isinstance(snapshot.get("request"), dict):
        if ordered[0].get("request_cursor") != snapshot["request"].get(
            "initial_cursor"
        ):
            errors.append("snapshot:initial-cursor-chain")
        for previous, current in zip(ordered, ordered[1:]):
            if previous.get("next_cursor") != current.get("request_cursor"):
                errors.append("snapshot:cursor-chain")
    observed = sum(
        len(page.get("records", ()))
        for page in ordered
        if isinstance(page.get("records"), list)
    )
    if isinstance(completion, dict) and completion.get("records_observed") != observed:
        errors.append("snapshot:records-observed")
    if status == "complete" and (not ordered or ordered[-1].get("next_cursor") is not None):
        errors.append("snapshot:complete-terminal-cursor")
    if status == "unavailable" and ordered:
        errors.append("snapshot:unavailable-pages")
    errors.extend(audited_evidence_errors_primitive(snapshot.get("evidence")))
    return tuple(errors)


def _canonical_record(record):
    return {
        "payload": record["payload"],
        "source_identity": record["source_identity"],
    }


def audited_canonical_page_primitive(page):
    return {
        "index": page["index"],
        "next_cursor": page["next_cursor"],
        "raw_sha256": page["raw_sha256"],
        "records": sorted(
            (_canonical_record(record) for record in page["records"]),
            key=lambda record: (
                record["source_identity"],
                canonical_sha256(record["payload"]),
            ),
        ),
        "request_cursor": page["request_cursor"],
    }


def canonical_snapshot_payload(snapshot):
    return audited_canonical_snapshot_payload_primitive(snapshot)


def audited_canonical_snapshot_payload_primitive(snapshot):
    return {
        "completion": snapshot["completion"],
        "format_version": snapshot["format_version"],
        "pages": sorted(
            (audited_canonical_page_primitive(page) for page in snapshot["pages"]),
            key=lambda page: page["index"],
        ),
        "request": canonical_request_payload(snapshot["request"]),
        "status": snapshot["status"],
    }


def canonical_evidence_payload(snapshot_sha256, evidence):
    return {
        "acquisition": evidence,
        "snapshot_sha256": snapshot_sha256,
    }


def audited_identify_snapshot_primitive(thing):
    """Validate semantic and evidence coordinates and identify both."""
    if not is_thing(thing):
        return audited_invalid_primitive(
            thing, "snapshot", ("thing:invalid",), "corpus:snapshot-invalid"
        )
    value = thing.get("value")
    snapshot = value.get("snapshot") if isinstance(value, dict) else None
    errors = audited_snapshot_errors_primitive(snapshot)
    if errors:
        return audited_invalid_primitive(
            thing, "snapshot", errors, "corpus:snapshot-invalid"
        )
    semantic = canonical_snapshot_payload(snapshot)
    snapshot_sha256 = canonical_sha256(semantic)
    evidence = canonical_evidence_payload(snapshot_sha256, snapshot["evidence"])
    return _result(
        thing,
        {
            "semantic_snapshot": semantic,
            "snapshot_sha256": snapshot_sha256,
            "evidence_sha256": canonical_sha256(evidence),
            "request_sha256": canonical_sha256(semantic["request"]),
            "status": snapshot["status"],
            "acquisition_mode": snapshot["evidence"]["acquisition_mode"],
            "errors": (),
            "ticket": None,
        },
        "corpus:snapshot-identified",
        "valid",
    )


def identify_snapshot(thing):
    """Public Part: one Thing in, one Thing out."""
    return audited_identify_snapshot_primitive(thing)


def audited_fixture_manifest_errors_primitive(manifest):
    """Host control flow for the offline fixture-pack boundary."""
    if not isinstance(manifest, dict):
        return ("fixture:manifest:type",)
    expected = {
        "completion",
        "evidence",
        "format_version",
        "pages",
        "request",
        "retrieval_contract_version",
        "status",
    }
    errors = []
    if set(manifest) != expected:
        errors.append("fixture:manifest:fields")
    if manifest.get("format_version") != FIXTURE_PACK_VERSION:
        errors.append("fixture:manifest:format-version")
    if manifest.get("retrieval_contract_version") != SNAPSHOT_VERSION:
        errors.append("fixture:manifest:retrieval-contract-version")
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        errors.append("fixture:manifest:pages")
        return tuple(errors)
    page_fields = {
        "content_sha256",
        "index",
        "next_cursor",
        "path",
        "request_cursor",
        "retrieval_contract_version",
        "source_url",
    }
    paths = []
    indices = []
    for page in pages:
        if not isinstance(page, dict) or set(page) != page_fields:
            errors.append("fixture:page:declaration")
            continue
        path = page.get("path")
        index = page.get("index")
        paths.append(path)
        indices.append(index)
        if not isinstance(path, str) or not path.startswith("pages/"):
            errors.append("fixture:page:path")
        if not isinstance(index, int) or isinstance(index, bool) or index < 0:
            errors.append("fixture:page:index")
        if not audited_is_sha256_primitive(page.get("content_sha256")):
            errors.append("fixture:page:content-sha256")
        if not isinstance(page.get("source_url"), str) or not page.get("source_url"):
            errors.append("fixture:page:source-url")
        if page.get("retrieval_contract_version") != SNAPSHOT_VERSION:
            errors.append("fixture:page:retrieval-contract-version")
    if len(paths) != len(set(paths)):
        errors.append("fixture:page:duplicate-path")
    if len(indices) != len(set(indices)):
        errors.append("fixture:page:duplicate-index")
    return tuple(errors)


def audited_fixture_page_payload_primitive(page):
    return {
        "format_version": page["format_version"],
        "records": sorted(
            (_canonical_record(record) for record in page["records"]),
            key=lambda record: (
                record["source_identity"],
                canonical_sha256(record["payload"]),
            ),
        ),
        "retrieval_contract_version": page["retrieval_contract_version"],
        "source_url": page["source_url"],
    }


def audited_decode_fixture_pages_primitive(manifest, page_texts):
    """Decode and authenticate supplied page text at one audited boundary."""
    errors = []
    decoded = []
    if not isinstance(page_texts, dict):
        return (), ("fixture:pages:type",)
    for declaration in manifest["pages"]:
        path = declaration["path"]
        text = page_texts.get(path)
        if not isinstance(text, str):
            errors.append(f"fixture:page:missing:{path}")
            continue
        try:
            page = json.loads(text)
        except (json.JSONDecodeError, UnicodeDecodeError):
            errors.append(f"fixture:page:malformed:{path}")
            continue
        expected = {
            "format_version",
            "records",
            "retrieval_contract_version",
            "source_url",
        }
        if not isinstance(page, dict) or set(page) != expected:
            errors.append(f"fixture:page:fields:{path}")
            continue
        if page.get("format_version") != FIXTURE_PAGE_VERSION:
            errors.append(f"fixture:page:format-version:{path}")
        if page.get("retrieval_contract_version") != declaration[
            "retrieval_contract_version"
        ]:
            errors.append(f"fixture:page:retrieval-contract-version:{path}")
        if page.get("source_url") != declaration["source_url"]:
            errors.append(f"fixture:page:source-url:{path}")
        records = page.get("records")
        if not isinstance(records, list):
            errors.append(f"fixture:page:records:{path}")
            continue
        record_errors = tuple(
            error
            for record in records
            for error in audited_record_errors_primitive(record, declaration["index"])
        )
        errors.extend(record_errors)
        if record_errors:
            continue
        canonical_page = audited_fixture_page_payload_primitive(page)
        content_sha256 = canonical_sha256(canonical_page)
        if content_sha256 != declaration["content_sha256"]:
            errors.append(f"fixture:page:sha256:{path}")
            continue
        decoded.append(
            {
                "index": declaration["index"],
                "next_cursor": declaration["next_cursor"],
                "raw_sha256": content_sha256,
                "records": records,
                "request_cursor": declaration["request_cursor"],
            }
        )
    return tuple(decoded), tuple(errors)


def canonical_fixture_manifest_payload(manifest):
    return {
        **manifest,
        "pages": sorted(manifest["pages"], key=lambda page: page["index"]),
        "request": canonical_request_payload(manifest["request"]),
    }


def audited_replay_fixture_pack_primitive(thing):
    """Authenticate offline pages and enter the canonical snapshot contract."""
    if not is_thing(thing):
        return audited_invalid_primitive(
            thing, "fixture_pack", ("thing:invalid",), "corpus:fixture-invalid"
        )
    value = thing.get("value")
    fixture_pack = value.get("fixture_pack") if isinstance(value, dict) else None
    manifest = fixture_pack.get("manifest") if isinstance(fixture_pack, dict) else None
    page_texts = fixture_pack.get("page_texts") if isinstance(fixture_pack, dict) else None
    errors = audited_fixture_manifest_errors_primitive(manifest)
    if errors:
        return audited_invalid_primitive(
            thing, "fixture_pack", errors, "corpus:fixture-invalid"
        )
    pages, errors = audited_decode_fixture_pages_primitive(manifest, page_texts)
    if errors:
        return audited_invalid_primitive(
            thing, "fixture_pack", errors, "corpus:fixture-invalid"
        )
    snapshot = {
        "completion": manifest["completion"],
        "evidence": manifest["evidence"],
        "format_version": manifest["retrieval_contract_version"],
        "pages": list(pages),
        "request": manifest["request"],
        "status": manifest["status"],
    }
    identified = audited_identify_snapshot_primitive(
        {**thing, "value": {"snapshot": snapshot}}
    )
    if identified["state"] == "invalid":
        return identified
    result = identified["value"]
    return _result(
        thing,
        {
            **result,
            "fixture_pack_sha256": canonical_sha256(
                canonical_fixture_manifest_payload(manifest)
            ),
        },
        "corpus:fixture-replayed",
        "valid",
    )


def replay_fixture_pack(thing):
    """Public Part: one offline fixture-pack Thing in, one Thing out."""
    return audited_replay_fixture_pack_primitive(thing)
