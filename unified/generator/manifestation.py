"""Deterministic qualified-name resolution and Thing v2 artifact manifestation.

The two public Parts are ``resolve_name(thing)`` and
``manifest_artifact(thing)``. Filesystem access is confined to explicitly
named boundary helpers. Resolution outcomes remain domain data inside
``thing["value"]`` and never replace the canonical Thing state vocabulary.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import re
import shutil
import tempfile
from pathlib import Path

from ..thing import is_thing
from .thing_v2 import (
    COMPILER_VERSION,
    _atomic_publish,
    proof_application_vocabulary,
    run_compile,
)


REGISTRY_VERSION = 1
QUALIFIED_NAME_RE = re.compile(
    r"^uc://applications/(?P<name>[a-z][a-z0-9-]*)@(?P<version>[1-9][0-9]*)$"
)
SHORT_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
RESOLUTION_STATUSES = frozenset(
    {
        "unresolved",
        "resolved",
        "unknown",
        "ambiguous",
        "unavailable",
        "conflict",
    }
)
CANONICAL_STATES = frozenset(
    {"unknown", "absent", "false", "formed", "valid", "invalid"}
)


def canonical_json_bytes(value) -> bytes:
    """Return the repository's canonical JSON representation."""
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_seed_sha256(seed: dict) -> str:
    return sha256_bytes(canonical_json_bytes(seed))


def _ticket_payload(error_type: str) -> dict:
    identity = sha256_bytes(f"manifestation:{error_type}".encode("utf-8"))
    return {
        "ticket_id": identity,
        "correlation_id": identity,
        "message": "[redacted-message]",
        "error_type": error_type,
    }


def _canonical_record(record: dict) -> dict:
    return {
        "artifact_tree_sha256": record.get("artifact_tree_sha256"),
        "canonical_name": record.get("canonical_name"),
        "compiler_version": record.get("compiler_version"),
        "seed_id": record.get("seed_id"),
        "seed_ref": record.get("seed_ref"),
        "seed_sha256": record.get("seed_sha256"),
    }


def canonical_registry_payload(registry: dict) -> dict:
    """Normalize record order and exclude the registry's self-identity field."""
    records = registry.get("records")
    normalized = (
        sorted(
            (_canonical_record(record) for record in records),
            key=lambda record: (
                str(record.get("canonical_name")),
                str(record.get("seed_id")),
            ),
        )
        if isinstance(records, list)
        else records
    )
    return {
        "compiler_version": registry.get("compiler_version"),
        "records": normalized,
        "registry_version": registry.get("registry_version"),
    }


def registry_snapshot_sha256(registry: dict) -> str:
    return sha256_bytes(canonical_json_bytes(canonical_registry_payload(registry)))


def _with_value(thing: dict, updates: dict, *marks: str, state: str | None = None):
    value = thing.get("value")
    current = value if isinstance(value, dict) else {}
    return {
        **thing,
        "value": {**current, **updates},
        "evidence": (*thing.get("evidence", ()), *marks),
        "state": thing["state"] if state is None else state,
    }


def _resolution(
    thing: dict,
    status: str,
    error: str | None,
    *marks: str,
    state: str = "valid",
    record: dict | None = None,
) -> dict:
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    identity = dict(value.get("identity") or {})
    if record:
        identity = {
            **identity,
            "canonical_name": record["canonical_name"],
            "seed_id": record["seed_id"],
            "seed_sha256": record["seed_sha256"],
            "compiler_version": record["compiler_version"],
        }
    return _with_value(
        thing,
        {
            "identity": identity,
            "resolution": {
                "status": status,
                "error": error,
            },
            "manifestation": {
                **dict(value.get("manifestation") or {}),
                "phase": "resolved" if status == "resolved" else "addressed",
            },
            "ticket": None,
            "_registry_record": record,
        },
        *marks,
        state=state,
    )


def _invalid_non_thing(raw, mark: str) -> dict:
    return {
        "value": raw,
        "depths": (),
        "axes": (),
        "evidence": (mark,),
        "state": "invalid",
    }


