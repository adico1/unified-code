"""Deterministic repository normalization for canonical GitHub snapshots.

The module is pure.  It does not acquire repositories, infer applications,
rank candidates, or select a winner from ambiguous relationships.
"""

from __future__ import annotations

from .github_corpus import (
    audited_snapshot_errors_primitive,
    canonical_snapshot_payload,
)
from .machine.canonical import canonical_sha256
from .thing import is_thing


NORMALIZATION_VERSION = "UC-GITHUB-REPOSITORY-NORMALIZATION-1"
AVAILABILITY = frozenset({"available", "deleted", "unavailable"})
RELATION_KINDS = frozenset({"fork_of", "mirror_of"})


def _result(thing, value, mark, state):
    return {
        **thing,
        "value": value,
        "evidence": (*thing.get("evidence", ()), mark),
        "state": state,
    }


def audited_invalid_primitive(thing, errors):
    base = thing if is_thing(thing) else {
        "value": thing,
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": "invalid",
    }
    return _result(
        base,
        {
            "errors": tuple(errors),
            "ticket": None,
        },
        "normalization:invalid",
        "invalid",
    )


def audited_boundary_errors_primitive(boundaries, source_identity):
    if boundaries is None:
        return ()
    if not isinstance(boundaries, list):
        return (f"repository:{source_identity}:candidate-boundaries:type",)
    errors = []
    for ordinal, path in enumerate(boundaries):
        prefix = f"repository:{source_identity}:candidate-boundary:{ordinal}"
        if not isinstance(path, str) or not path:
            errors.append(f"{prefix}:type")
            continue
        segments = path.split("/")
        if path.startswith("/") or path.endswith("/") or ".." in segments:
            errors.append(f"{prefix}:path")
    if len(boundaries) != len(set(boundaries)):
        errors.append(f"repository:{source_identity}:candidate-boundary:duplicate")
    return tuple(errors)


def audited_relationship_errors_primitive(relationships, source_identity):
    if relationships is None:
        return ()
    if not isinstance(relationships, list):
        return (f"repository:{source_identity}:relationships:type",)
    errors = []
    expected = {"evidence_url", "kind", "target_identity"}
    for ordinal, relation in enumerate(relationships):
        prefix = f"repository:{source_identity}:relationship:{ordinal}"
        if not isinstance(relation, dict) or set(relation) != expected:
            errors.append(f"{prefix}:fields")
            continue
        if relation.get("kind") not in RELATION_KINDS:
            errors.append(f"{prefix}:kind")
        if not isinstance(relation.get("target_identity"), str) or not relation.get(
            "target_identity"
        ):
            errors.append(f"{prefix}:target")
        elif relation.get("target_identity") == source_identity:
            errors.append(f"{prefix}:self-target")
        if not isinstance(relation.get("evidence_url"), str) or not relation.get(
            "evidence_url"
        ):
            errors.append(f"{prefix}:evidence-url")
    canonical_relations = [
        (
            relation.get("kind"),
            relation.get("target_identity"),
            relation.get("evidence_url"),
        )
        for relation in relationships
        if isinstance(relation, dict)
    ]
    if len(canonical_relations) != len(set(canonical_relations)):
        errors.append(f"repository:{source_identity}:relationship:duplicate")
    return tuple(errors)


def audited_record_errors_primitive(record):
    if not isinstance(record, dict) or set(record) != {"payload", "source_identity"}:
        return ("repository:record:fields",)
    source_identity = record.get("source_identity")
    if not isinstance(source_identity, str) or not source_identity:
        return ("repository:identity",)
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return (f"repository:{source_identity}:payload",)
    errors = []
    source_url = payload.get("source_url") or payload.get("html_url")
    if not isinstance(source_url, str) or not source_url:
        errors.append(f"repository:{source_identity}:source-url")
    availability = payload.get("availability", "available")
    if availability not in AVAILABILITY:
        errors.append(f"repository:{source_identity}:availability")
    archived = payload.get("archived")
    if archived is not None and not isinstance(archived, bool):
        errors.append(f"repository:{source_identity}:archived")
    previous_names = payload.get("previous_names", [])
    if not isinstance(previous_names, list) or not all(
        isinstance(name, str) and name for name in previous_names
    ):
        errors.append(f"repository:{source_identity}:previous-names")
    elif len(previous_names) != len(set(previous_names)):
        errors.append(f"repository:{source_identity}:previous-name:duplicate")
    elif payload.get("full_name") in previous_names:
        errors.append(f"repository:{source_identity}:previous-name:current")
    errors.extend(
        audited_boundary_errors_primitive(
            payload.get("candidate_boundaries"), source_identity
        )
    )
    errors.extend(
        audited_relationship_errors_primitive(
            payload.get("relationships"), source_identity
        )
    )
    return tuple(errors)


