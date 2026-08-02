"""Evidence-bearing candidate seed extraction from canonical records.

Candidate declarations remain outside the proven application registry.  This
module performs no network access, source execution, application inference,
or compiler mutation.
"""

from __future__ import annotations

from .machine.canonical import canonical_sha256
from .thing import is_thing


CANDIDATE_VERSION = "UC-GITHUB-CANDIDATE-SEED-1"
OBSERVATION_VERSION = "UC-GITHUB-CANDIDATE-OBSERVATIONS-1"
LETTER_VERDICTS = frozenset(
    {"valid", "missing", "foreign", "duplicate", "misplaced", "unresolved"}
)
REVIEW_STATUSES = frozenset({"pending", "reviewed-candidate", "rejected"})


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
        {"errors": tuple(errors), "ticket": None},
        "candidate-extraction:invalid",
        "invalid",
    )


def audited_is_sha256_primitive(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(letter in "0123456789abcdef" for letter in value)
    )


def audited_normalization_semantic_primitive(normalization):
    return {
        key: normalization[key]
        for key in (
            "candidate_groups",
            "normalization_version",
            "relationship_edges",
            "repositories",
            "snapshot_sha256",
            "snapshot_status",
            "unresolved",
        )
    }


def audited_normalization_errors_primitive(normalization):
    if not isinstance(normalization, dict):
        return ("candidate:normalization:type",)
    required = {
        "candidate_groups",
        "errors",
        "normalization_sha256",
        "normalization_version",
        "relationship_edges",
        "repositories",
        "snapshot_sha256",
        "snapshot_status",
        "ticket",
        "unresolved",
    }
    if set(normalization) != required:
        return ("candidate:normalization:fields",)
    if normalization.get("errors") or normalization.get("ticket") is not None:
        return ("candidate:normalization:not-valid",)
    if canonical_sha256(
        audited_normalization_semantic_primitive(normalization)
    ) != normalization.get("normalization_sha256"):
        return ("candidate:normalization:sha256",)
    return ()


def audited_evidence_errors_primitive(evidence):
    if not isinstance(evidence, list) or not evidence:
        return ("candidate:evidence:type",)
    expected = {
        "evidence_id",
        "license_spdx",
        "location",
        "observation",
        "repository_identity",
        "revision",
        "source_path",
        "source_sha256",
        "source_url",
    }
    errors = []
    for ordinal, item in enumerate(evidence):
        prefix = f"candidate:evidence:{ordinal}"
        if not isinstance(item, dict) or set(item) != expected:
            errors.append(f"{prefix}:fields")
            continue
        for field in (
            "evidence_id",
            "license_spdx",
            "location",
            "observation",
            "repository_identity",
            "revision",
            "source_path",
            "source_url",
        ):
            if not isinstance(item.get(field), str) or not item.get(field):
                errors.append(f"{prefix}:{field}")
        if not audited_is_sha256_primitive(item.get("source_sha256")):
            errors.append(f"{prefix}:source-sha256")
        if isinstance(item.get("source_url"), str) and isinstance(
            item.get("revision"), str
        ) and item["revision"] not in item["source_url"]:
            errors.append(f"{prefix}:unpinned-url")
    identities = [
        item.get("evidence_id") for item in evidence if isinstance(item, dict)
    ]
    if len(identities) != len(set(identities)):
        errors.append("candidate:evidence:duplicate-identity")
    return tuple(errors)


def audited_assessment_errors_primitive(
    assessments, evidence_by_id, repository_identity, candidate_ordinal
):
    if not isinstance(assessments, list) or not assessments:
        return (f"candidate:{candidate_ordinal}:assessments:type",)
    expected = {
        "assessment_id",
        "evidence_ids",
        "expected_role",
        "letter_id",
        "observed_role",
        "reason",
        "value",
        "verdict",
    }
    errors = []
    assessment_ids = []
    valid_letter_ids = []
    duplicate_letter_ids = []
    for ordinal, assessment in enumerate(assessments):
        prefix = f"candidate:{candidate_ordinal}:assessment:{ordinal}"
        if not isinstance(assessment, dict) or set(assessment) != expected:
            errors.append(f"{prefix}:fields")
            continue
        assessment_ids.append(assessment.get("assessment_id"))
        verdict = assessment.get("verdict")
        evidence_ids = assessment.get("evidence_ids")
        if not isinstance(assessment.get("assessment_id"), str) or not assessment.get(
            "assessment_id"
        ):
            errors.append(f"{prefix}:assessment-id")
        if not isinstance(assessment.get("letter_id"), str) or not assessment.get(
            "letter_id"
        ):
            errors.append(f"{prefix}:letter-id")
        if verdict not in LETTER_VERDICTS:
            errors.append(f"{prefix}:verdict")
        if not isinstance(evidence_ids, list) or not all(
            isinstance(identity, str) and identity in evidence_by_id
            for identity in evidence_ids or ()
        ):
            errors.append(f"{prefix}:evidence")
            evidence_ids = []
        if any(
            evidence_by_id[identity]["repository_identity"] != repository_identity
            for identity in evidence_ids
            if identity in evidence_by_id
        ):
            errors.append(f"{prefix}:foreign-evidence")
        if verdict in {"valid", "foreign", "duplicate", "misplaced"} and not evidence_ids:
            errors.append(f"{prefix}:evidence-required")
        if verdict in {"missing", "unresolved"} and not isinstance(
            assessment.get("reason"), str
        ):
            errors.append(f"{prefix}:reason-required")
        if verdict == "valid":
            valid_letter_ids.append(assessment.get("letter_id"))
            if assessment.get("value") is None:
                errors.append(f"{prefix}:value-required")
            if assessment.get("expected_role") != assessment.get("observed_role"):
                errors.append(f"{prefix}:role")
        if verdict == "misplaced" and assessment.get(
            "expected_role"
        ) == assessment.get("observed_role"):
            errors.append(f"{prefix}:misplaced-role")
        if verdict == "duplicate":
            duplicate_letter_ids.append(assessment.get("letter_id"))
    if len(assessment_ids) != len(set(assessment_ids)):
        errors.append(f"candidate:{candidate_ordinal}:assessment:duplicate-identity")
    if not set(duplicate_letter_ids).issubset(set(valid_letter_ids)):
        errors.append(f"candidate:{candidate_ordinal}:duplicate-without-valid")
    return tuple(errors)