def _unhandled(thing: dict, operation: str, error_type: str) -> dict:
    ticket = _ticket_payload(error_type)
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    return _with_value(
        thing,
        {
            **value,
            "error": "unhandled-failure",
            "operation": operation,
            "message": "[redacted-message]",
            "ticket": ticket,
        },
        "ticket.open",
        "processing.failed",
        state="invalid",
    )


def outward_registry_read(thing):
    """Named filesystem boundary: read and parse the pinned registry."""
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    registry_path = value.get("registry_path")
    if not isinstance(registry_path, str) or not registry_path:
        return _resolution(
            thing,
            "unavailable",
            "registry-not-provided",
            "resolution:registry-missing",
            "resolution:unavailable",
        )
    path = Path(registry_path).expanduser().resolve()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return _resolution(
            _with_value(
                thing,
                {"registry_path": str(path)},
                "boundary:registry:read",
            ),
            "unavailable",
            "registry-unavailable",
            "resolution:registry-unavailable",
            "resolution:unavailable",
        )
    try:
        registry = json.loads(raw)
    except ValueError:
        return _resolution(
            _with_value(
                thing,
                {"registry_path": str(path)},
                "boundary:registry:read",
            ),
            "conflict",
            "registry-invalid-json",
            "resolution:registry-invalid",
            "resolution:conflict",
            state="invalid",
        )
    return _with_value(
        thing,
        {
            "registry_path": str(path),
            "_registry": registry,
        },
        "boundary:registry:read",
    )


def _validate_record(record: object, index: int) -> list[str]:
    if not isinstance(record, dict):
        return [f"records[{index}]:not-object"]
    errors = []
    qualified = record.get("canonical_name")
    if not isinstance(qualified, str) or not QUALIFIED_NAME_RE.fullmatch(qualified):
        errors.append(f"records[{index}].canonical_name:invalid")
    for key in ("seed_id", "seed_ref"):
        if not isinstance(record.get(key), str) or not record.get(key):
            errors.append(f"records[{index}].{key}:invalid")
    for key in ("seed_sha256", "artifact_tree_sha256"):
        if not HASH_RE.fullmatch(str(record.get(key, ""))):
            errors.append(f"records[{index}].{key}:invalid")
    if record.get("compiler_version") != COMPILER_VERSION:
        errors.append(f"records[{index}].compiler_version:conflict")
    allowed = {
        "artifact_tree_sha256",
        "canonical_name",
        "compiler_version",
        "seed_id",
        "seed_ref",
        "seed_sha256",
    }
    errors.extend(
        f"records[{index}].unknown:{key}"
        for key in sorted(set(record) - allowed)
    )
    return errors


def validate_registry(registry: object) -> list[str]:
    if not isinstance(registry, dict):
        return ["registry:not-object"]
    errors = []
    allowed = {
        "compiler_version",
        "records",
        "registry_snapshot_sha256",
        "registry_version",
    }
    errors.extend(f"registry.unknown:{key}" for key in sorted(set(registry) - allowed))
    if registry.get("registry_version") != REGISTRY_VERSION:
        errors.append("registry_version:invalid")
    if registry.get("compiler_version") != COMPILER_VERSION:
        errors.append("compiler_version:conflict")
    records = registry.get("records")
    if not isinstance(records, list) or not records:
        errors.append("records:empty")
        return sorted(errors)
    for index, record in enumerate(records):
        errors.extend(_validate_record(record, index))
    names = [
        record.get("canonical_name")
        for record in records
        if isinstance(record, dict)
    ]
    seed_ids = [
        record.get("seed_id")
        for record in records
        if isinstance(record, dict)
    ]
    if len(names) != len(set(names)):
        errors.append("records:duplicate-canonical-name")
    if len(seed_ids) != len(set(seed_ids)):
        errors.append("records:duplicate-seed-id")
    embedded = registry.get("registry_snapshot_sha256")
    if not HASH_RE.fullmatch(str(embedded or "")):
        errors.append("registry_snapshot_sha256:invalid")
    return sorted(errors)