def audited_input_errors_primitive(value):
    if not isinstance(value, dict) or set(value) != {
        "snapshot",
        "snapshot_sha256",
    }:
        return ("normalization:input-fields",)
    snapshot = value.get("snapshot")
    if not isinstance(snapshot, dict):
        return ("normalization:snapshot:type",)
    if set(snapshot) != {
        "completion",
        "format_version",
        "pages",
        "request",
        "status",
    }:
        return ("normalization:snapshot-fields",)
    validation_snapshot = {
        **snapshot,
        "evidence": {
            "acquisition_mode": "replay",
            "attempts": [],
            "duration_ns": 0,
            "observed_at": "1970-01-01T00:00:00Z",
        },
    }
    errors = list(audited_snapshot_errors_primitive(validation_snapshot))
    pages = snapshot.get("pages")
    records = []
    if isinstance(pages, list):
        for page in pages:
            if isinstance(page, dict) and isinstance(page.get("records"), list):
                records.extend(page["records"])
    for record in records:
        errors.extend(audited_record_errors_primitive(record))
    identities = [
        record.get("source_identity")
        for record in records
        if isinstance(record, dict)
    ]
    if len(identities) != len(set(identities)):
        errors.append("normalization:duplicate-repository-identity")
    if errors:
        return tuple(errors)
    canonical_snapshot = canonical_snapshot_payload(snapshot)
    if canonical_sha256(canonical_snapshot) != value.get("snapshot_sha256"):
        return ("normalization:snapshot-sha256",)
    return tuple(errors)


def audited_records_primitive(snapshot):
    return tuple(
        record
        for page in snapshot["pages"]
        for record in page["records"]
    )


def audited_archive_state_primitive(payload):
    archived = payload.get("archived")
    return {True: "archived", False: "active", None: "unknown"}[archived]


def audited_repository_primitive(record):
    payload = record["payload"]
    source_identity = record["source_identity"]
    boundaries = payload.get("candidate_boundaries")
    normalized_boundaries = tuple(
        {
            "boundary_identity": canonical_sha256(
                {"path": path, "repository_identity": source_identity}
            ),
            "path": path,
            "repository_identity": source_identity,
        }
        for path in sorted(boundaries or ())
    )
    semantic = {
        "archive_state": audited_archive_state_primitive(payload),
        "availability": payload.get("availability", "available"),
        "candidate_boundaries": normalized_boundaries,
        "candidate_boundary_status": (
            "declared" if boundaries is not None else "unresolved"
        ),
        "current_name": payload.get("full_name"),
        "previous_names": tuple(sorted(payload.get("previous_names", ()))),
        "repository_identity": source_identity,
        "source_url": payload.get("source_url") or payload.get("html_url"),
    }
    return {
        **semantic,
        "repository_sha256": canonical_sha256(semantic),
    }


def audited_raw_edges_primitive(records):
    return tuple(
        {
            "evidence_url": relation["evidence_url"],
            "kind": relation["kind"],
            "source_identity": record["source_identity"],
            "target_identity": relation["target_identity"],
        }
        for record in records
        for relation in record["payload"].get("relationships", ())
    )