def audited_candidate_errors_primitive(
    candidates, evidence_by_id, repository_identities
):
    if not isinstance(candidates, list) or not candidates:
        return ("candidate:declarations:type",)
    expected = {
        "assessments",
        "boundary_evidence_ids",
        "boundary_path",
        "human_review",
        "repository_identity",
    }
    errors = []
    repository_boundaries = []
    for ordinal, candidate in enumerate(candidates):
        prefix = f"candidate:{ordinal}"
        if not isinstance(candidate, dict) or set(candidate) != expected:
            errors.append(f"{prefix}:fields")
            continue
        repository_identity = candidate.get("repository_identity")
        if repository_identity not in repository_identities:
            errors.append(f"{prefix}:repository")
        boundary_path = candidate.get("boundary_path")
        if not isinstance(boundary_path, str) or not boundary_path:
            errors.append(f"{prefix}:boundary-path")
        elif boundary_path.startswith("/") or ".." in boundary_path.split("/"):
            errors.append(f"{prefix}:boundary-path")
        repository_boundaries.append((repository_identity, boundary_path))
        boundary_evidence = candidate.get("boundary_evidence_ids")
        if not isinstance(boundary_evidence, list) or not boundary_evidence:
            errors.append(f"{prefix}:boundary-evidence")
        elif any(identity not in evidence_by_id for identity in boundary_evidence):
            errors.append(f"{prefix}:boundary-evidence")
        elif any(
            evidence_by_id[identity]["repository_identity"]
            != repository_identity
            for identity in boundary_evidence
        ):
            errors.append(f"{prefix}:boundary-foreign-evidence")
        review = candidate.get("human_review")
        if not isinstance(review, dict) or set(review) != {
            "reviewer",
            "status",
            "verdict",
        }:
            errors.append(f"{prefix}:human-review")
        elif review.get("status") not in REVIEW_STATUSES:
            errors.append(f"{prefix}:review-status")
        elif review["status"] == "pending" and (
            review.get("reviewer") is not None or review.get("verdict") is not None
        ):
            errors.append(f"{prefix}:pending-review-fields")
        elif review["status"] != "pending" and (
            not isinstance(review.get("reviewer"), str)
            or not review.get("reviewer")
            or not isinstance(review.get("verdict"), str)
            or not review.get("verdict")
        ):
            errors.append(f"{prefix}:completed-review-fields")
        errors.extend(
            audited_assessment_errors_primitive(
                candidate.get("assessments"),
                evidence_by_id,
                repository_identity,
                ordinal,
            )
        )
    if len(repository_boundaries) != len(set(repository_boundaries)):
        errors.append("candidate:duplicate-boundary")
    return tuple(errors)


def audited_observation_errors_primitive(observations, normalization):
    if not isinstance(observations, dict) or set(observations) != {
        "candidates",
        "evidence",
        "format_version",
        "normalization_sha256",
    }:
        return ("candidate:observations:fields",)
    errors = []
    if observations.get("format_version") != OBSERVATION_VERSION:
        errors.append("candidate:observations:format-version")
    if observations.get("normalization_sha256") != normalization.get(
        "normalization_sha256"
    ):
        errors.append("candidate:observations:normalization-sha256")
    evidence = observations.get("evidence")
    errors.extend(audited_evidence_errors_primitive(evidence))
    evidence_by_id = {
        item["evidence_id"]: item
        for item in evidence or ()
        if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
    }
    repository_identities = frozenset(
        repository["repository_identity"]
        for repository in normalization.get("repositories", ())
    )
    if any(
        item.get("repository_identity") not in repository_identities
        for item in evidence or ()
        if isinstance(item, dict)
    ):
        errors.append("candidate:evidence:repository")
    errors.extend(
        audited_candidate_errors_primitive(
            observations.get("candidates"), evidence_by_id, repository_identities
        )
    )
    return tuple(errors)