def _verify_registry(thing: dict) -> dict:
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    registry = value.get("_registry")
    resolution = value.get("resolution") or {}
    if resolution.get("status") in RESOLUTION_STATUSES:
        return thing
    errors = validate_registry(registry)
    if errors:
        conflict = (
            "registry-identity-conflict"
            if any("duplicate-" in error for error in errors)
            else "registry-schema-invalid"
        )
        return _resolution(
            _with_value(thing, {"registry_errors": errors}),
            "conflict",
            conflict,
            "resolution:registry-invalid",
            "resolution:conflict",
            state="invalid",
        )
    computed = registry_snapshot_sha256(registry)
    embedded = registry["registry_snapshot_sha256"]
    expected = value.get("expected_registry_snapshot_sha256")
    if not HASH_RE.fullmatch(str(expected or "")):
        return _resolution(
            thing,
            "unresolved",
            "registry-snapshot-not-pinned",
            "resolution:snapshot-unpinned",
            "resolution:unresolved",
            state="invalid",
        )
    if computed != embedded or computed != expected:
        return _resolution(
            _with_value(thing, {"computed_registry_snapshot_sha256": computed}),
            "conflict",
            "registry-snapshot-mismatch",
            "resolution:snapshot-mismatch",
            "resolution:conflict",
            state="invalid",
        )
    return _with_value(
        thing,
        {
            "registry_snapshot_sha256": computed,
        },
        "resolution:registry-verified",
    )


def _select_record(thing: dict) -> dict:
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    resolution = value.get("resolution") or {}
    if resolution.get("status") in RESOLUTION_STATUSES:
        return thing
    query = value.get("name")
    if not isinstance(query, str) or not query:
        return _resolution(
            thing,
            "unresolved",
            "name-not-provided",
            "resolution:name-invalid",
            "resolution:unresolved",
            state="invalid",
        )
    records = value["_registry"]["records"]
    qualified = QUALIFIED_NAME_RE.fullmatch(query)
    if qualified:
        matches = [
            record for record in records if record["canonical_name"] == query
        ]
        if len(matches) == 1:
            return _resolution(
                thing,
                "resolved",
                None,
                "manifestation:resolved",
                record=matches[0],
            )
        return _resolution(
            thing,
            "unknown",
            "qualified-name-unknown",
            "resolution:unknown",
        )
    if SHORT_NAME_RE.fullmatch(query):
        matches = [
            record
            for record in records
            if QUALIFIED_NAME_RE.fullmatch(record["canonical_name"]).group("name")
            == query
        ]
        if len(matches) > 1:
            return _resolution(
                _with_value(
                    thing,
                    {
                        "resolution_matches": sorted(
                            record["canonical_name"] for record in matches
                        )
                    },
                ),
                "ambiguous",
                "short-name-ambiguous",
                "resolution:ambiguous",
            )
        return _resolution(
            thing,
            "unresolved",
            "short-name-requires-explicit-version",
            "resolution:version-required",
            "resolution:unresolved",
        )
    return _resolution(
        thing,
        "unknown",
        "qualified-name-unknown",
        "resolution:unknown",
    )


def _resolution_pipeline(thing: dict) -> dict:
    addressed = _with_value(
        thing,
        {
            "manifestation": {
                **dict(
                    (thing.get("value") or {}).get("manifestation") or {}
                    if isinstance(thing.get("value"), dict)
                    else {}
                ),
                "phase": "addressed",
            },
            "ticket": None,
        },
        "manifestation:addressed",
        state="formed",
    )
    return _select_record(_verify_registry(outward_registry_read(addressed)))


