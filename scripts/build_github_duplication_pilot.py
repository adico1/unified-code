"""Acquire or replay a pinned public-code duplication pilot.

Live bytes cross one explicit read-only GitHub boundary. Published evidence
contains hashes and derived measurements, never copied source text.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import io
import json
import re
import tarfile
import tomllib
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath


FORMAT = "uc-github-duplication-pilot-1"
EXTRACTOR_VERSION = "UC-GITHUB-DUPLICATION-PILOT-1"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED = ROOT / "seed/economics/github-duplication-pilot.seed.json"
DEFAULT_SNAPSHOT = ROOT / "artifacts/economics/github-duplication-pilot.snapshot.json"
DEFAULT_REPORT = ROOT / "artifacts/economics/github-duplication-pilot.json"
PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*")


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_value(value):
    return sha256_bytes(canonical_bytes(value))


class _NormalizePython(ast.NodeTransformer):
    """Audited structural proxy: erase names and literal values, not syntax."""

    def visit_Name(self, node):
        return ast.copy_location(ast.Name(id="NAME", ctx=node.ctx), node)

    def visit_arg(self, node):
        annotation = self.visit(node.annotation) if node.annotation is not None else None
        return ast.copy_location(ast.arg(arg="ARG", annotation=annotation), node)

    def visit_FunctionDef(self, node):
        node = self.generic_visit(node)
        node.name = "FUNCTION"
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        node = self.generic_visit(node)
        node.name = "CLASS"
        return node

    def visit_Attribute(self, node):
        node = self.generic_visit(node)
        node.attr = "ATTRIBUTE"
        return node

    def visit_Constant(self, node):
        kind = type(node.value).__name__
        return ast.copy_location(ast.Constant(value=f"<{kind}>"), node)


def normalized_python_sha256(source):
    try:
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return None
    normalized = _NormalizePython().visit(tree)
    ast.fix_missing_locations(normalized)
    return sha256_bytes(ast.dump(normalized, annotate_fields=True, include_attributes=False).encode())


def normalized_python_units(source):
    """Return bounded statement/expression motifs without names or literals."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []
    counts = Counter()
    coordinates = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.stmt, ast.expr)):
            continue
        node_count = sum(1 for _ in ast.walk(node))
        if not 12 <= node_count <= 80:
            continue
        normalized = _NormalizePython().visit(copy.deepcopy(node))
        ast.fix_missing_locations(normalized)
        identity = sha256_bytes(ast.dump(normalized, annotate_fields=True, include_attributes=False).encode())
        coordinates[identity] = (type(node).__name__, node_count)
        counts[identity] += 1
    units = [
        {"kind": coordinates[identity][0], "node_count": coordinates[identity][1], "occurrences": count, "structure_sha256": identity}
        for identity, count in counts.items()
    ]
    return sorted(units, key=lambda item: (item["structure_sha256"], item["kind"], item["node_count"]))


def dependency_names(path, content):
    name = PurePosixPath(path).name
    text = content.decode("utf-8", errors="replace")
    if name in {"requirements.txt", "Pipfile"}:
        candidates = (
            PACKAGE_RE.match(line.strip()).group(0).lower().replace("_", "-")
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith(("#", "[")) and PACKAGE_RE.match(line.strip())
        )
        return sorted(set(candidates))
    if name == "pyproject.toml":
        try:
            document = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            return []
        values = list(document.get("project", {}).get("dependencies", ()))
        values += list(document.get("tool", {}).get("poetry", {}).get("dependencies", {}))
        return sorted({match.group(0).lower().replace("_", "-") for value in values if (match := PACKAGE_RE.match(str(value))) and match.group(0).lower() != "python"})
    return []


def github_archive_boundary(full_name, commit_sha):
    url = f"https://codeload.github.com/{full_name}/tar.gz/{commit_sha}"
    request = urllib.request.Request(url, headers={"User-Agent": EXTRACTOR_VERSION})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def project_archive(seed, repository, archive):
    measured = seed["measurement"]
    extensions = set(measured["file_extensions"])
    dependency_files = set(measured["dependency_files"])
    excluded = set(measured["excluded_path_segments"])
    maximum = measured["maximum_file_bytes"]
    files = []
    dependencies = set()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
        members = sorted((member for member in bundle.getmembers() if member.isfile()), key=lambda item: item.name)
        for member in members:
            relative = PurePosixPath(*PurePosixPath(member.name).parts[1:])
            if not relative.parts or excluded.intersection(relative.parts) or member.size > maximum:
                continue
            is_source = relative.suffix in extensions
            is_dependency = relative.name in dependency_files
            if not is_source and not is_dependency:
                continue
            stream = bundle.extractfile(member)
            content = stream.read() if stream else b""
            dependencies.update(dependency_names(str(relative), content))
            if is_source:
                source = content.decode("utf-8", errors="replace")
                files.append({
                    "path": str(relative),
                    "bytes": len(content),
                    "content_sha256": sha256_bytes(content),
                    "structure_sha256": normalized_python_sha256(source),
                    "structure_units": normalized_python_units(source),
                })
    return {
        "family": repository["family"],
        "full_name": repository["full_name"],
        "commit_sha": repository["commit_sha"],
        "license_spdx": repository["license_spdx"],
        "source_url": f"https://github.com/{repository['full_name']}/tree/{repository['commit_sha']}",
        "archive_sha256": sha256_bytes(archive),
        "files": files,
        "dependencies": sorted(dependencies),
    }


def acquire(seed):
    return {
        "format": "uc-github-duplication-snapshot-1",
        "seed_sha256": sha256_value(seed),
        "repositories": [
            project_archive(
                seed,
                repository,
                github_archive_boundary(repository["full_name"], repository["commit_sha"]),
            )
            for repository in sorted(seed["repositories"], key=lambda item: item["full_name"])
        ],
    }


