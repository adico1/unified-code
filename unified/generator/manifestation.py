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
from ..standard import UEM_VERSION
from ..standard_generate import generate_uem_from_seed_declaration
from .assembly import APPLICATION_VERSION, run_assemble
from .thing_v2 import COMPILER_VERSION, _atomic_publish, run_compile
from .unfold import run_unfold


REGISTRY_VERSION = 1
UNFOLD_VERSION = "UC-UNFOLD-1"
ROUTE_VERSIONS = {
    "application-v3": APPLICATION_VERSION,
    "expression-uem": UEM_VERSION,
    "stateful-unfold": UNFOLD_VERSION,
    "thing-v2": COMPILER_VERSION,
}
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
        "compiler_route": record.get("compiler_route"),
        "compiler_version": record.get("compiler_version"),
        "product_family": record.get("product_family"),
        "route_options": record.get("route_options", {}),
        "seed_id": record.get("seed_id"),
        "seed_path": record.get("seed_path"),
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
    for key in ("seed_id", "seed_path", "product_family", "compiler_route"):
        if not isinstance(record.get(key), str) or not record.get(key):
            errors.append(f"records[{index}].{key}:invalid")
    for key in ("seed_sha256", "artifact_tree_sha256"):
        if not HASH_RE.fullmatch(str(record.get(key, ""))):
            errors.append(f"records[{index}].{key}:invalid")
    route = record.get("compiler_route")
    if route not in ROUTE_VERSIONS:
        errors.append(f"records[{index}].compiler_route:unknown")
    if record.get("compiler_version") != ROUTE_VERSIONS.get(route):
        errors.append(f"records[{index}].compiler_version:conflict")
    if not isinstance(record.get("route_options", {}), dict):
        errors.append(f"records[{index}].route_options:invalid")
    elif route == "application-v3":
        options = record.get("route_options") or {}
        product_key = options.get("product_key")
        suite_ref = options.get("suite_ref")
        if set(options) != {"product_key", "suite_ref"}:
            errors.append(f"records[{index}].route_options:invalid")
        if (
            not isinstance(product_key, str)
            or not SHORT_NAME_RE.fullmatch(product_key)
        ):
            errors.append(f"records[{index}].route_options.product_key:invalid")
        if (
            not isinstance(suite_ref, str)
            or not suite_ref
            or Path(suite_ref).is_absolute()
            or ".." in Path(suite_ref).parts
        ):
            errors.append(f"records[{index}].route_options.suite_ref:invalid")
    elif record.get("route_options"):
        errors.append(f"records[{index}].route_options:unexpected")
    allowed = {
        "artifact_tree_sha256",
        "canonical_name",
        "compiler_route",
        "compiler_version",
        "product_family",
        "route_options",
        "seed_id",
        "seed_path",
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
        "records",
        "registry_snapshot_sha256",
        "registry_version",
    }
    errors.extend(f"registry.unknown:{key}" for key in sorted(set(registry) - allowed))
    if registry.get("registry_version") != REGISTRY_VERSION:
        errors.append("registry_version:invalid")
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
    seed_path = (seed_root / record["seed_path"]).resolve()
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
            "seed_root": str(seed_root),
            "seed_path": str(seed_path),
            "_canonical_seed": seed,
            "manifestation": {"phase": "specified"},
        },
        "boundary:seed:read",
        "manifestation:seed-verified",
    )


def outward_artifact_output_prepare(thing):
    """Named filesystem boundary: validate and prepare the artifact parent."""
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
    return _with_value(
        thing,
        {"output": str(output)},
        "boundary:artifact-output:prepare",
    )


def _without_transient_verification_paths(verification: object) -> object:
    if not isinstance(verification, dict):
        return verification
    seedless_copy = verification.get("seedless_copy")
    normalized_seedless = (
        {
            key: item
            for key, item in seedless_copy.items()
            if key != "path"
        }
        if isinstance(seedless_copy, dict)
        else seedless_copy
    )
    return {
        **verification,
        "seedless_copy": normalized_seedless,
    }


def _route_failure(thing: dict, result: dict, fallback: str) -> dict:
    result_value = result.get("value") if isinstance(result.get("value"), dict) else {}
    return _with_value(
        thing,
        {
            "diagnostics_result": _without_transient_verification_paths(result_value),
            "error": result_value.get("error", fallback),
            "manifestation": {"phase": "planned"},
        },
        "manifestation:compile-failed",
        state="invalid",
    )


def _copy_artifact(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )


def _compile_application_v3(thing: dict) -> dict:
    value = thing["value"]
    record = value["_registry_record"]
    work_root = Path(value["_manifestation_work_root"])
    suite_ref = (record.get("route_options") or {}).get("suite_ref")
    product_key = (record.get("route_options") or {}).get("product_key")
    if not isinstance(suite_ref, str) or not isinstance(product_key, str):
        return _route_failure(thing, {"value": {}}, "application-route-options-invalid")
    suite_path = (Path(value["seed_root"]) / suite_ref).resolve()
    seed_root = Path(value["seed_root"]).resolve()
    if suite_path != seed_root and seed_root not in suite_path.parents:
        return _route_failure(thing, {"value": {}}, "application-suite-reference-invalid")
    suite_output = work_root / "suite"
    request = {
        **thing,
        "value": {
            "suite_path": str(suite_path),
            "output": str(suite_output),
            "build": True,
            "install": True,
            "verify": True,
            "gauntlet_depths": 10,
        },
    }
    compiled = run_assemble(request)
    if compiled.get("state") != "valid":
        return _route_failure(thing, compiled, "application-assembly-failed")
    compiled_value = compiled["value"]
    suite_manifest = compiled_value.get("manifest") or {}
    manifest = (suite_manifest.get("applications") or {}).get(product_key)
    report = (suite_manifest.get("reports") or {}).get(product_key)
    source = suite_output / "applications" / product_key
    if (
        not isinstance(manifest, dict)
        or not isinstance(report, dict)
        or not source.is_dir()
    ):
        return _route_failure(thing, compiled, "application-artifact-missing")
    _copy_artifact(source, Path(value["_artifact_staging"]))
    return _with_value(
        thing,
        {
            "_actual_artifact_tree_sha256": manifest.get("tree_sha256"),
            "verification": report.get("verification"),
            "acceptance_outputs": report.get("acceptance"),
        },
    )


def _compile_thing_v2(thing: dict) -> dict:
    value = thing["value"]
    request = {
        **thing,
        "value": {
            "seed_path": value["seed_path"],
            "output": value["_artifact_staging"],
            "verify": True,
        },
    }
    compiled = run_compile(request)
    if compiled.get("state") != "valid":
        return _route_failure(thing, compiled, "thing-v2-compile-failed")
    compiled_value = compiled["value"]
    return _with_value(
        thing,
        {
            "_actual_artifact_tree_sha256": compiled_value.get("tree_sha256"),
            "verification": _without_transient_verification_paths(
                compiled_value.get("verification")
            ),
            "acceptance_outputs": compiled_value.get("acceptance_outputs"),
        },
    )


def _compile_stateful_unfold(thing: dict) -> dict:
    value = thing["value"]
    request = {
        **thing,
        "value": {
            "command": "unfold",
            "seed_path": value["seed_path"],
            "declaration_path": value["seed_path"],
            "output": value["_artifact_staging"],
            "verify": True,
            "run": True,
        },
    }
    compiled = run_unfold(request)
    if compiled.get("state") != "valid":
        return _route_failure(thing, compiled, "stateful-unfold-failed")
    compiled_value = compiled["value"]
    fixed_point = compiled_value.get("fixed_point") or {}
    return _with_value(
        thing,
        {
            "_actual_artifact_tree_sha256": fixed_point.get("tree_sha256_a"),
            "verification": {
                "fixed_point": fixed_point,
                "generated_tests": compiled_value.get("verify_result"),
                "acceptance": compiled_value.get("run_result"),
                "python_c": compiled_value.get("python_c_result"),
            },
        },
    )


def _tree_identity(root: Path) -> str:
    hashes = {
        path.relative_to(root).as_posix(): sha256_bytes(path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
    }
    return sha256_bytes(canonical_json_bytes(hashes))


def _compile_expression_uem(thing: dict) -> dict:
    value = thing["value"]
    request = {
        **thing,
        "value": {
            "declaration_path": value["seed_path"],
            "out_dir": value["_artifact_staging"],
        },
    }
    compiled = generate_uem_from_seed_declaration(request)
    artifact = Path(value["_artifact_staging"])
    expected = {"program.uem", "program.symbolic.json"}
    present = {path.name for path in artifact.iterdir()} if artifact.is_dir() else set()
    if compiled.get("state") == "invalid" or not expected.issubset(present):
        return _route_failure(thing, compiled, "expression-uem-compile-failed")
    return _with_value(
        thing,
        {
            "_actual_artifact_tree_sha256": _tree_identity(artifact),
            "verification": {
                "generated": True,
                "program_uem": "program.uem" in present,
                "symbolic": "program.symbolic.json" in present,
            },
        },
    )


COMPILER_ROUTES = {
    "application-v3": _compile_application_v3,
    "expression-uem": _compile_expression_uem,
    "stateful-unfold": _compile_stateful_unfold,
    "thing-v2": _compile_thing_v2,
}


def outward_compile_route(thing):
    """Named compiler boundary: dispatch only by registered generic route."""
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    if (value.get("manifestation") or {}).get("phase") != "specified":
        return thing
    output = Path(value["output"])
    work_root = output.parent / f".{output.name}.manifestation-diagnostics"
    if work_root.exists():
        shutil.rmtree(work_root)
    work_root.mkdir()
    artifact_staging = work_root / "artifact"
    requested = _with_value(
        thing,
        {
            "manifestation": {"phase": "planned"},
            "_manifestation_work_root": str(work_root),
            "_artifact_staging": str(artifact_staging),
            "diagnostics": str(work_root),
        },
        "manifestation:compile-requested",
        state="formed",
    )
    record = value["_registry_record"]
    compiled = COMPILER_ROUTES[record["compiler_route"]](requested)
    if compiled.get("state") == "invalid":
        return compiled
    compiled_value = compiled.get("value") or {}
    actual = compiled_value.get("_actual_artifact_tree_sha256")
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
        "compiler_version": record["compiler_version"],
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
        "compiler_version": record["compiler_version"],
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
        outward_compile_route(
            outward_artifact_output_prepare(
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
    """Resolve and manifest one registered artifact. Public Part: Thing → Thing."""
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
        if isinstance(node, ast.keyword) and node.arg == "state":
            if isinstance(node.value, ast.Name) and node.value.id in {
                "resolution",
                "status",
            }:
                overloads.append(f"state-keyword:{node.value.id}")
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.slice, ast.Constant)
                    and target.slice.value == "state"
                ):
                    overloads.append("state-direct-assignment")
        if isinstance(node, ast.Name) and node.id in {
            "get_close_matches",
            "SequenceMatcher",
        }:
            selection_hits.append(node.id)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"startswith", "endswith"}
            and (
                (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id in {"query", "record"}
                )
                or any(
                    isinstance(argument, ast.Name)
                    and argument.id in {"query", "record"}
                    for argument in node.args
                )
            )
        ):
            selection_hits.append(node.func.attr)
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