def _guard_resolution(thing) -> dict:
    if not is_thing(thing):
        return _invalid_non_thing(thing, "resolution:rejected-non-thing")
    if thing.get("state") in {"invalid", "absent", "false"}:
        return {
            **thing,
            "evidence": (*thing["evidence"], "resolution:skipped"),
        }
    value = thing.get("value")
    if isinstance(value, dict) and value.get("error"):
        return _resolution(
            thing,
            "unresolved",
            str(value["error"]),
            "resolution:argv-invalid",
            "resolution:unresolved",
            state="invalid",
        )
    try:
        return _resolution_pipeline(thing)
    except Exception as exc:
        return _unhandled(thing, "resolve_name", type(exc).__name__)


def _without_internal_values(thing: dict) -> dict:
    value = thing.get("value")
    if not isinstance(value, dict):
        return thing
    public = {
        key: item
        for key, item in value.items()
        if not key.startswith("_")
    }
    return {**thing, "value": public}


def resolve_name(thing):
    """Resolve one pinned name request. Public Part: Thing → Thing."""
    return _without_internal_values(_guard_resolution(thing))


def outward_seed_read(thing):
    """Named filesystem boundary: read and canonically verify the resolved seed."""
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    if (value.get("resolution") or {}).get("status") != "resolved":
        return thing
    record = value.get("_registry_record") or {}
    registry_path = Path(value["registry_path"])
    seed_root_raw = value.get("seed_root")
    seed_root = (
        Path(seed_root_raw).expanduser().resolve()
        if isinstance(seed_root_raw, str) and seed_root_raw
        else registry_path.parent.resolve()
    )
    seed_path = (seed_root / record["seed_ref"]).resolve()
    if seed_root != seed_path and seed_root not in seed_path.parents:
        return _with_value(
            thing,
            {
                "error": "unsafe-seed-reference",
                "manifestation": {"phase": "resolved"},
            },
            "boundary:seed:read",
            "manifestation:seed-reference-invalid",
            state="invalid",
        )
    try:
        raw_seed = seed_path.read_text(encoding="utf-8")
    except OSError:
        return _with_value(
            thing,
            {
                "seed_path": str(seed_path),
                "manifestation": {
                    "phase": "resolved",
                    "error": "seed-unavailable",
                },
            },
            "boundary:seed:read",
            "manifestation:seed-unavailable",
            state="valid",
        )
    try:
        seed = json.loads(raw_seed)
    except ValueError:
        return _with_value(
            thing,
            {
                "seed_path": str(seed_path),
                "error": "seed-invalid-json",
                "manifestation": {"phase": "resolved"},
            },
            "boundary:seed:read",
            "manifestation:seed-invalid",
            state="invalid",
        )
    if not isinstance(seed, dict):
        return _with_value(
            thing,
            {
                "seed_path": str(seed_path),
                "error": "seed-not-object",
                "manifestation": {"phase": "resolved"},
            },
            "boundary:seed:read",
            "manifestation:seed-invalid",
            state="invalid",
        )
    actual = canonical_seed_sha256(seed)
    if actual != record["seed_sha256"]:
        return _with_value(
            thing,
            {
                "seed_path": str(seed_path),
                "computed_seed_sha256": actual,
                "error": "seed-hash-mismatch",
                "manifestation": {"phase": "resolved"},
            },
            "boundary:seed:read",
            "manifestation:seed-hash-mismatch",
            state="invalid",
        )
    return _with_value(
        thing,
        {
            "seed_path": str(seed_path),
            "_canonical_seed": seed,
            "manifestation": {"phase": "specified"},
        },
        "boundary:seed:read",
        "manifestation:seed-verified",
    )