def audited_assessment_primitive(assessment):
    semantic = {
        key: assessment[key]
        for key in (
            "assessment_id",
            "evidence_ids",
            "expected_role",
            "letter_id",
            "observed_role",
            "reason",
            "value",
            "verdict",
        )
    }
    return {**semantic, "assessment_sha256": canonical_sha256(semantic)}


def audited_observation_authority_primitive(observations):
    """Canonicalize declaration collections whose input order has no meaning."""
    return {
        "candidates": tuple(
            sorted(
                (
                    {
                        **candidate,
                        "assessments": tuple(
                            sorted(
                                candidate["assessments"],
                                key=lambda item: item["assessment_id"],
                            )
                        ),
                        "boundary_evidence_ids": tuple(
                            sorted(candidate["boundary_evidence_ids"])
                        ),
                    }
                    for candidate in observations["candidates"]
                ),
                key=lambda item: (
                    item["repository_identity"], item["boundary_path"]
                ),
            )
        ),
        "evidence": tuple(
            sorted(observations["evidence"], key=lambda item: item["evidence_id"])
        ),
        "format_version": observations["format_version"],
        "normalization_sha256": observations["normalization_sha256"],
    }


def audited_candidate_seed_primitive(candidate, evidence_by_id, normalization):
    assessments = tuple(
        sorted(
            (
                audited_assessment_primitive(assessment)
                for assessment in candidate["assessments"]
            ),
            key=lambda assessment: assessment["assessment_id"],
        )
    )
    semantics = tuple(
        {
            "evidence_ids": assessment["evidence_ids"],
            "letter_id": assessment["letter_id"],
            "role": assessment["expected_role"],
            "value": assessment["value"],
        }
        for assessment in assessments
        if assessment["verdict"] == "valid"
    )
    used_evidence = frozenset(
        evidence_id
        for assessment in assessments
        for evidence_id in assessment["evidence_ids"]
    ) | frozenset(candidate["boundary_evidence_ids"])
    traceability = tuple(
        {
            **evidence_by_id[evidence_id],
            "observation_sha256": canonical_sha256(
                {"observation": evidence_by_id[evidence_id]["observation"]}
            ),
        }
        for evidence_id in sorted(used_evidence)
    )
    candidate_identity = canonical_sha256(
        {
            "boundary_path": candidate["boundary_path"],
            "repository_identity": candidate["repository_identity"],
        }
    )
    semantic = {
        "assessments": assessments,
        "boundary_path": candidate["boundary_path"],
        "candidate_identity": candidate_identity,
        "candidate_version": CANDIDATE_VERSION,
        "catalog_status": "candidate",
        "human_review": dict(sorted(candidate["human_review"].items())),
        "normalization_sha256": normalization["normalization_sha256"],
        "promotion_eligible": False,
        "repository_identity": candidate["repository_identity"],
        "semantics": semantics,
        "traceability": traceability,
    }
    return {**semantic, "candidate_seed_sha256": canonical_sha256(semantic)}


def audited_extract_candidate_seeds_primitive(thing):
    if not is_thing(thing):
        return audited_invalid_primitive(thing, ("thing:invalid",))
    value = thing.get("value")
    if not isinstance(value, dict) or set(value) != {
        "normalization",
        "observations",
    }:
        return audited_invalid_primitive(thing, ("candidate:input-fields",))
    normalization = value["normalization"]
    observations = value["observations"]
    errors = audited_normalization_errors_primitive(normalization)
    errors += audited_observation_errors_primitive(observations, normalization)
    if errors:
        return audited_invalid_primitive(thing, errors)
    evidence_by_id = {
        item["evidence_id"]: item for item in observations["evidence"]
    }
    candidates = tuple(
        sorted(
            (
                audited_candidate_seed_primitive(
                    candidate, evidence_by_id, normalization
                )
                for candidate in observations["candidates"]
            ),
            key=lambda candidate: candidate["candidate_identity"],
        )
    )
    semantic = {
        "candidate_seeds": candidates,
        "candidate_version": CANDIDATE_VERSION,
        "normalization_sha256": normalization["normalization_sha256"],
        "observation_authority_sha256": canonical_sha256(
            audited_observation_authority_primitive(observations)
        ),
    }
    return _result(
        thing,
        {
            **semantic,
            "extraction_sha256": canonical_sha256(semantic),
            "errors": (),
            "ticket": None,
        },
        "candidate-extraction:completed",
        "valid",
    )


def extract_candidate_seeds(thing):
    """Public Part: one normalized evidence Thing in, candidate seeds out."""
    return audited_extract_candidate_seeds_primitive(thing)
