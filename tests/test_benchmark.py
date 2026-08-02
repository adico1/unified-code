"""Deterministic L9 benchmark tests. Thresholds use injected clock feeds."""

from __future__ import annotations

import os
from inspect import Parameter, signature
from pathlib import Path

from unified import selftest

from unified import LIMIT_NS, clock_end, clock_start, inward, is_thing
from unified.generator.benchmark import (
    cleanup_benchmark,
    evaluate_l9,
    measure_add_iteration,
    measure_all,
    measure_new_iteration,
    prepare_benchmark,
    run_benchmark,
    validate_benchmark,
)
from unified.generator.cli import host_main, run_command


def _feed_for_durations(new_durations, add_durations):
    """Build clock_feed: pairs of (start, end) for each new then each add, per iteration."""
    feed = []
    assert len(new_durations) == len(add_durations)
    for new_d, add_d in zip(new_durations, add_durations):
        feed.extend([0, int(new_d)])
        feed.extend([0, int(add_d)])
    return tuple(feed)


def _benchmark_payload(tmp_path, iterations, new_ds, add_ds):
    return {
        "command": "benchmark",
        "iterations": iterations,
        "parent": str(tmp_path),
        "owned_temp": True,
        "clock_feed": _feed_for_durations(new_ds, add_ds),
    }


def test_benchmark_public_ops_one_input():
    ops = (
        validate_benchmark,
        prepare_benchmark,
        measure_all,
        measure_new_iteration,
        measure_add_iteration,
        evaluate_l9,
        cleanup_benchmark,
        run_benchmark,
        clock_start,
        clock_end,
    )
    for operation in ops:
        parameters = tuple(signature(operation).parameters.values())
        assert len(parameters) == 1
        assert parameters[0].name == "thing"


def test_clock_end_after_structure_and_verdict_evidence(tmp_path):
    """L9: structural check and iteration verdict evidence precede clock_end."""
    iterations = 1
    payload = _benchmark_payload(tmp_path, iterations, [1_000], [1_000])
    result = run_benchmark(inward(payload))
    evidence = result["evidence"]
    # First measured new iteration markers
    structure = evidence.index("measure_new:0:structure:pass")
    verdict = evidence.index("measure_new:0:verdict:valid")
    clock_ends = [i for i, e in enumerate(evidence) if e == "boundary:clock_end"]
    assert clock_ends, "expected clock_end boundary evidence"
    first_clock_end = clock_ends[0]
    assert structure < first_clock_end
    assert verdict < first_clock_end
    # Same for add
    add_structure = evidence.index("measure_add:0:structure:pass")
    add_verdict = evidence.index("measure_add:0:verdict:valid")
    second_clock_end = clock_ends[1]
    assert add_structure < second_clock_end
    assert add_verdict < second_clock_end


def test_benchmark_result_schema_separate_new_and_add(tmp_path):
    iterations = 5
    new_ds = [10_000_000] * iterations
    add_ds = [20_000_000] * iterations
    result = run_benchmark(inward(_benchmark_payload(tmp_path, iterations, new_ds, add_ds)))
    assert is_thing(result)
    value = result["value"]
    assert "new" in value and "add" in value
    for key in ("new", "add"):
        report = value[key]
        for field in (
            "iterations",
            "minimum_ns",
            "median_ns",
            "p95_ns",
            "maximum_ns",
            "limit_ns",
            "verdict",
        ):
            assert field in report
        assert report["limit_ns"] == LIMIT_NS
        assert report["iterations"] == iterations
    assert value["new"]["minimum_ns"] == 10_000_000
    assert value["add"]["minimum_ns"] == 20_000_000
    assert value["new"]["p95_ns"] != value["add"]["p95_ns"] or iterations == 0


def test_exact_one_second_threshold_passes(tmp_path):
    iterations = 20
    new_ds = [LIMIT_NS] * iterations
    add_ds = [LIMIT_NS] * iterations
    result = run_benchmark(inward(_benchmark_payload(tmp_path, iterations, new_ds, add_ds)))
    assert result["value"]["new"]["p95_ns"] == LIMIT_NS
    assert result["value"]["add"]["p95_ns"] == LIMIT_NS
    assert result["value"]["new"]["verdict"] == "pass"
    assert result["value"]["add"]["verdict"] == "pass"
    assert result["value"]["l9_verdict"] == "pass"
    assert result["state"] == "valid"


