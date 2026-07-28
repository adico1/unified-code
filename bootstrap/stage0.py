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


def _remove_path(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _atomic_publish(output, files):
    parent = output.parent
    stage = parent / f".{output.name}.stage0-new"
    backup = parent / f".{output.name}.stage0-old"
    if stage.exists():
        _remove_path(stage)
    if backup.exists() or backup.is_symlink():
        _remove_path(backup)
    stage.mkdir(parents=True)
    for filename, raw in sorted(files.items()):
        (stage / filename).write_bytes(raw)
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


def stage0_plan(thing):
    """Public Stage-0 Part: one Thing in, one Thing out."""
    try:
        return outward_publish_handoff(
            plan_stage1_handoff(inward_read_trusted_inputs(inward_read_contract(thing)))
        )
    except BaseException:
        return _unhandled(thing)


def main(argv=None):
    args = list(sys.argv if argv is None else argv)
    if len(args) != 8 or args[1] != "plan" or args[2] != "--contract" or args[4] != "--input-root" or args[6] != "--output":
        result = _invalid(_thing({}), "stage0.cli:usage", "stage0:cli-rejected")
    else:
        result = stage0_plan(
            _thing({"contract_path": args[3], "input_root": args[5], "output": args[7]})
        )
    sys.stdout.buffer.write(_canonical_json_bytes(result))
    return 0 if result["state"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
