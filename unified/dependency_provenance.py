"""Offline verification of pinned external dependency provenance.

The public Part delegates physical file traversal and validation to one named
audited primitive.  It never acquires dependencies and performs no network I/O.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .thing import is_thing


FORMAT_VERSION = "UC-EXTERNAL-DEPENDENCIES-1"
MANIFEST_PATH = "seed/EXTERNAL_DEPENDENCIES.json"
ROOT_SEED_PATH = "seed/ROOT.seed.json"
REQUIRED_DEPENDENCY_FIELDS = frozenset(
    {
        "id",
        "canonical_name",
        "kind",
        "role",
        "version",
        "upstream",
        "artifacts",
        "license",
        "acquisition",
        "verification",
        "reproducibility",
        "offline_bootstrap",
        "maintenance",
        "replacement_plan",
        "dependents",
    }
)
REQUIRED_PROCEDURE_FIELDS = frozenset({"status", "procedure"})
PROCEDURE_FIELDS = (
    "acquisition",
    "verification",
    "reproducibility",
    "offline_bootstrap",
)


def _result(thing, value, mark, state):
    return {
        **thing,
        "value": value,
        "evidence": (*thing.get("evidence", ()), mark),
        "state": state,
    }


def audited_sha256_file_primitive(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def audited_canonical_sha256_primitive(value):
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def audited_canonical_manifest_primitive(manifest):
    """Normalize semantically unordered registry collections before hashing."""
    normalized = json.loads(json.dumps(manifest))
    normalized["vendored_roots"] = sorted(normalized["vendored_roots"])
    normalized["dependencies"] = sorted(
        normalized["dependencies"], key=lambda dependency: dependency["id"]
    )
    for dependency in normalized["dependencies"]:
        dependency["artifacts"] = sorted(
            dependency["artifacts"], key=lambda artifact: artifact["path"]
        )
        dependency["license"]["files"] = sorted(
            dependency["license"]["files"], key=lambda item: item["path"]
        )
        dependency["dependents"]["stage0"] = sorted(
            dependency["dependents"]["stage0"]
        )
        dependency["dependents"]["stage1"] = sorted(
            dependency["dependents"]["stage1"]
        )
    normalized["substrate_requirements"] = sorted(
        normalized["substrate_requirements"], key=lambda item: item["id"]
    )
    normalized["excluded_external_surfaces"] = sorted(
        normalized["excluded_external_surfaces"], key=lambda item: item["surface"]
    )
    return normalized


def audited_is_sha256_primitive(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(letter in "0123456789abcdef" for letter in value)
    )


def audited_is_revision_primitive(value):
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(letter in "0123456789abcdef" for letter in value)
    )


def audited_load_json_primitive(path, subject, errors):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{subject}:missing")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        errors.append(f"{subject}:unreadable")
    return None


def audited_dependency_errors_primitive(root, manifest, root_seed):
    """Own all host control flow for the frozen offline provenance contract."""
    errors = []
    if not isinstance(manifest, dict):
        return ("manifest:type",)
    expected_top = {
        "format_version",
        "canonicalization",
        "vendored_roots",
        "dependencies",
        "substrate_requirements",
        "excluded_external_surfaces",
    }
    if set(manifest) != expected_top:
        errors.append("manifest:fields")
    if manifest.get("format_version") != FORMAT_VERSION:
        errors.append("manifest:format-version")
    if manifest.get("canonicalization") != "UC-CANONICAL-JSON-1":
        errors.append("manifest:canonicalization")
    vendored_roots = manifest.get("vendored_roots")
    if (
        not isinstance(vendored_roots, list)
        or not vendored_roots
        or not all(isinstance(path, str) and path for path in vendored_roots)
        or len(vendored_roots) != len(set(vendored_roots or ()))
    ):
        errors.append("manifest:vendored-roots")
        vendored_roots = []
    dependencies = manifest.get("dependencies")
    if not isinstance(dependencies, list) or not dependencies:
        errors.append("manifest:dependencies")
        dependencies = []

    artifact_records = []
    dependency_ids = []
    for index, dependency in enumerate(dependencies):
        prefix = f"dependency:{index}"
        if not isinstance(dependency, dict):
            errors.append(f"{prefix}:type")
            continue
        if set(dependency) != REQUIRED_DEPENDENCY_FIELDS:
            errors.append(f"{prefix}:fields")
        dependency_id = dependency.get("id")
        if not isinstance(dependency_id, str) or not dependency_id:
            errors.append(f"{prefix}:id")
        else:
            dependency_ids.append(dependency_id)
            prefix = f"dependency:{dependency_id}"
        if dependency.get("kind") not in {
            "external-vendored",
            "project-originated",
        }:
            errors.append(f"{prefix}:kind")
        for field in ("canonical_name", "role", "version"):
            if not isinstance(dependency.get(field), str) or not dependency.get(field):
                errors.append(f"{prefix}:{field.replace('_', '-')}")
        upstream = dependency.get("upstream")
        if not isinstance(upstream, dict) or set(upstream) != {
            "source",
            "immutable_revision",
        }:
            errors.append(f"{prefix}:upstream")
            revision = None
        else:
            revision = upstream.get("immutable_revision")
            if not audited_is_revision_primitive(revision):
                errors.append(f"{prefix}:immutable-revision")
            if not isinstance(upstream.get("source"), str) or not upstream.get(
                "source"
            ):
                errors.append(f"{prefix}:upstream-source")
        artifacts = dependency.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"{prefix}:artifacts")
            artifacts = []
        for artifact_index, artifact in enumerate(artifacts):
            artifact_prefix = f"{prefix}:artifact:{artifact_index}"
            if not isinstance(artifact, dict) or set(artifact) != {
                "artifact_id",
                "path",
                "sha256",
                "size",
                "immutable_source",
                "root_reference",
            }:
                errors.append(f"{artifact_prefix}:fields")
                continue
            artifact_id = artifact.get("artifact_id")
            artifact_path = artifact.get("path")
            if not isinstance(artifact_id, str) or not artifact_id:
                errors.append(f"{artifact_prefix}:id")
            if not isinstance(artifact_path, str) or not artifact_path:
                errors.append(f"{artifact_prefix}:path")
                continue
            artifact_prefix = f"artifact:{artifact_path}"
            if not audited_is_sha256_primitive(artifact.get("sha256")):
                errors.append(f"{artifact_prefix}:sha256-format")
            if not isinstance(artifact.get("size"), int) or isinstance(
                artifact.get("size"), bool
            ) or artifact.get("size", -1) < 0:
                errors.append(f"{artifact_prefix}:size-format")
            source = artifact.get("immutable_source")
            if not isinstance(source, str) or not source or not revision or revision not in source:
                errors.append(f"{artifact_prefix}:mutable-source")
            root_reference = artifact.get("root_reference")
            if root_reference is not None and (
                not isinstance(root_reference, dict)
                or set(root_reference) != {"id", "license"}
                or not all(
                    isinstance(root_reference.get(field), str)
                    and root_reference.get(field)
                    for field in ("id", "license")
                )
            ):
                errors.append(f"{artifact_prefix}:root-reference")
            artifact_records.append((dependency_id, artifact_id, artifact))
        license_record = dependency.get("license")
        if not isinstance(license_record, dict) or set(license_record) != {
            "spdx",
            "files",
            "note",
        }:
            errors.append(f"{prefix}:license")
        else:
            if not isinstance(license_record.get("spdx"), str) or not license_record.get(
                "spdx"
            ):
                errors.append(f"{prefix}:license-spdx")
            if not isinstance(license_record.get("note"), str) or not license_record.get(
                "note"
            ):
                errors.append(f"{prefix}:license-note")
            license_files = license_record.get("files")
            if not isinstance(license_files, list) or not license_files:
                errors.append(f"{prefix}:license-files")
                license_files = []
            for license_index, license_file in enumerate(license_files):
                license_prefix = f"{prefix}:license-file:{license_index}"
                if not isinstance(license_file, dict) or set(license_file) != {
                    "path",
                    "sha256",
                }:
                    errors.append(f"{license_prefix}:fields")
                    continue
                license_path = license_file.get("path")
                if not isinstance(license_path, str) or not license_path:
                    errors.append(f"{license_prefix}:path")
                    continue
                physical_license = root / license_path
                if not physical_license.is_file():
                    errors.append(f"license:{license_path}:missing")
                elif audited_sha256_file_primitive(physical_license) != license_file.get(
                    "sha256"
                ):
                    errors.append(f"license:{license_path}:hash-mismatch")
        for field in PROCEDURE_FIELDS:
            procedure = dependency.get(field)
            if not isinstance(procedure, dict) or set(procedure) != REQUIRED_PROCEDURE_FIELDS:
                errors.append(f"{prefix}:{field.replace('_', '-')}")
            elif not all(
                isinstance(procedure.get(key), str) and procedure.get(key)
                for key in REQUIRED_PROCEDURE_FIELDS
            ):
                errors.append(f"{prefix}:{field.replace('_', '-')}")
        maintenance = dependency.get("maintenance")
        if not isinstance(maintenance, dict) or set(maintenance) != {
            "update_cadence",
            "security_owner",
        } or not all(isinstance(value, str) and value for value in maintenance.values()):
            errors.append(f"{prefix}:maintenance")
        replacement = dependency.get("replacement_plan")
        if not isinstance(replacement, dict) or set(replacement) != {
            "status",
            "plan",
        } or not all(isinstance(value, str) and value for value in replacement.values()):
            errors.append(f"{prefix}:replacement-plan")
        dependents = dependency.get("dependents")
        if not isinstance(dependents, dict) or set(dependents) != {
            "stage0",
            "stage1",
        } or not all(
            isinstance(dependents.get(stage), list)
            and all(isinstance(value, str) and value for value in dependents[stage])
            for stage in ("stage0", "stage1")
        ):
            errors.append(f"{prefix}:dependents")

    if len(dependency_ids) != len(set(dependency_ids)):
        errors.append("manifest:duplicate-dependency-id")
    artifact_paths = [record[2]["path"] for record in artifact_records]
    artifact_ids = [record[1] for record in artifact_records]
    if len(artifact_paths) != len(set(artifact_paths)):
        errors.append("manifest:duplicate-artifact-path")
    if len(artifact_ids) != len(set(artifact_ids)):
        errors.append("manifest:duplicate-artifact-id")

    declared_paths = set(artifact_paths)
    observed_paths = set()
    for vendored_root in vendored_roots:
        physical_root = root / vendored_root
        if not physical_root.is_dir():
            errors.append(f"vendored-root:{vendored_root}:missing")
            continue
        observed_paths.update(
            path.relative_to(root).as_posix()
            for path in physical_root.rglob("*")
            if path.is_file()
        )
    for path in sorted(observed_paths - declared_paths):
        errors.append(f"artifact:{path}:undeclared")
    for path in sorted(declared_paths - observed_paths):
        errors.append(f"artifact:{path}:missing")
    for _, _, artifact in artifact_records:
        path = artifact["path"]
        physical = root / path
        if not physical.is_file():
            continue
        if physical.stat().st_size != artifact.get("size"):
            errors.append(f"artifact:{path}:size-mismatch")
        if audited_sha256_file_primitive(physical) != artifact.get("sha256"):
            errors.append(f"artifact:{path}:hash-mismatch")

    root_records = root_seed.get("vendored") if isinstance(root_seed, dict) else None
    if not isinstance(root_records, list):
        errors.append("root-seed:vendored")
        root_records = []
    root_paths = []
    expected_root = {}
    for dependency_id, artifact_id, artifact in artifact_records:
        del dependency_id, artifact_id
        if artifact.get("root_reference") is not None:
            expected_root[artifact["path"]] = artifact["root_reference"]
    for index, record in enumerate(root_records):
        if not isinstance(record, dict):
            errors.append(f"root-seed:vendored:{index}:type")
            continue
        path = record.get("path")
        root_paths.append(path)
        expected = expected_root.get(path)
        if expected is None:
            errors.append(f"root-seed:vendored:{path}:undeclared")
            continue
        if record.get("id") != expected["id"]:
            errors.append(f"root-seed:vendored:{path}:id")
        if record.get("license") != expected["license"]:
            errors.append(f"root-seed:vendored:{path}:license")
    if len(root_paths) != len(set(root_paths)):
        errors.append("root-seed:vendored:duplicate-path")
    for path in sorted(set(expected_root) - set(root_paths)):
        errors.append(f"root-seed:vendored:{path}:missing")

    substrate = manifest.get("substrate_requirements")
    if not isinstance(substrate, list) or not all(
        isinstance(item, dict)
        and set(item) == {"id", "role", "constraint", "boundary"}
        and all(isinstance(value, str) and value for value in item.values())
        for item in substrate or ()
    ):
        errors.append("manifest:substrate-requirements")
    exclusions = manifest.get("excluded_external_surfaces")
    if not isinstance(exclusions, list) or not all(
        isinstance(item, dict)
        and set(item) == {"surface", "reason"}
        and all(isinstance(value, str) and value for value in item.values())
        for item in exclusions or ()
    ):
        errors.append("manifest:excluded-external-surfaces")
    return tuple(sorted(set(errors)))


def audited_verify_external_dependencies_primitive(thing):
    if not is_thing(thing):
        return {
            "value": {"errors": ("thing:invalid",), "ticket": None},
            "depths": (),
            "axes": (),
            "evidence": ("dependencies:rejected",),
            "state": "invalid",
        }
    value = thing.get("value")
    if not isinstance(value, dict):
        return _result(
            thing,
            {"errors": ("request:type",), "ticket": None},
            "dependencies:rejected",
            "invalid",
        )
    root = Path(value.get("root") or Path(__file__).resolve().parents[1]).resolve()
    manifest_path = root / (value.get("manifest") or MANIFEST_PATH)
    root_seed_path = root / (value.get("root_seed") or ROOT_SEED_PATH)
    load_errors = []
    manifest = audited_load_json_primitive(manifest_path, "manifest", load_errors)
    root_seed = audited_load_json_primitive(root_seed_path, "root-seed", load_errors)
    errors = tuple(load_errors)
    if not errors:
        errors = audited_dependency_errors_primitive(root, manifest, root_seed)
    if errors:
        return _result(
            thing,
            {"errors": errors, "ticket": None},
            "dependencies:rejected",
            "invalid",
        )
    artifacts = tuple(
        artifact["path"]
        for dependency in manifest["dependencies"]
        for artifact in dependency["artifacts"]
    )
    return _result(
        thing,
        {
            "format_version": FORMAT_VERSION,
            "manifest_sha256": audited_canonical_sha256_primitive(
                audited_canonical_manifest_primitive(manifest)
            ),
            "dependency_count": len(manifest["dependencies"]),
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
            "offline": True,
            "ticket": None,
        },
        "dependencies:verified",
        "valid",
    )


def verify_external_dependencies(thing):
    """Verify the complete pinned dependency inventory from one Thing."""
    return audited_verify_external_dependencies_primitive(thing)


def _main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("verify",))
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    arguments = parser.parse_args()
    thing = {
        "value": {"root": arguments.root},
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": "formed",
    }
    result = verify_external_dependencies(thing)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["state"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(_main())
