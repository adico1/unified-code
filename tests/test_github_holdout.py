"""Frozen unseen-holdout proof for Issue #47."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from unified import selftest
from unified.boundary import inward
from unified.generator.application_language.seed_compiler import assemble
from unified.github_candidates import extract_candidate_seeds
from unified.github_corpus import replay_fixture_pack
from unified.github_normalization import normalize_repositories
from unified.machine.thing import blank_thing
from unified.standard_generate import request_feature


ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = ROOT / "seed" / "github_corpus" / "holdout"
ACCEPTED = HOLDOUT / "accepted"
GENERATED = ROOT / "build" / "holdouts" / "documented-keyboard-calculator-holdout@1"
COMPILER_BASELINE = "ca64e9fe7ed25a0d30b12ff8b1420329ed61780e23a20c93157a7b06a699af98"


def _load(path):
    return json.loads(path.read_text())


def _extract(directory):
    pack = _load(directory / "PACK.json")
    pages = {
        item["path"]: (directory / item["path"]).read_text()
        for item in pack["pages"]
    }
    replay = replay_fixture_pack(
        inward({"fixture_pack": {"manifest": copy.deepcopy(pack), "page_texts": pages}})
    )
    assert replay["state"] == "valid"
    normalized = normalize_repositories(
        inward(
            {
                "snapshot": replay["value"]["semantic_snapshot"],
                "snapshot_sha256": replay["value"]["snapshot_sha256"],
            }
        )
    )
    assert normalized["state"] == "valid"
    extracted = extract_candidate_seeds(
        inward(
            {
                "normalization": normalized["value"],
                "observations": _load(directory / "OBSERVATIONS.json"),
            }
        )
    )
    assert extracted["state"] == "valid"
    return replay, normalized, extracted


def _gap():
    return request_feature(
        blank_thing(
            {
                "kind": "application-language-without-backspace-control",
                "paths": ["seed/github_corpus/holdout/application.seed.json"],
            }
        )
    )


def test_holdouts_were_pinned_before_evaluation_and_replay_deterministically():
    identities = []
    for directory, commit, repository in (
        (HOLDOUT, "dff0c896e59f19ca9a7c007bc4dd30f20385c722", "github:repository:609855380"),
        (ACCEPTED, "4d2fa2752f30c42dbca87a469879a4781f79502e", "github:repository:995929651"),
    ):
        pin = _load(directory / "PIN.json")
        assert pin["pinned_before_evaluation"] is True
        assert pin["repository"]["commit_sha256_identity"] == commit
        assert pin["repository"]["repository_identity"] == repository
        assert pin["generic_compiler_baseline"]["application_language_sha256"] == COMPILER_BASELINE
        first = _extract(directory)
        second = _extract(directory)
        assert first == second
        candidate = first[2]["value"]["candidate_seeds"][0]
        assert candidate["catalog_status"] == "candidate"
        assert candidate["promotion_eligible"] is False
        identities.append(candidate["candidate_identity"])
    assert len(set(identities)) == 2


def test_unsupported_semantics_emit_exact_standard_gap_without_fallback():
    with selftest.raises(KeyError, match="backspace"):
        assemble(HOLDOUT / "application.seed.json")
    first = _gap()
    assert first == _gap()
    assert first["state"] == "invalid"
    assert first["value"]["error"] == "standard.gap"
    assert first["value"]["gap_id"] == "gap.unsupported-feature:application-language-without-backspace-control"
    assert first["value"]["gap"]["status"] == "open"
    assert first["value"]["ticket"]["error_type"] == "StandardGap"
    assert first["evidence"] == (
        "standard.gap",
        "standard.gap:gap.unsupported-feature:application-language-without-backspace-control",
        "standard.rule:non-fallback",
        "event:ticket.open",
    )
    assert not (ROOT / "build" / "holdouts" / "dark-four-operation-calculator-holdout@1").exists()


def test_accepted_holdout_generates_exactly_and_repeats_byte_identically():
    seed = ACCEPTED / "application.seed.json"
    first_manifest, first_files = assemble(seed)
    second_manifest, second_files = assemble(seed)
    assert first_manifest == second_manifest
    assert first_files == second_files
    assert first_manifest["compiler_sha256"] == COMPILER_BASELINE
    assert first_manifest["tree_sha256"] == "bc4a12032771aaaec094bec5240c66817a6fec19c9c71ae778461d60de58ded8"
    assert first_manifest["verification"] == {
        "cases": ["holdout.add", "holdout.subtract", "holdout.multiply", "holdout.divide", "holdout.divide-zero", "derived.division-by-zero", "derived.invalid-expression"],
        "passed": 7,
        "total": 7,
    }
    assert first_manifest["manual_application_files"] == 0
    assert first_manifest["manual_test_files"] == 0
    assert first_manifest["runtime_seed_files"] == 0
    assert first_manifest["runtime_shared_engine_files"] == 0
    assert first_manifest["precompile"]["missing_capabilities"] == []
    assert first_manifest["precompile"]["excess_capabilities"] == []
    assert first_manifest["precompile"]["verdict"] == "pass"
    for name, content in first_files.items():
        assert (GENERATED / name).read_bytes() == content
    runtime = first_files["main.py"].decode()
    assert "application.seed.json" not in runtime
    assert "github_corpus" not in runtime
    assert "eval(" not in runtime
    assert "exec(" not in runtime


def test_candidate_traceability_reaches_the_accepted_seed_and_artifact():
    _, normalized, extracted = _extract(ACCEPTED)
    candidate = extracted["value"]["candidate_seeds"][0]
    seed = _load(ACCEPTED / "application.seed.json")
    manifest = _load(GENERATED / "manifest.json")
    assert normalized["value"]["normalization_sha256"] == "cd9ac53dc93eba8dcfbd77e9983424c2a2c394b958aed2a7e126551631985445"
    assert candidate["candidate_identity"] == "62187c089719bbfdd9ba8277c86137245dd4ddeaba06dd4edfa8f9d168fc3ba6"
    assert candidate["candidate_seed_sha256"] == "e2ed67bbe75ab108ca8aa891bff7dceecb1dc7d8e17752b07ae2d6c509c22c4c"
    assert seed["what"]["identity"]["canonical"] == "uc://applications/documented-keyboard-calculator-holdout@1"
    assert manifest["seed_sha256"] == "00b20b1cef28f9bb13647227b02af475daddba2bc8c5ea49a929493c24ec5889"
    assert manifest["tree_sha256"] == "bc4a12032771aaaec094bec5240c66817a6fec19c9c71ae778461d60de58ded8"
    assert {item["verdict"] for item in candidate["assessments"]} == {"valid", "foreign", "missing", "unresolved"}
    assert all(evidence["revision"] in evidence["source_url"] for evidence in candidate["traceability"])

    evaluation = _load(HOLDOUT / "EVALUATION.json")
    assert evaluation["accepted"]["candidate_identity"] == candidate["candidate_identity"]
    assert evaluation["accepted"]["repeated_tree_sha256"] == [manifest["tree_sha256"]] * 2
    assert evaluation["compiler"]["application_language_sha256_before"] == COMPILER_BASELINE
    assert evaluation["compiler"]["application_language_sha256_after"] == COMPILER_BASELINE
    assert evaluation["compiler"]["changed_files"] == []
    assert evaluation["compiler"]["generic_runtime_changed_files"] == []


def test_holdout_does_not_enter_production_registry_or_generic_vocabulary():
    assert "holdout" not in (ROOT / "seed" / "registry.json").read_text()
    generic = "\n".join(
        path.read_text()
        for path in sorted((ROOT / "unified" / "generator" / "application_language").glob("*.py"))
    )
    for term in (
        "Carlos-Guilherme",
        "calculator-customtk",
        "nityasaini",
        "documented-keyboard-calculator-holdout",
        "dark-four-operation-calculator-holdout",
    ):
        assert term not in generic