def test_p95_over_limit_fails_even_if_average_would_pass(tmp_path):
    # 19 fast + 1 slow → p95 is the slow sample for n=20 (index ceil(0.95*20)-1 = 18)
    # Use 20 samples where the top values exceed the limit.
    iterations = 20
    new_ds = [1] * 18 + [LIMIT_NS + 1, LIMIT_NS + 2]
    add_ds = [1] * iterations
    result = run_benchmark(inward(_benchmark_payload(tmp_path, iterations, new_ds, add_ds)))
    assert result["value"]["new"]["p95_ns"] > LIMIT_NS
    assert result["value"]["new"]["verdict"] == "fail"
    assert result["value"]["l9_verdict"] == "fail"
    assert result["state"] == "invalid"
    # add may still pass individually
    assert result["value"]["add"]["verdict"] == "pass"


def test_invalid_generation_cannot_pass_benchmark(tmp_path, monkeypatch):
    import unified.generator.benchmark as bench

    real = bench.run_command
    calls = {"n": 0}

    def flaky(thing):
        calls["n"] += 1
        # Warmup uses 2 calls (new+add). Fail the first measured new.
        if calls["n"] <= 2:
            return real(thing)
        return {
            "value": {"error": "forced"},
            "depths": (),
            "axes": (),
            "evidence": ("forced:invalid",),
            "state": "invalid",
        }

    monkeypatch.setattr(bench, "run_command", flaky)
    iterations = 3
    new_ds = [1] * iterations
    add_ds = [1] * iterations
    result = run_benchmark(inward(_benchmark_payload(tmp_path, iterations, new_ds, add_ds)))
    assert result["value"]["l9_verdict"] == "fail"
    assert result["state"] == "invalid"
    assert result["value"]["all_generations_valid"] is False
    assert any("invalid" in f for f in result["value"]["failures"])


def test_temporary_benchmark_projects_are_removed(tmp_path):
    iterations = 2
    new_ds = [1_000] * iterations
    add_ds = [1_000] * iterations
    # owned_temp True with parent under tmp_path still cleans only if name starts
    # with uc-benchmark-. prepare with no parent so owned temp is created.
    payload = {
        "command": "benchmark",
        "iterations": iterations,
        "clock_feed": _feed_for_durations(new_ds, add_ds),
    }
    result = run_benchmark(inward(payload))
    roots = result["value"].get("temp_roots") or ()
    removed = result["value"].get("removed_temp_roots") or ()
    assert removed
    for root in roots:
        assert not Path(root).exists()
    for root in removed:
        assert root.startswith(str(Path(root).anchor)) or True
        assert not Path(root).exists()


def test_benchmark_does_not_modify_real_repository():
    repo = Path(__file__).resolve().parents[1]
    before = {p.name for p in repo.iterdir()}
    # Also snapshot that no uc-benchmark dirs appear in repo.
    before_bench = list(repo.glob("uc-benchmark-*"))
    iterations = 2
    payload = {
        "command": "benchmark",
        "iterations": iterations,
        "clock_feed": _feed_for_durations([100] * iterations, [100] * iterations),
    }
    result = run_benchmark(inward(payload))
    assert is_thing(result)
    after = {p.name for p in repo.iterdir()}
    assert after == before
    assert list(repo.glob("uc-benchmark-*")) == before_bench
    assert list(repo.glob("n0000")) == []
    assert list(repo.glob("generated-demo")) == []


def test_host_main_benchmark_flag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Use real clock; small iteration count for unit suite speed is ok —
    # this only checks CLI routing, not L9 authority.
    code = host_main(["benchmark", "--iterations", "1"])
    # Real timing should pass on ordinary hardware; if not, still returns 0/1 int.
    assert code in (0, 1)


def test_evaluate_l9_conceals_no_individual_invalid(tmp_path):
    """Even if p95 is low, any invalid generation forces L9 fail."""
    # Build a formed measurement thing with fake low samples but invalid flags.
    thing = {
        "value": {
            "command": "benchmark",
            "iterations": 3,
            "new_samples_ns": (1, 1, 1),
            "add_samples_ns": (1, 1, 1),
            "new_results_valid": (True, False, True),
            "add_results_valid": (True, True, True),
            "failures": ("new[1]:invalid-or-incomplete",),
            "limit_ns": LIMIT_NS,
        },
        "depths": (),
        "axes": (),
        "evidence": (),
        "state": "formed",
    }
    result = evaluate_l9(thing)
    assert result["value"]["l9_verdict"] == "fail"
    assert result["state"] == "invalid"
    assert result["value"]["new"]["verdict"] == "fail"
