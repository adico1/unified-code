#!/usr/bin/env python3
"""Minimal pre-bootstrap verifier and deterministic Stage-1 handoff planner.

This file is intentionally standalone and Python-standard-library only.  It is
part of the explicitly pinned Stage-0 trust base, not the post-bootstrap
Unified Code implementation.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path, PurePosixPath

STAGE0_VERSION = "UC-STAGE0-1"
CANONICAL_JSON_VERSION = "UC-CANONICAL-JSON-1"
THING_STATES = frozenset({"unknown", "absent", "false", "formed", "valid", "invalid"})
REQUIRED_ROLES = frozenset(
    {
        "root-seed",
        "root-seed-schema",
        "stage0-contract-schema",
        "stage1-handoff-schema",
        "stage0-generation-manifest-schema",
        "stage0-executable",
    }
)
ALLOWED_HASH_MODES = frozenset({"canonical-json", "raw-bytes"})
ALLOWED_OPERATIONS = (
    "canonicalize-json",
    "sha256",
    "validate-contract",
    "validate-root-seed",
    "validate-path",
    "read-trusted-input",
    "plan-stage1-handoff",
    "interpret-stage1-declaration",
    "render-stage1-boilerplate",
    "hash-stage1-tree",
    "atomic-publish",
)
PROHIBITED_CAPABILITIES = (
    "application-domain-behavior",
    "dynamic-code-loading",
    "environment-dependent-selection",
    "fuzzy-name-resolution",
    "network-access",
    "process-execution",
    "randomness",
    "time-dependent-output",
    "unverified-input-copy",
)

STAGE1_OPERATIONS = (
    "canonicalize-json",
    "resolve-seed-node",
    "render-canonical-json",
    "render-utf8-lines",
    "render-hex-bytes",
    "resolve-projection-dependencies",
    "render-stage1-runner",
    "hash-file",
    "hash-tree",
    "write-manifest",
    "atomic-publish",
)

STAGE1_TEMPLATE = '''#!/usr/bin/env python3
"""Generated seed-defined Stage-1 framework/generator runner."""

import hashlib
import json
import shutil
import sys
from pathlib import Path, PurePosixPath

BOILERPLATE_ID = "UC-STAGE1-PY-1"
OPERATIONS = (
    "canonicalize-json",
    "resolve-seed-node",
    "render-canonical-json",
    "render-utf8-lines",
    "render-hex-bytes",
    "resolve-projection-dependencies",
    "render-stage1-runner",
    "hash-file",
    "hash-tree",
    "write-manifest",
    "atomic-publish",
)
TEMPLATE = __TEMPLATE_REPR__


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\\n").encode("utf-8")


def pairs_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate-json-key")
        result[key] = value
    return result


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_path(raw):
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("invalid-output-path")
    return path


def resolve(root, pointer):
    if pointer == "/":
        return root
    parts = pointer.split("/")[1:]
    if not pointer.startswith("/") or not parts:
        raise ValueError("unsupported-seed-node")
    value = root
    for part in parts:
        if not isinstance(value, dict) or part not in value:
            raise ValueError("unsupported-seed-node")
        value = value[part]
    return value


def render_canonical_json(value):
    return canonical(value)


def render_utf8_lines(value):
    if not isinstance(value, list) or not all(isinstance(line, str) for line in value):
        raise ValueError("unsupported-utf8-lines")
    return ("\\n".join(value) + "\\n").encode("utf-8")


def render_hex_bytes(value):
    if not isinstance(value, str):
        raise ValueError("unsupported-hex-bytes")
    try:
        return bytes.fromhex(value)
    except ValueError as error:
        raise ValueError("unsupported-hex-bytes") from error


RENDERERS = {
    "canonical-json": render_canonical_json,
    "utf8-lines": render_utf8_lines,
    "hex-bytes": render_hex_bytes,
}


def validate_repository(seed):
    repository = seed.get("repository")
    if (
        not isinstance(repository, dict)
        or set(repository) != {
            "format_version",
            "renderers",
            "generation_bound",
            "depths",
            "watchers",
            "summary_lines",
            "projections",
        }
        or repository["format_version"] != "UC-ROOT-REPOSITORY-1"
        or repository["renderers"] != list(RENDERERS)
        or repository["generation_bound"] != 3
        or repository["depths"] != list(range(1, 11))
        or not isinstance(repository["watchers"], list)
        or [item.get("depth") for item in repository["watchers"] if isinstance(item, dict)] != list(range(1, 11))
        or any(set(item) != {"id", "depth"} or not isinstance(item["id"], str) or not item["id"] for item in repository["watchers"])
        or len({item["id"] for item in repository["watchers"]}) != 10
        or not isinstance(repository["summary_lines"], list)
        or not all(isinstance(line, str) for line in repository["summary_lines"])
        or not isinstance(repository["projections"], list)
    ):
        raise ValueError("unsupported-repository-declaration")
    return repository


def render_runner():
    token = "__TEMPLATE" + "_REPR__"
    return TEMPLATE.replace(token, repr(TEMPLATE)).encode("utf-8")


def validate(seed):
    if not isinstance(seed, dict) or seed.get("standard_version") != "TEN-1":
        raise ValueError("invalid-root-seed")
    stage1 = seed.get("stage1")
    if not isinstance(stage1, dict) or set(stage1) != {"format_version", "framework", "generator", "uem"}:
        raise ValueError("unsupported-stage1-declaration")
    generator = stage1["generator"]
    framework = stage1["framework"]
    uem = stage1["uem"]
    if (
        stage1["format_version"] != "UC-STAGE1-SEED-1"
        or not isinstance(generator, dict)
        or generator.get("boilerplate") != BOILERPLATE_ID
        or tuple(generator.get("operations") or ()) != OPERATIONS
        or not isinstance(generator.get("outputs"), list)
    ):
        raise ValueError("standard.gap:unsupported-stage1-operation")
    if (
        not isinstance(framework, dict)
        or set(framework) != {"standard_version", "thing_fields", "thing_states", "laws"}
        or framework["standard_version"] != "TEN-1"
        or framework["thing_fields"] != ["value", "depths", "axes", "evidence", "state"]
        or framework["thing_states"] != ["unknown", "absent", "false", "formed", "valid", "invalid"]
        or framework["laws"] != ["L" + str(index) for index in range(1, 14)]
    ):
        raise ValueError("unsupported-framework-declaration")
    if (
        not isinstance(uem, dict)
        or set(uem) != {"machine", "format_version", "opcodes", "primitive_registry_version", "primitives"}
        or uem["machine"] != "UEM-16"
        or uem["format_version"] != 1
        or uem["primitive_registry_version"] != 2
        or not isinstance(uem["opcodes"], list)
        or [item.get("code") for item in uem["opcodes"] if isinstance(item, dict)] != list(range(1, 17))
        or any(set(item) != {"code", "name"} or not isinstance(item["name"], str) or not item["name"] for item in uem["opcodes"])
        or not isinstance(uem["primitives"], list)
        or not uem["primitives"]
        or len(uem["primitives"]) != len(set(uem["primitives"]))
        or any(not isinstance(item, str) or not item for item in uem["primitives"])
    ):
        raise ValueError("unsupported-uem-declaration")
    validate_repository(seed)
    return stage1


def tree_hash(inventory):
    raw = "".join(
        item["path"] + "\\0" + item["sha256"] + "\\n"
        for item in sorted(inventory, key=lambda item: item["path"])
    ).encode("utf-8")
    return sha(raw)


def render(seed):
    stage1 = validate(seed)
    outputs = stage1["generator"]["outputs"] + seed["repository"]["projections"]
    files = {"stage1.py": render_runner()}
    origins = {"stage1.py": ["/stage1/generator"]}
    seen = {"stage1.py"}
    for output in outputs:
        if not isinstance(output, dict) or set(output) != {"path", "seed_node", "renderer", "depends_on"}:
            raise ValueError("unsupported-output-declaration")
        path = safe_path(output["path"]).as_posix()
        dependencies = output["depends_on"]
        if (
            path in seen
            or output["renderer"] not in RENDERERS
            or not isinstance(dependencies, list)
            or not all(isinstance(item, str) and item in seen for item in dependencies)
        ):
            raise ValueError("unsupported-output-declaration")
        seen.add(path)
        files[path] = RENDERERS[output["renderer"]](resolve(seed, output["seed_node"]))
        origins[path] = [output["seed_node"]]
    inventory = [
        {
            "path": path,
            "sha256": sha(raw),
            "size": len(raw),
            "originating_seed_nodes": origins[path],
            "depends_on": next(
                (item["depends_on"] for item in outputs if item["path"] == path),
                [],
            ),
        }
        for path, raw in sorted(files.items())
    ]
    manifest = {
        "format_version": "UC-STAGE1-GENERATION-MANIFEST-1",
        "generator_identity": BOILERPLATE_ID,
        "root_seed_identity": seed["seed_id"],
        "root_seed_sha256": sha(canonical(seed)),
        "files": inventory,
        "tree_sha256": tree_hash(inventory),
        "evidence": [
            "stage1:root-seed-validated",
            "stage1:declarations-resolved",
            "stage1:tree-rendered",
            "stage1:tree-verified",
        ],
    }
    files["stage1-manifest.json"] = canonical(manifest)
    return files, manifest


def remove(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def publish(output, files):
    output = output.resolve(strict=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = output.parent / ("." + output.name + ".stage1-new")
    backup = output.parent / ("." + output.name + ".stage1-old")
    remove(stage)
    remove(backup)
    stage.mkdir(parents=True)
    for relative, raw in sorted(files.items()):
        destination = stage.joinpath(*safe_path(relative).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    had_output = output.exists()
    if had_output:
        output.rename(backup)
    try:
        stage.rename(output)
    except BaseException:
        if had_output and backup.exists() and not output.exists():
            backup.rename(output)
        raise
    remove(backup)


def main(argv=None):
    args = list(sys.argv if argv is None else argv)
    try:
        if len(args) != 3:
            raise ValueError("usage")
        seed_path = Path(args[1]).resolve(strict=True)
        output = Path(args[2]).resolve(strict=False)
        if output in seed_path.parents:
            raise ValueError("output-overlaps-root-seed")
        seed = json.loads(seed_path.read_text(encoding="utf-8"), object_pairs_hook=pairs_without_duplicates)
        files, manifest = render(seed)
        publish(output, files)
        result = {
            "value": manifest,
            "depths": [],
            "axes": [],
            "evidence": manifest["evidence"] + ["boundary:stage1-published"],
            "state": "valid",
        }
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        result = {
            "value": {"error": str(error), "ticket": None},
            "depths": [],
            "axes": [],
            "evidence": ["stage1:rejected"],
            "state": "invalid",
        }
    sys.stdout.buffer.write(canonical(result))
    return 0 if result["state"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _canonical_json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def _sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _thing(value, evidence=(), state="formed"):
    return {
        "value": value,
        "depths": (),
        "axes": (),
        "evidence": tuple(evidence),
        "state": state,
    }


def _is_thing(value):
    return (
        isinstance(value, dict)
        and set(("value", "depths", "axes", "evidence", "state")).issubset(value)
        and isinstance(value["depths"], tuple)
        and isinstance(value["axes"], tuple)
        and isinstance(value["evidence"], tuple)
        and value["state"] in THING_STATES
    )


def _invalid(thing, code, evidence):
    value = dict(thing.get("value") or {}) if isinstance(thing, dict) else {}
    value.pop("handoff_bytes", None)
    value.pop("generation_manifest_bytes", None)
    value.update(
        {
            "error": code,
            "ticket": None,
            "handoff": None,
            "handoff_sha256": None,
            "generation_manifest": None,
            "generation_manifest_sha256": None,
            "stage1_payload_tree_sha256": None,
        }
    )
    return {
        "value": value,
        "depths": tuple(thing.get("depths") or ()) if isinstance(thing, dict) else (),
        "axes": tuple(thing.get("axes") or ()) if isinstance(thing, dict) else (),
        "evidence": (*tuple(thing.get("evidence") or ()), evidence),
        "state": "invalid",
    }


def _unhandled(thing):
    value = dict(thing.get("value") or {}) if isinstance(thing, dict) else {}
    correlation = _sha256(b"stage0|unhandled|redacted")[:16]
    value.update(
        {
            "error": "stage0.unhandled",
            "handoff": None,
            "handoff_sha256": None,
            "ticket": {
                "kind": "unhandled-exception",
                "operation": "stage0",
                "error_type": "UnhandledBoundaryFailure",
                "message": "[redacted-message]",
                "correlation_id": correlation,
                "ticket_id": correlation,
                "acked": False,
            },
        }
    )
    return {
        "value": value,
        "depths": tuple(thing.get("depths") or ()) if isinstance(thing, dict) else (),
        "axes": tuple(thing.get("axes") or ()) if isinstance(thing, dict) else (),
        "evidence": (*tuple(thing.get("evidence") or ()), "event:ticket.open"),
        "state": "invalid",
    }


def _pairs_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate-json-key")
        result[key] = value
    return result


def _read_json(path, maximum_bytes):
    raw = path.read_bytes()
    if len(raw) > maximum_bytes:
        raise ValueError("resource-limit:bytes")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs_without_duplicates), raw


def _json_depth(value):
    if isinstance(value, dict):
        return 1 + max((_json_depth(item) for item in value.values()), default=0)
    if isinstance(value, list):
        return 1 + max((_json_depth(item) for item in value), default=0)
    return 0


def _validate_trusted_json(role, parsed):
    if not isinstance(parsed, dict):
        raise ValueError(f"invalid-json-root:{role}")
    schema_ids = {
        "root-seed-schema": "uc-seed-schema-ten-1",
        "stage0-contract-schema": "uc-stage0-contract-schema-1",
        "stage1-handoff-schema": "uc-stage1-handoff-schema-1",
        "stage0-generation-manifest-schema": "uc-stage0-generation-manifest-schema-1",
    }
    if role in schema_ids and parsed.get("$id") != schema_ids[role]:
        raise ValueError(f"schema-identity:{role}")
    if role == "root-seed":
        required = {
            "standard_version",
            "uem_version",
            "seed_id",
            "packages",
            "declarations",
            "hosts",
            "vendored",
            "laws",
            "standard_ten",
            "gaps",
        }
        if not required.issubset(parsed):
            raise ValueError("root-seed-shape")
        if (
            parsed["standard_version"] != "TEN-1"
            or parsed["uem_version"] != "UEM-16-v0.1"
            or parsed["seed_id"] != "uc-canonical"
            or parsed["standard_ten"] is not True
            or parsed["laws"] != [f"L{index}" for index in range(1, 14)]
        ):
            raise ValueError("root-seed-identity")


def _safe_relative_path(raw_path, maximum_length):
    if not isinstance(raw_path, str) or not raw_path or len(raw_path.encode("utf-8")) > maximum_length:
        raise ValueError("invalid-path")
    if "\\" in raw_path or "\x00" in raw_path:
        raise ValueError("invalid-path")
    path = PurePosixPath(raw_path)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("invalid-path")
    return path


def _confined_file(root, relative):
    root_resolved = root.resolve(strict=True)
    candidate = root.joinpath(*relative.parts)
    resolved = candidate.resolve(strict=True)
    if root_resolved != resolved and root_resolved not in resolved.parents:
        raise ValueError("path-escape")
    if not resolved.is_file():
        raise ValueError("not-file")
    return resolved


def _safe_output_path(value):
    raw = value.get("output")
    if not isinstance(raw, (str, Path)):
        raise ValueError("invalid-output-path")
    output = Path(raw)
    if not output.name:
        raise ValueError("invalid-output-path")
    output_resolved = output.resolve(strict=False)
    input_root = Path(value["input_root"]).resolve(strict=True)
    if (
        output_resolved == input_root
        or output_resolved in input_root.parents
        or input_root in output_resolved.parents
    ):
        raise ValueError("output-overlaps-input-root")
    contract = Path(value["contract_path"]).resolve(strict=True)
    if output_resolved == contract or output_resolved in contract.parents:
        raise ValueError("output-overlaps-contract")
    return output


def _contract_shape(contract):
    required = {
        "contract_version",
        "canonicalization",
        "runtime",
        "limits",
        "allowed_operations",
        "prohibited_capabilities",
        "trusted_inputs",
        "external_dependencies",
        "stage1_handoff",
    }
    if not isinstance(contract, dict) or set(contract) != required:
        raise ValueError("contract-shape")
    if contract["contract_version"] != STAGE0_VERSION:
        raise ValueError("contract-version")
    if contract["canonicalization"] != CANONICAL_JSON_VERSION:
        raise ValueError("canonicalization-version")
    if tuple(contract["allowed_operations"]) != ALLOWED_OPERATIONS:
        raise ValueError("allowed-operations")
    if tuple(contract["prohibited_capabilities"]) != PROHIBITED_CAPABILITIES:
        raise ValueError("prohibited-capabilities")
    runtime = contract["runtime"]
    if (
        not isinstance(runtime, dict)
        or set(runtime) != {"implementation", "minimum_version", "allowed_modules"}
        or runtime["implementation"] != "cpython-stdlib"
        or runtime["minimum_version"] != "3.11"
        or runtime["allowed_modules"] != ["hashlib", "json", "pathlib", "shutil", "sys"]
    ):
        raise ValueError("runtime-profile")
    limits = contract["limits"]
    if not isinstance(limits, dict) or set(limits) != {
        "maximum_input_bytes",
        "maximum_input_count",
        "maximum_json_depth",
        "maximum_path_bytes",
    }:
        raise ValueError("limits-shape")
    if any(not isinstance(item, int) or item < 1 for item in limits.values()):
        raise ValueError("limits-value")
    inputs = contract["trusted_inputs"]
    if not isinstance(inputs, list) or len(inputs) > limits["maximum_input_count"]:
        raise ValueError("resource-limit:input-count")
    roles = [item.get("role") for item in inputs if isinstance(item, dict)]
    if frozenset(roles) != REQUIRED_ROLES or len(roles) != len(REQUIRED_ROLES):
        raise ValueError("trusted-input-roles")
    seen_paths = set()
    for item in inputs:
        if set(item) != {"role", "path", "hash_mode", "sha256"}:
            raise ValueError("trusted-input-shape")
        _safe_relative_path(item["path"], limits["maximum_path_bytes"])
        if item["path"] in seen_paths:
            raise ValueError("trusted-input-path-conflict")
        seen_paths.add(item["path"])
        if item["hash_mode"] not in ALLOWED_HASH_MODES:
            raise ValueError("hash-mode")
        if not isinstance(item["sha256"], str) or len(item["sha256"]) != 64:
            raise ValueError("hash-value")
    if contract["external_dependencies"] != []:
        raise ValueError("external-dependency-not-allowed")
    handoff = contract["stage1_handoff"]
    if not isinstance(handoff, dict) or set(handoff) != {
        "format_version",
        "handoff_file",
        "generation_manifest_file",
        "required_fields",
    }:
        raise ValueError("handoff-contract")
    if handoff["format_version"] != "UC-STAGE1-HANDOFF-1":
        raise ValueError("handoff-version")
    _safe_relative_path(handoff["handoff_file"], limits["maximum_path_bytes"])
    _safe_relative_path(handoff["generation_manifest_file"], limits["maximum_path_bytes"])
    return contract


def _normalized_contract(contract):
    normalized = dict(contract)
    normalized["trusted_inputs"] = sorted(
        contract["trusted_inputs"], key=lambda entry: (entry["role"], entry["path"])
    )
    return normalized


def inward_read_contract(thing):
    """Named INWARD boundary: read and validate the pinned trust manifest."""
    if not _is_thing(thing):
        return _invalid(_thing(thing), "stage0.invalid-thing", "stage0:invalid-thing")
    value = dict(thing["value"]) if isinstance(thing["value"], dict) else {}
    try:
        path = Path(value["contract_path"])
        contract, raw = _read_json(path, 1_048_576)
        _contract_shape(contract)
        value.update(
            {
                "contract": contract,
                "contract_sha256": _sha256(_canonical_json_bytes(_normalized_contract(contract))),
                "contract_raw_sha256": _sha256(raw),
                "ticket": None,
            }
        )
        return {
            **thing,
            "value": value,
            "evidence": (*thing["evidence"], "boundary:contract:read", "stage0:contract-verified"),
            "state": "formed",
        }
    except (KeyError, OSError, RecursionError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        return _invalid(thing, f"stage0.contract:{str(error)}", "stage0:contract-rejected")


def inward_read_trusted_inputs(thing):
    """Named INWARD boundary: hash only explicitly trusted and confined inputs."""
    if thing.get("state") == "invalid":
        return thing
    value = dict(thing["value"])
    contract = value["contract"]
    limits = contract["limits"]
    try:
        root = Path(value["input_root"])
        verified = []
        documents = {}
        for item in sorted(contract["trusted_inputs"], key=lambda entry: (entry["role"], entry["path"])):
            relative = _safe_relative_path(item["path"], limits["maximum_path_bytes"])
            path = _confined_file(root, relative)
            raw = path.read_bytes()
            if len(raw) > limits["maximum_input_bytes"]:
                raise ValueError("resource-limit:bytes")
            if item["hash_mode"] == "canonical-json":
                parsed = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs_without_duplicates)
                if _json_depth(parsed) > limits["maximum_json_depth"]:
                    raise ValueError("resource-limit:json-depth")
                hashed = _canonical_json_bytes(parsed)
            else:
                hashed = raw
            actual = _sha256(hashed)
            if actual != item["sha256"]:
                raise ValueError(f"hash-mismatch:{item['role']}")
            if item["hash_mode"] == "canonical-json":
                _validate_trusted_json(item["role"], parsed)
                documents[item["role"]] = parsed
            verified.append(
                {
                    "role": item["role"],
                    "path": item["path"],
                    "hash_mode": item["hash_mode"],
                    "sha256": actual,
                    "size": len(raw),
                }
            )
        value["verified_inputs"] = verified
        value["trusted_documents"] = documents
        return {
            **thing,
            "value": value,
            "evidence": (*thing["evidence"], "boundary:trusted-inputs:read", "stage0:inputs-verified"),
        }
    except (KeyError, OSError, RecursionError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        return _invalid(thing, f"stage0.input:{str(error)}", "stage0:inputs-rejected")


def plan_stage1_handoff(thing):
    """Pure construction: create the canonical, host-path-independent handoff."""
    if thing.get("state") == "invalid":
        return thing
    value = dict(thing["value"])
    inputs = value["verified_inputs"]
    root_seed = next(item for item in inputs if item["role"] == "root-seed")
    root_schema = next(item for item in inputs if item["role"] == "root-seed-schema")
    handoff_schema = next(item for item in inputs if item["role"] == "stage1-handoff-schema")
    handoff = {
        "format_version": "UC-STAGE1-HANDOFF-1",
        "stage0": {
            "version": STAGE0_VERSION,
            "contract_sha256": value["contract_sha256"],
            "canonicalization": CANONICAL_JSON_VERSION,
        },
        "root_seed": {
            "seed_id": "uc-canonical",
            "path": root_seed["path"],
            "sha256": root_seed["sha256"],
            "schema_path": root_schema["path"],
            "schema_sha256": root_schema["sha256"],
        },
        "trusted_inputs": inputs,
        "external_dependencies": [],
        "stage1_output": {
            "tree_path": "stage1",
            "manifest_path": "stage1-manifest.json",
            "handoff_schema_sha256": handoff_schema["sha256"],
        },
    }
    raw = _canonical_json_bytes(handoff)
    handoff_sha256 = _sha256(raw)
    tree_sha256 = _sha256(f"stage1-handoff.json\0{handoff_sha256}\n".encode("utf-8"))
    manifest = {
        "format_version": "UC-STAGE0-GENERATION-MANIFEST-1",
        "stage0_version": STAGE0_VERSION,
        "contract_sha256": value["contract_sha256"],
        "input_inventory": inputs,
        "output_inventory": [
            {
                "path": "stage1-handoff.json",
                "sha256": handoff_sha256,
                "size": len(raw),
            }
        ],
        "stage1_payload_tree_sha256": tree_sha256,
        "evidence": [
            "boundary:contract:read",
            "stage0:contract-verified",
            "boundary:trusted-inputs:read",
            "stage0:inputs-verified",
            "stage0:handoff-planned",
        ],
        "verification_result": "valid",
    }
    manifest_raw = _canonical_json_bytes(manifest)
    value.update(
        {
            "handoff": handoff,
            "handoff_bytes": raw,
            "handoff_sha256": handoff_sha256,
            "generation_manifest": manifest,
            "generation_manifest_bytes": manifest_raw,
            "generation_manifest_sha256": _sha256(manifest_raw),
            "stage1_payload_tree_sha256": tree_sha256,
        }
    )
    return {
        **thing,
        "value": value,
        "evidence": (*thing["evidence"], "stage0:handoff-planned"),
        "state": "valid",
    }


def _render_stage1_runner():
    token = "__TEMPLATE" + "_REPR__"
    return STAGE1_TEMPLATE.replace(token, repr(STAGE1_TEMPLATE)).encode("utf-8")


def _resolve_seed_node(seed, pointer):
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("unsupported-seed-node")
    parts = pointer.split("/")[1:]
    if not parts:
        raise ValueError("unsupported-seed-node")
    value = seed
    for part in parts:
        if not isinstance(value, dict) or part not in value:
            raise ValueError("unsupported-seed-node")
        value = value[part]
    return value


def _stage1_tree_hash(inventory):
    raw = "".join(
        item["path"] + "\0" + item["sha256"] + "\n"
        for item in sorted(inventory, key=lambda item: item["path"])
    ).encode("utf-8")
    return _sha256(raw)


def _validate_stage1_seed(seed):
    stage1 = seed.get("stage1") if isinstance(seed, dict) else None
    if (
        not isinstance(stage1, dict)
        or set(stage1) != {"format_version", "framework", "generator", "uem"}
        or stage1.get("format_version") != "UC-STAGE1-SEED-1"
    ):
        raise ValueError("unsupported-stage1-declaration")
    generator = stage1.get("generator")
    framework = stage1.get("framework")
    uem = stage1.get("uem")
    if (
        not isinstance(generator, dict)
        or generator.get("boilerplate") != "UC-STAGE1-PY-1"
        or tuple(generator.get("operations") or ()) != STAGE1_OPERATIONS
        or not isinstance(generator.get("outputs"), list)
    ):
        raise ValueError("standard.gap:unsupported-stage1-operation")
    if (
        not isinstance(framework, dict)
        or set(framework)
        != {"standard_version", "thing_fields", "thing_states", "laws"}
        or framework["standard_version"] != "TEN-1"
        or framework["thing_fields"]
        != ["value", "depths", "axes", "evidence", "state"]
        or framework["thing_states"]
        != ["unknown", "absent", "false", "formed", "valid", "invalid"]
        or framework["laws"] != [f"L{index}" for index in range(1, 14)]
    ):
        raise ValueError("unsupported-framework-declaration")
    if (
        not isinstance(uem, dict)
        or set(uem)
        != {
            "machine",
            "format_version",
            "opcodes",
            "primitive_registry_version",
            "primitives",
        }
        or uem["machine"] != "UEM-16"
        or uem["format_version"] != 1
        or uem["primitive_registry_version"] != 2
        or not isinstance(uem["opcodes"], list)
        or [
            item.get("code") for item in uem["opcodes"] if isinstance(item, dict)
        ]
        != list(range(1, 17))
        or any(
            set(item) != {"code", "name"}
            or not isinstance(item["name"], str)
            or not item["name"]
            for item in uem["opcodes"]
        )
        or not isinstance(uem["primitives"], list)
        or not uem["primitives"]
        or len(uem["primitives"]) != len(set(uem["primitives"]))
        or any(not isinstance(item, str) or not item for item in uem["primitives"])
    ):
        raise ValueError("unsupported-uem-declaration")
    _validate_repository(seed)
    return stage1


def _render_canonical_json(value):
    return _canonical_json_bytes(value)


def _render_utf8_lines(value):
    if not isinstance(value, list) or not all(isinstance(line, str) for line in value):
        raise ValueError("unsupported-utf8-lines")
    return ("\n".join(value) + "\n").encode("utf-8")


def _render_hex_bytes(value):
    if not isinstance(value, str):
        raise ValueError("unsupported-hex-bytes")
    try:
        return bytes.fromhex(value)
    except ValueError as error:
        raise ValueError("unsupported-hex-bytes") from error


_STAGE1_RENDERERS = {
    "canonical-json": _render_canonical_json,
    "utf8-lines": _render_utf8_lines,
    "hex-bytes": _render_hex_bytes,
}


def _validate_repository(seed):
    repository = seed.get("repository") if isinstance(seed, dict) else None
    if (
        not isinstance(repository, dict)
        or set(repository)
        != {
            "format_version",
            "renderers",
            "generation_bound",
            "depths",
            "watchers",
            "summary_lines",
            "projections",
        }
        or repository["format_version"] != "UC-ROOT-REPOSITORY-1"
        or repository["renderers"] != list(_STAGE1_RENDERERS)
        or repository["generation_bound"] != 3
        or repository["depths"] != list(range(1, 11))
        or not isinstance(repository["watchers"], list)
        or [
            item.get("depth")
            for item in repository["watchers"]
            if isinstance(item, dict)
        ]
        != list(range(1, 11))
        or any(
            set(item) != {"id", "depth"}
            or not isinstance(item["id"], str)
            or not item["id"]
            for item in repository["watchers"]
        )
        or len({item["id"] for item in repository["watchers"]}) != 10
        or not isinstance(repository["summary_lines"], list)
        or not all(isinstance(line, str) for line in repository["summary_lines"])
        or not isinstance(repository["projections"], list)
    ):
        raise ValueError("unsupported-repository-declaration")
    return repository


def plan_stage1_tree(thing):
    """Pure construction: specialize the generic Stage-1 boilerplate from ROOT.seed."""
    if thing.get("state") == "invalid":
        return thing
    value = dict(thing["value"])
    try:
        seed = value["trusted_documents"]["root-seed"]
        stage1 = _validate_stage1_seed(seed)
        outputs = stage1["generator"]["outputs"] + seed["repository"]["projections"]
        files = {"stage1.py": _render_stage1_runner()}
        origins = {"stage1.py": ["/stage1/generator"]}
        seen = {"stage1.py"}
        for output in outputs:
            if not isinstance(output, dict) or set(output) != {
                "path",
                "seed_node",
                "renderer",
                "depends_on",
            }:
                raise ValueError("unsupported-output-declaration")
            path = _safe_relative_path(
                output["path"], value["contract"]["limits"]["maximum_path_bytes"]
            ).as_posix()
            dependencies = output["depends_on"]
            if (
                path in seen
                or output["renderer"] not in _STAGE1_RENDERERS
                or not isinstance(dependencies, list)
                or not all(isinstance(item, str) and item in seen for item in dependencies)
            ):
                raise ValueError("unsupported-output-declaration")
            seen.add(path)
            files[path] = _STAGE1_RENDERERS[output["renderer"]](
                seed
                if output["seed_node"] == "/"
                else _resolve_seed_node(seed, output["seed_node"])
            )
            origins[path] = [output["seed_node"]]
        inventory = [
            {
                "path": path,
                "sha256": _sha256(raw),
                "size": len(raw),
                "originating_seed_nodes": origins[path],
                "depends_on": next(
                    (
                        item["depends_on"]
                        for item in outputs
                        if item["path"] == path
                    ),
                    [],
                ),
            }
            for path, raw in sorted(files.items())
        ]
        manifest = {
            "format_version": "UC-STAGE1-GENERATION-MANIFEST-1",
            "generator_identity": "UC-STAGE1-PY-1",
            "root_seed_identity": seed["seed_id"],
            "root_seed_sha256": _sha256(_canonical_json_bytes(seed)),
            "files": inventory,
            "tree_sha256": _stage1_tree_hash(inventory),
            "evidence": [
                "stage1:root-seed-validated",
                "stage1:declarations-resolved",
                "stage1:tree-rendered",
                "stage1:tree-verified",
            ],
        }
        files["stage1-manifest.json"] = _canonical_json_bytes(manifest)
        value.update(
            {
                "stage1_files": files,
                "stage1_manifest": manifest,
                "stage1_tree_sha256": manifest["tree_sha256"],
            }
        )
        return {
            **thing,
            "value": value,
            "evidence": (
                *thing["evidence"],
                "stage1:root-seed-validated",
                "stage1:declarations-resolved",
                "stage1:tree-rendered",
                "stage1:tree-verified",
            ),
            "state": "valid",
        }
    except (KeyError, TypeError, ValueError) as error:
        return _invalid(
            thing,
            f"stage1.generate:{str(error)}",
            "stage1:generation-rejected",
        )


def _remove_path(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _atomic_publish(output, files):
    parent = output.parent
    parent.mkdir(parents=True, exist_ok=True)
    stage = parent / f".{output.name}.stage0-new"
    backup = parent / f".{output.name}.stage0-old"
    if stage.exists():
        _remove_path(stage)
    if backup.exists() or backup.is_symlink():
        _remove_path(backup)
    stage.mkdir(parents=True)
    for filename, raw in sorted(files.items()):
        relative = _safe_relative_path(filename, 256)
        destination = stage.joinpath(*relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    had_output = output.exists()
    if had_output:
        output.rename(backup)
    try:
        stage.rename(output)
    except BaseException:
        if had_output and backup.exists() and not output.exists():
            backup.rename(output)
        raise
    if backup.exists() or backup.is_symlink():
        try:
            _remove_path(backup)
        except OSError:
            pass


def outward_publish_handoff(thing):
    """Named OUTWARD boundary: atomically install the verified handoff."""
    if thing.get("state") == "invalid":
        return thing
    value = dict(thing["value"])
    try:
        output = _safe_output_path(value)
        handoff_contract = value["contract"]["stage1_handoff"]
        _atomic_publish(
            output,
            {
                handoff_contract["handoff_file"]: value["handoff_bytes"],
                handoff_contract["generation_manifest_file"]: value["generation_manifest_bytes"],
            },
        )
        value.pop("handoff_bytes", None)
        value.pop("generation_manifest_bytes", None)
        return {
            **thing,
            "value": value,
            "evidence": (*thing["evidence"], "boundary:handoff:publish", "stage0:handoff-published"),
        }
    except (OSError, ValueError) as error:
        return _invalid(thing, f"stage0.publish:{type(error).__name__}", "stage0:publish-rejected")


def outward_publish_stage1(thing):
    """Named OUTWARD boundary: atomically install the verified Stage1-A tree."""
    if thing.get("state") == "invalid":
        return thing
    value = dict(thing["value"])
    try:
        output = _safe_output_path(value)
        _atomic_publish(output, value["stage1_files"])
        value.pop("stage1_files", None)
        value.pop("trusted_documents", None)
        return {
            **thing,
            "value": value,
            "evidence": (
                *thing["evidence"],
                "boundary:stage1:publish",
                "stage1:published",
            ),
            "state": "valid",
        }
    except (KeyError, OSError, ValueError) as error:
        return _invalid(
            thing,
            f"stage1.publish:{type(error).__name__}",
            "stage1:publish-rejected",
        )


def stage0_plan(thing):
    """Public Stage-0 Part: one Thing in, one Thing out."""
    try:
        return outward_publish_handoff(
            plan_stage1_handoff(inward_read_trusted_inputs(inward_read_contract(thing)))
        )
    except BaseException:
        return _unhandled(thing)


def stage0_generate(thing):
    """Public Stage-0 Part: ROOT.seed to a runnable generated Stage1-A."""
    try:
        return outward_publish_stage1(
            plan_stage1_tree(inward_read_trusted_inputs(inward_read_contract(thing)))
        )
    except BaseException:
        return _unhandled(thing)


def main(argv=None):
    args = list(sys.argv if argv is None else argv)
    if (
        len(args) != 8
        or args[1] not in ("plan", "generate")
        or args[2] != "--contract"
        or args[4] != "--input-root"
        or args[6] != "--output"
    ):
        result = _invalid(_thing({}), "stage0.cli:usage", "stage0:cli-rejected")
    else:
        operation = stage0_plan if args[1] == "plan" else stage0_generate
        result = operation(
            _thing(
                {
                    "contract_path": args[3],
                    "input_root": args[5],
                    "output": args[7],
                }
            )
        )
    sys.stdout.buffer.write(_canonical_json_bytes(result))
    return 0 if result["state"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