def cross_repository_groups(repositories, field):
    groups = defaultdict(list)
    for repository in repositories:
        for file_record in repository["files"]:
            identity = file_record.get(field)
            if identity:
                groups[identity].append({"repository": repository["full_name"], "path": file_record["path"], "bytes": file_record["bytes"]})
    return [
        {"identity": identity, "instances": sorted(instances, key=lambda item: (item["repository"], item["path"]))}
        for identity, instances in sorted(groups.items())
        if len({item["repository"] for item in instances}) > 1
    ]


def cross_repository_structure_groups(repositories):
    groups = defaultdict(list)
    for repository in repositories:
        for file_record in repository["files"]:
            for unit in file_record.get("structure_units", ()):
                groups[unit["structure_sha256"]].append({
                    "repository": repository["full_name"],
                    "path": file_record["path"],
                    "kind": unit["kind"],
                    "node_count": unit["node_count"],
                    "occurrences": unit["occurrences"],
                })
    return [
        {"identity": identity, "instances": sorted(instances, key=lambda item: (item["repository"], item["path"], item["kind"], item["node_count"]))}
        for identity, instances in sorted(groups.items())
        if len({item["repository"] for item in instances}) > 1
    ]


def measure(seed, snapshot):
    expected = {
        item["full_name"]: (item["family"], item["commit_sha"], item["license_spdx"])
        for item in seed["repositories"]
    }
    repositories = sorted(snapshot["repositories"], key=lambda item: item["full_name"])
    observed = {
        item["full_name"]: (item["family"], item["commit_sha"], item["license_spdx"])
        for item in repositories
    }
    if snapshot.get("seed_sha256") != sha256_value(seed):
        raise ValueError("snapshot:seed-sha256")
    if len(observed) != len(repositories) or observed != expected:
        raise ValueError("snapshot:repository-authority")
    canonical_snapshot = {**snapshot, "repositories": repositories}
    exact_groups = cross_repository_groups(repositories, "content_sha256")
    structure_groups = cross_repository_structure_groups(repositories)
    all_files = [file_record for repository in repositories for file_record in repository["files"]]
    unique_bytes = {}
    for file_record in all_files:
        unique_bytes.setdefault(file_record["content_sha256"], file_record["bytes"])
    dependency_repositories = defaultdict(set)
    family_by_repository = {item["full_name"]: item["family"] for item in repositories}
    for repository in repositories:
        for dependency in repository["dependencies"]:
            dependency_repositories[dependency].add(repository["full_name"])
    dependency_groups = [
        {"identity": dependency, "repositories": sorted(names)}
        for dependency, names in sorted(dependency_repositories.items())
        if len(names) > 1
    ]
    total_bytes = sum(file_record["bytes"] for file_record in all_files)
    unique_content_bytes = sum(unique_bytes.values())
    semantic = {
        "format": FORMAT,
        "extractor_version": EXTRACTOR_VERSION,
        "status": "bounded-public-pilot",
        "seed_sha256": sha256_value(seed),
        "snapshot_sha256": sha256_value(canonical_snapshot),
        "cohort": {"families": seed["measurement"]["families"], "repository_count": len(repositories), "selection": "explicit non-random public pilot; not representative"},
        "metrics": {
            "measured_source_files": len(all_files),
            "measured_source_bytes": total_bytes,
            "unique_content_bytes": unique_content_bytes,
            "exact_content_addressable_bytes": total_bytes - unique_content_bytes,
            "exact_cross_repository_groups": len(exact_groups),
            "measured_structural_units": sum(len(file_record.get("structure_units", ())) for file_record in all_files),
            "measured_structural_occurrences": sum(unit["occurrences"] for file_record in all_files for unit in file_record.get("structure_units", ())),
            "recurrent_structural_occurrences": sum(sum(instance["occurrences"] for instance in group["instances"]) for group in structure_groups),
            "normalized_structure_cross_repository_groups": len(structure_groups),
            "normalized_structure_cross_family_groups": sum(
                len({family_by_repository[instance["repository"]] for instance in group["instances"]}) > 1
                for group in structure_groups
            ),
            "minimum_cross_repository_reuse_coordinates": sum(
                len({instance["repository"] for instance in group["instances"]}) - 1
                for group in structure_groups
            ),
            "minimum_cross_family_reuse_coordinates": sum(
                len({family_by_repository[instance["repository"]] for instance in group["instances"]}) - 1
                for group in structure_groups
            ),
            "recurrent_dependency_groups": len(dependency_groups),
        },
        "exact_groups": exact_groups,
        "structure_groups": structure_groups,
        "dependency_groups": dependency_groups,
        "repositories": [{"family": item["family"], "full_name": item["full_name"], "commit_sha": item["commit_sha"], "license_spdx": item["license_spdx"], "source_url": item["source_url"], "archive_sha256": item["archive_sha256"], "measured_source_files": len(item["files"]), "dependencies": item["dependencies"]} for item in repositories],
        "claim_boundary": seed["claim_boundary"],
    }
    return {**semantic, "dataset_sha256": sha256_value(semantic)}


def write_canonical(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--acquire", action="store_true")
    arguments = parser.parse_args()
    seed = json.loads(arguments.seed.read_text())
    snapshot = acquire(seed) if arguments.acquire else json.loads(arguments.snapshot.read_text())
    if arguments.acquire:
        write_canonical(arguments.snapshot, snapshot)
    report = measure(seed, snapshot)
    write_canonical(arguments.output, report)
    print(json.dumps({"dataset_sha256": report["dataset_sha256"], **report["metrics"]}, sort_keys=True))


if __name__ == "__main__":
    main()