def _safe_artifact_output(thing: dict) -> dict:
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    if (value.get("manifestation") or {}).get("phase") != "specified":
        return thing
    output_raw = value.get("output")
    if not isinstance(output_raw, str) or not output_raw:
        return _with_value(
            thing,
            {
                "error": "artifact-output-not-provided",
                "manifestation": {"phase": "specified"},
            },
            "manifestation:output-invalid",
            state="invalid",
        )
    output = Path(output_raw).expanduser().resolve()
    registry_path = Path(value["registry_path"]).resolve()
    seed_path = Path(value["seed_path"]).resolve()
    unsafe = (
        output == Path(output.anchor)
        or output == registry_path
        or output == seed_path
        or output in registry_path.parents
        or output in seed_path.parents
    )
    if unsafe or (output.exists() and not output.is_dir()):
        return _with_value(
            thing,
            {
                "output": str(output),
                "error": "unsafe-artifact-output",
                "manifestation": {"phase": "specified"},
            },
            "manifestation:output-invalid",
            state="invalid",
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    return _with_value(thing, {"output": str(output)})


def outward_compile_thing_v2(thing):
    """Named compiler boundary: invoke the existing Thing v2 compiler once."""
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    if (value.get("manifestation") or {}).get("phase") != "specified":
        return thing
    output = Path(value["output"])
    work_root = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.manifestation-", dir=output.parent)
    )
    canonical_seed_path = work_root / "seed.json"
    artifact_staging = work_root / "artifact"
    canonical_seed_path.write_bytes(canonical_json_bytes(value["_canonical_seed"]))
    requested = _with_value(
        thing,
        {
            "seed_path": str(canonical_seed_path),
            "output": str(artifact_staging),
            "verify": True,
            "manifestation": {"phase": "planned"},
            "_manifestation_work_root": str(work_root),
            "_artifact_staging": str(artifact_staging),
            "diagnostics": str(work_root),
        },
        "manifestation:compile-requested",
        state="formed",
    )
    compiled = run_compile(requested)
    if compiled.get("state") != "valid":
        return _with_value(
            compiled,
            {
                "manifestation": {"phase": "planned"},
                "error": (compiled.get("value") or {}).get(
                    "error", "thing-v2-compile-failed"
                ),
            },
            "manifestation:compile-failed",
            state="invalid",
        )
    compiled_value = compiled.get("value") or {}
    record = value["_registry_record"]
    actual = compiled_value.get("tree_sha256")
    if actual != record["artifact_tree_sha256"]:
        return _with_value(
            compiled,
            {
                "computed_artifact_tree_sha256": actual,
                "error": "artifact-tree-hash-mismatch",
                "manifestation": {"phase": "compiled"},
            },
            "manifestation:compiled",
            "manifestation:artifact-hash-mismatch",
            state="invalid",
        )
    return _with_value(
        compiled,
        {
            "manifestation": {"phase": "verified"},
            "_final_output": str(output),
        },
        "manifestation:compiled",
        "manifestation:artifact-verified",
        state="formed",
    )


def outward_artifact_publish(thing):
    """Named artifact boundary: atomically publish only a verified tree."""
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    if (value.get("manifestation") or {}).get("phase") != "verified":
        return thing
    staging = Path(value["_artifact_staging"])
    output = Path(value["_final_output"])
    try:
        _atomic_publish(staging, output)
    except OSError:
        return _with_value(
            thing,
            {
                "error": "artifact-publish-failed",
                "manifestation": {"phase": "verified"},
            },
            "boundary:artifact:publish",
            "manifestation:publish-failed",
            state="invalid",
        )
    work_root = Path(value["_manifestation_work_root"])
    shutil.rmtree(work_root, ignore_errors=True)
    record = value["_registry_record"]
    identity = {
        "registry_snapshot_sha256": value["registry_snapshot_sha256"],
        "canonical_name": record["canonical_name"],
        "seed_id": record["seed_id"],
        "seed_sha256": record["seed_sha256"],
        "compiler_version": COMPILER_VERSION,
        "artifact_tree_sha256": record["artifact_tree_sha256"],
    }
    result = {
        "identity": identity,
        "resolution": {"status": "resolved", "error": None},
        "manifestation": {
            "phase": "manifested",
            "artifact_id": f"sha256:{record['artifact_tree_sha256']}",
        },
        "artifact_path": str(output),
        "artifact_tree_sha256": record["artifact_tree_sha256"],
        "compiler_version": COMPILER_VERSION,
        "registry_snapshot_sha256": value["registry_snapshot_sha256"],
        "seed_id": record["seed_id"],
        "seed_sha256": record["seed_sha256"],
        "ticket": None,
        "verification": value.get("verification"),
        "acceptance_outputs": value.get("acceptance_outputs"),
    }
    return {
        **thing,
        "value": result,
        "evidence": (
            *thing["evidence"],
            "boundary:artifact:publish",
            "manifestation:manifested",
        ),
        "state": "valid",
    }