def audited_relationship_edges_primitive(records):
    known = frozenset(record["source_identity"] for record in records)
    raw_edges = audited_raw_edges_primitive(records)
    targets_by_source = {}
    for edge in raw_edges:
        targets_by_source.setdefault(edge["source_identity"], set()).add(
            edge["target_identity"]
        )
    edges = []
    for edge in raw_edges:
        status = "resolved"
        if len(targets_by_source[edge["source_identity"]]) > 1:
            status = "ambiguous"
        elif edge["target_identity"] not in known:
            status = "unresolved"
        semantic = {**edge, "status": status}
        edges.append(
            {
                **semantic,
                "relationship_sha256": canonical_sha256(semantic),
            }
        )
    return tuple(
        sorted(
            edges,
            key=lambda edge: (
                edge["source_identity"],
                edge["kind"],
                edge["target_identity"],
                edge["evidence_url"],
            ),
        )
    )


def audited_find_primitive(parents, identity):
    current = identity
    while parents[current] != current:
        current = parents[current]
    return current


def audited_candidate_groups_primitive(repositories, edges):
    identities = tuple(
        repository["repository_identity"] for repository in repositories
    )
    parents = {identity: identity for identity in identities}
    for edge in edges:
        if edge["status"] != "resolved":
            continue
        left = audited_find_primitive(parents, edge["source_identity"])
        right = audited_find_primitive(parents, edge["target_identity"])
        if left != right:
            first, second = sorted((left, right))
            parents[second] = first
    components = {}
    for identity in identities:
        root = audited_find_primitive(parents, identity)
        components.setdefault(root, []).append(identity)
    groups = []
    for members in components.values():
        ordered = tuple(sorted(members))
        semantic = {
            "members": ordered,
            "selection_status": "single" if len(ordered) == 1 else "unresolved",
        }
        groups.append(
            {
                **semantic,
                "candidate_group_identity": canonical_sha256(semantic),
            }
        )
    return tuple(
        sorted(groups, key=lambda group: group["candidate_group_identity"])
    )


def audited_unresolved_primitive(repositories, edges, groups):
    unresolved = []
    for repository in repositories:
        identity = repository["repository_identity"]
        if repository["archive_state"] == "unknown":
            unresolved.append(
                {"identity": identity, "reason": "archive-state-unresolved"}
            )
        if repository["candidate_boundary_status"] == "unresolved":
            unresolved.append(
                {"identity": identity, "reason": "candidate-boundary-unresolved"}
            )
    for edge in edges:
        if edge["status"] != "resolved":
            unresolved.append(
                {
                    "identity": edge["relationship_sha256"],
                    "reason": f"relationship-{edge['status']}",
                }
            )
    for group in groups:
        if group["selection_status"] == "unresolved":
            unresolved.append(
                {
                    "identity": group["candidate_group_identity"],
                    "reason": "canonical-winner-unresolved",
                }
            )
    return tuple(
        sorted(unresolved, key=lambda item: (item["reason"], item["identity"]))
    )


def audited_normalize_repositories_primitive(thing):
    if not is_thing(thing):
        return audited_invalid_primitive(thing, ("thing:invalid",))
    value = thing.get("value")
    errors = audited_input_errors_primitive(value)
    if errors:
        return audited_invalid_primitive(thing, errors)
    records = audited_records_primitive(value["snapshot"])
    repositories = tuple(
        sorted(
            (audited_repository_primitive(record) for record in records),
            key=lambda repository: repository["repository_identity"],
        )
    )
    edges = audited_relationship_edges_primitive(records)
    groups = audited_candidate_groups_primitive(repositories, edges)
    unresolved = audited_unresolved_primitive(repositories, edges, groups)
    semantic = {
        "candidate_groups": groups,
        "normalization_version": NORMALIZATION_VERSION,
        "relationship_edges": edges,
        "repositories": repositories,
        "snapshot_sha256": value["snapshot_sha256"],
        "snapshot_status": value["snapshot"]["status"],
        "unresolved": unresolved,
    }
    return _result(
        thing,
        {
            **semantic,
            "normalization_sha256": canonical_sha256(semantic),
            "errors": (),
            "ticket": None,
        },
        "normalization:completed",
        "valid",
    )


def normalize_repositories(thing):
    """Public Part: one canonical snapshot Thing in, one normalized Thing out."""
    return audited_normalize_repositories_primitive(thing)