GENERIC_VOCABULARY = frozenset(
    {
        "acceptance", "action", "actions", "adapter", "and", "any", "append",
        "application", "are", "arg", "argument", "arguments", "artifact",
        "atomically", "boolean", "boundary", "build", "bytes", "canonical",
        "collect", "command", "commands", "compile", "compiler", "composition", "constant",
        "core", "data", "declaration", "default", "dependency", "description",
        "deterministic", "effect", "empty", "encoding", "error", "errors",
        "evidence", "expected", "extend", "failed", "false", "field", "fields", "file",
        "files", "filesystem", "format", "formed", "from", "generated",
        "generic", "guard", "guards", "identity", "index", "input", "inside", "int",
        "integer", "invalid", "item", "items", "json", "key", "keys", "kind",
        "len", "li" + "st", "literal", "manifest", "message", "mode", "mutation",
        "name", "native", "none", "not", "object", "one", "only", "open",
        "operation", "operations", "options", "order", "output", "package", "parse", "part",
        "parameter", "parameters", "path", "persistence", "prepare", "present",
        "phase", "processing", "program", "projection", "proof", "raw", "read",
        "record", "registry", "replace", "representation", "request", "require",
        "required", "result", "root", "route", "runtime", "schema", "seed",
        "selected", "set", "source", "stage", "str", "strings", "sum",
        "sha256", "state", "status", "string", "target", "test", "tests", "text", "the",
        "thing", "token", "total", "transformation", "tree", "true", "two", "type",
        "uem", "unavailable", "unknown", "valid", "validate", "validation",
        "value", "values", "verify", "version", "word", "words",
    }
)


def manifestation_application_vocabulary(seeds: tuple[dict, ...]) -> tuple[str, ...]:
    """Derive non-generic application words from every registered proof seed."""
    strings = []

    def collect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                strings.append(str(key))
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, str):
            strings.append(value)

    for seed in seeds:
        collect(seed)
    words = {
        word.lower()
        for value in strings
        for word in re.split(r"[^A-Za-z0-9]+", value)
        if len(word) > 2
        and word[0].isalpha()
        and not word.isdigit()
        and not re.fullmatch(r"[0-9a-fA-F]{32,}", word)
    }
    return tuple(sorted(words - GENERIC_VOCABULARY))


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
    vocabulary = manifestation_application_vocabulary(seeds)
    hits = sorted(term for term in vocabulary if term in tokens)
    return {
        "ok": not hits,
        "vocabulary": list(vocabulary),
        "hits": hits,
    }


def manifestation_mutation_report(seeds: tuple[dict, ...]) -> dict:
    source = inspect.getsource(inspect.getmodule(manifest_artifact))
    cases = []
    for term in manifestation_application_vocabulary(seeds):
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
        "canonical-state-variable-overload": (
            "\ndef mutant(thing, status):\n"
            "    return _with_value(thing, {}, state=status)\n"
        ),
        "canonical-state-direct-assignment": (
            "\ndef mutant(thing, status):\n"
            '    thing["state"] = status\n'
            "    return thing\n"
        ),
        "fuzzy-selection": "\nMUTANT = get_close_matches\n",
        "prefix-fuzzy-selection": (
            "\ndef mutant(query, record):\n"
            "    return record.startswith(query)\n"
        ),
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