def _manifestation_pipeline(thing: dict) -> dict:
    return outward_artifact_publish(
        outward_compile_thing_v2(
            _safe_artifact_output(
                outward_seed_read(
                    _resolution_pipeline(thing)
                )
            )
        )
    )


def _guard_manifestation(thing) -> dict:
    if not is_thing(thing):
        return _invalid_non_thing(thing, "manifestation:rejected-non-thing")
    if thing.get("state") in {"invalid", "absent", "false"}:
        return {
            **thing,
            "evidence": (*thing["evidence"], "manifestation:skipped"),
        }
    value = thing.get("value")
    if isinstance(value, dict) and value.get("error"):
        return _resolution(
            thing,
            "unresolved",
            str(value["error"]),
            "manifestation:argv-invalid",
            "resolution:unresolved",
            state="invalid",
        )
    try:
        return _manifestation_pipeline(thing)
    except Exception as exc:
        return _unhandled(thing, "manifest_artifact", type(exc).__name__)


def manifest_artifact(thing):
    """Resolve and manifest one Thing v2 artifact. Public Part: Thing → Thing."""
    return _without_internal_values(_guard_manifestation(thing))


def manifestation_source_report(source: str | None = None) -> dict:
    """Detect state overloading and prohibited implicit/fuzzy selection."""
    text = (
        inspect.getsource(inspect.getmodule(manifest_artifact))
        if source is None
        else source
    )
    tree = ast.parse(text)
    overloads = []
    selection_hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            pairs = zip(node.keys, node.values)
            for key, value in pairs:
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "state"
                    and isinstance(value, ast.Constant)
                    and value.value in RESOLUTION_STATUSES
                ):
                    overloads.append(str(value.value))
        if isinstance(node, ast.Name) and node.id in {
            "get_close_matches",
            "SequenceMatcher",
        }:
            selection_hits.append(node.id)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "split"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "@"
        ):
            selection_hits.append("split-version")
    return {
        "ok": not overloads and not selection_hits,
        "state_overloads": sorted(overloads),
        "selection_hits": sorted(selection_hits),
    }


def manifestation_vocabulary_report(
    seeds: tuple[dict, ...],
    source: str | None = None,
) -> dict:
    text = (
        inspect.getsource(inspect.getmodule(manifest_artifact))
        if source is None
        else source
    )
    tokens = {
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", text)
    }
    vocabulary = proof_application_vocabulary(seeds)
    hits = sorted(term for term in vocabulary if term in tokens)
    return {
        "ok": not hits,
        "vocabulary": list(vocabulary),
        "hits": hits,
    }


def manifestation_mutation_report(seeds: tuple[dict, ...]) -> dict:
    source = inspect.getsource(inspect.getmodule(manifest_artifact))
    cases = []
    for term in proof_application_vocabulary(seeds):
        report = manifestation_vocabulary_report(seeds, source + f"\n{term}\n")
        cases.append(
            {
                "kind": "application-vocabulary",
                "mutation": term,
                "detected": term in report["hits"],
            }
        )
    semantic_mutations = {
        "canonical-state-overload": '\nMUTANT = {"state": "ambiguous"}\n',
        "fuzzy-selection": "\nMUTANT = get_close_matches\n",
        "silent-version-selection": '\nMUTANT = query.split("@")[0]\n',
    }
    for name, mutation in semantic_mutations.items():
        report = manifestation_source_report(source + mutation)
        cases.append(
            {
                "kind": "semantic",
                "mutation": name,
                "detected": not report["ok"],
            }
        )
    return {
        "ok": bool(cases) and all(case["detected"] for case in cases),
        "detected": sum(case["detected"] for case in cases),
        "total": len(cases),
        "cases": cases,
    }
