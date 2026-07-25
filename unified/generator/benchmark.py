"""L9 construction benchmark: real uc new / uc add in temporary directories.

Composition:

    outward(
        cleanup_benchmark(
            evaluate_l9(
                measure_all(
                    prepare_benchmark(
                        validate_benchmark(thing)
                    )
                )
            )
        )
    )
"""

from __future__ import annotations

import math
import shutil
import tempfile
from pathlib import Path

from ..boundary import inward, outward
from ..clock import LIMIT_NS, clock_end, clock_start
from ..thing import is_thing
from .cli import run_command

REQUIRED_NEW_RELATIVE = (
    "pyproject.toml",
    "README.md",
)


def validate_benchmark(thing):
    """Validate benchmark host command shape."""
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("validate_benchmark:rejected-non-thing",),
            "state": "invalid",
        }

    value = thing["value"]
    if value is None:
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate_benchmark:absent"),
            "state": "absent",
        }
    if value is False:
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate_benchmark:false"),
            "state": "false",
        }
    if not isinstance(value, dict):
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate_benchmark:not-map"),
            "state": "invalid",
        }
    if value.get("command") != "benchmark":
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate_benchmark:not-benchmark"),
            "state": "invalid",
        }

    iterations = value.get("iterations", 10)
    if iterations is None:
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate_benchmark:absent-iterations"),
            "state": "absent",
        }
    if iterations is False:
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate_benchmark:false-iterations"),
            "state": "false",
        }
    if not isinstance(iterations, int) or isinstance(iterations, bool) or iterations < 1:
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate_benchmark:bad-iterations"),
            "state": "invalid",
        }
    if iterations > 10_000:
        return {
            **thing,
            "evidence": (*thing["evidence"], "validate_benchmark:iterations-too-large"),
            "state": "invalid",
        }

    return {
        **thing,
        "value": {
            **value,
            "iterations": iterations,
            "limit_ns": LIMIT_NS,
            "new_samples_ns": (),
            "add_samples_ns": (),
            "new_results_valid": (),
            "add_results_valid": (),
            "failures": (),
            "temp_roots": (),
        },
        "evidence": (*thing["evidence"], "validate_benchmark:ok"),
        "state": "formed",
    }


def prepare_benchmark(thing):
    """Create an isolated temporary root for all benchmark projects."""
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("prepare_benchmark:rejected-non-thing",),
            "state": "invalid",
        }
    if thing["state"] in {"invalid", "absent", "false"}:
        return {
            **thing,
            "evidence": (*thing["evidence"], "prepare_benchmark:skipped"),
            "state": thing["state"],
        }

    value = thing["value"]
    if not isinstance(value, dict):
        return {
            **thing,
            "evidence": (*thing["evidence"], "prepare_benchmark:value-not-map"),
            "state": "invalid",
        }

    # Allow tests to inject an existing parent directory.
    parent = value.get("parent")
    if parent is None:
        root = Path(tempfile.mkdtemp(prefix="uc-benchmark-"))
        owned = True
    else:
        root = Path(parent).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        owned = bool(value.get("owned_temp", False))

    return {
        **thing,
        "value": {
            **value,
            "parent": str(root),
            "owned_temp": owned,
            "temp_roots": (str(root),),
            "repo_root_marker": str(Path.cwd().resolve()),
        },
        "evidence": (*thing["evidence"], "prepare_benchmark:ready", f"prepare:parent:{root}"),
        "state": "formed",
    }


def measure_all(thing):
    """Warm up once, then measure new and add for each iteration."""
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("measure_all:rejected-non-thing",),
            "state": "invalid",
        }
    if thing["state"] in {"invalid", "absent", "false"}:
        return {
            **thing,
            "evidence": (*thing["evidence"], "measure_all:skipped"),
            "state": thing["state"],
        }

    # Warm-up (not included in samples).
    thing = _warmup(thing)
    if thing["state"] in {"invalid", "absent", "false"}:
        return thing

    iterations = thing["value"]["iterations"]
    for index in range(iterations):
        thing = measure_new_iteration(thing, index)
        if thing["state"] in {"invalid", "absent", "false", "unknown"} and _hard_stop(
            thing
        ):
            return thing
        thing = measure_add_iteration(thing, index)
        if thing["state"] in {"invalid", "absent", "false", "unknown"} and _hard_stop(
            thing
        ):
            return thing

    return {
        **thing,
        "evidence": (
            *thing["evidence"],
            f"measure_all:new:{len(thing['value'].get('new_samples_ns', ()))}",
            f"measure_all:add:{len(thing['value'].get('add_samples_ns', ()))}",
        ),
        "state": "formed",
    }


def measure_new_iteration(thing, index: int):
    """Time one full uc new pipeline (validation through write + evidence)."""
    if not is_thing(thing) or not isinstance(thing.get("value"), dict):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("measure_new:rejected",),
            "state": "invalid",
        }

    value = thing["value"]
    parent = value["parent"]
    name = f"n{index:04d}"
    # Preserve clock_feed across the measurement carrier.
    carrier = {
        **thing,
        "value": {
            **value,
            "measure_op": "new",
            "measure_index": index,
            "project_name": name,
        },
        "evidence": thing["evidence"],
        "state": "formed",
    }
    started = clock_start(carrier)
    if started["state"] in {"unknown", "absent", "false", "invalid"}:
        return {
            **started,
            "evidence": (*started["evidence"], "measure_new:clock-failed"),
        }

    generated = run_command(
        inward(
            {
                "command": "new",
                "name": name,
                "parent": parent,
            }
        )
    )
    # Re-attach generation result onto the clock carrier (clock fields in value).
    carrier_value = started["value"]
    if not isinstance(carrier_value, dict):
        carrier_value = {}
    mid = {
        **started,
        "value": {
            **carrier_value,
            "last_generation": {
                "state": generated.get("state"),
                "evidence": generated.get("evidence"),
                "project_path": _project_path(generated),
            },
        },
    }
    ended = clock_end(mid)
    duration = _duration_ns(ended)
    valid = generated.get("state") == "valid" and _structurally_complete_new(generated)
    samples = tuple(ended["value"].get("new_samples_ns", ())) if isinstance(ended.get("value"), dict) else ()
    valids = tuple(ended["value"].get("new_results_valid", ())) if isinstance(ended.get("value"), dict) else ()
    failures = tuple(ended["value"].get("failures", ())) if isinstance(ended.get("value"), dict) else ()

    if duration is None:
        failures = (*failures, f"new[{index}]:missing-duration")
    else:
        samples = (*samples, duration)
    valids = (*valids, valid)
    if not valid:
        failures = (*failures, f"new[{index}]:invalid-or-incomplete")

    new_value = ended["value"] if isinstance(ended["value"], dict) else {}
    return {
        **ended,
        "value": {
            **new_value,
            "new_samples_ns": samples,
            "new_results_valid": valids,
            "failures": failures,
            # keep clock_feed if present
        },
        "evidence": (
            *ended["evidence"],
            f"measure_new:{index}:{'ok' if valid and duration is not None else 'fail'}",
        ),
        "state": "formed",
    }


def measure_add_iteration(thing, index: int):
    """Time one full uc add pipeline against the project created for this index."""
    if not is_thing(thing) or not isinstance(thing.get("value"), dict):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("measure_add:rejected",),
            "state": "invalid",
        }

    value = thing["value"]
    parent = value["parent"]
    project_path = str(Path(parent) / f"n{index:04d}")
    feature = f"f{index:04d}"

    carrier = {
        **thing,
        "value": {
            **value,
            "measure_op": "add",
            "measure_index": index,
            "feature_name": feature,
        },
        "evidence": thing["evidence"],
        "state": "formed",
    }
    started = clock_start(carrier)
    if started["state"] in {"unknown", "absent", "false", "invalid"}:
        return {
            **started,
            "evidence": (*started["evidence"], "measure_add:clock-failed"),
        }

    generated = run_command(
        inward(
            {
                "command": "add",
                "name": feature,
                "project_root": project_path,
            }
        )
    )
    carrier_value = started["value"] if isinstance(started["value"], dict) else {}
    mid = {
        **started,
        "value": {
            **carrier_value,
            "last_generation": {
                "state": generated.get("state"),
                "evidence": generated.get("evidence"),
                "project_path": project_path,
            },
        },
    }
    ended = clock_end(mid)
    duration = _duration_ns(ended)
    valid = generated.get("state") == "valid" and _structurally_complete_add(generated, feature)
    samples = tuple(ended["value"].get("add_samples_ns", ())) if isinstance(ended.get("value"), dict) else ()
    valids = tuple(ended["value"].get("add_results_valid", ())) if isinstance(ended.get("value"), dict) else ()
    failures = tuple(ended["value"].get("failures", ())) if isinstance(ended.get("value"), dict) else ()

    if duration is None:
        failures = (*failures, f"add[{index}]:missing-duration")
    else:
        samples = (*samples, duration)
    valids = (*valids, valid)
    if not valid:
        failures = (*failures, f"add[{index}]:invalid-or-incomplete")

    new_value = ended["value"] if isinstance(ended["value"], dict) else {}
    return {
        **ended,
        "value": {
            **new_value,
            "add_samples_ns": samples,
            "add_results_valid": valids,
            "failures": failures,
        },
        "evidence": (
            *ended["evidence"],
            f"measure_add:{index}:{'ok' if valid and duration is not None else 'fail'}",
        ),
        "state": "formed",
    }


def evaluate_l9(thing):
    """Compute per-operation stats and overall L9 verdict."""
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("evaluate_l9:rejected-non-thing",),
            "state": "invalid",
        }
    if thing["state"] in {"absent", "false"}:
        return {
            **thing,
            "evidence": (*thing["evidence"], "evaluate_l9:not-run"),
            "state": thing["state"],
        }

    value = thing["value"]
    if not isinstance(value, dict):
        return {
            **thing,
            "evidence": (*thing["evidence"], "evaluate_l9:value-not-map"),
            "state": "invalid",
        }

    new_samples = tuple(value.get("new_samples_ns") or ())
    add_samples = tuple(value.get("add_samples_ns") or ())
    new_valids = tuple(value.get("new_results_valid") or ())
    add_valids = tuple(value.get("add_results_valid") or ())
    failures = tuple(value.get("failures") or ())

    if not new_samples or not add_samples:
        return {
            **thing,
            "value": {
                **value,
                "new": None,
                "add": None,
                "l9_verdict": "fail",
            },
            "evidence": (*thing["evidence"], "evaluate_l9:missing-samples"),
            "state": "invalid",
        }

    new_report = _stats(new_samples)
    add_report = _stats(add_samples)

    all_valid = all(new_valids) and all(add_valids) and len(new_valids) == len(new_samples) and len(add_valids) == len(add_samples)
    if not all_valid:
        failures = (*failures, "evaluate_l9:invalid-generation")
        new_report = {**new_report, "verdict": "fail"}
        add_report = {**add_report, "verdict": "fail"}

    # Individual operation verdict already set by p95; overall requires both + validity.
    if new_report["p95_ns"] > LIMIT_NS:
        new_report = {**new_report, "verdict": "fail"}
    if add_report["p95_ns"] > LIMIT_NS:
        add_report = {**add_report, "verdict": "fail"}

    l9_pass = (
        new_report["verdict"] == "pass"
        and add_report["verdict"] == "pass"
        and all_valid
    )

    return {
        **thing,
        "value": {
            **value,
            "new": new_report,
            "add": add_report,
            "l9_verdict": "pass" if l9_pass else "fail",
            "failures": failures,
            "all_generations_valid": all_valid,
        },
        "evidence": (
            *thing["evidence"],
            f"evaluate_l9:new_p95:{new_report['p95_ns']}",
            f"evaluate_l9:add_p95:{add_report['p95_ns']}",
            f"evaluate_l9:{'pass' if l9_pass else 'fail'}",
        ),
        "state": "valid" if l9_pass else "invalid",
    }


def cleanup_benchmark(thing):
    """Remove only temporary directories owned by this benchmark run."""
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("cleanup_benchmark:rejected-non-thing",),
            "state": "invalid",
        }

    value = thing["value"] if isinstance(thing.get("value"), dict) else {}
    removed = []
    if value.get("owned_temp"):
        for root in value.get("temp_roots") or ():
            path = Path(root)
            if path.is_dir() and path.name.startswith("uc-benchmark-"):
                shutil.rmtree(path, ignore_errors=True)
                removed.append(str(path))

    # Never touch the real repository; only report marker.
    return {
        **thing,
        "value": {
            **value,
            "removed_temp_roots": tuple(removed),
            # Drop bulky file maps if any leaked
            "files": None,
        },
        "evidence": (
            *thing["evidence"],
            "cleanup_benchmark:done",
            f"cleanup:removed:{len(removed)}",
        ),
        # Preserve evaluate_l9 state (valid/invalid).
        "state": thing["state"],
    }


def run_benchmark(thing):
    """Full benchmark pipeline. One thing in, one thing out."""
    return outward(
        cleanup_benchmark(
            evaluate_l9(
                measure_all(
                    prepare_benchmark(
                        validate_benchmark(thing)
                    )
                )
            )
        )
    )


def _warmup(thing):
    value = thing["value"]
    parent = value["parent"]
    name = "warmup"
    generated = run_command(
        inward({"command": "new", "name": name, "parent": parent})
    )
    if generated.get("state") != "valid":
        return {
            **thing,
            "value": {
                **value,
                "failures": (*value.get("failures", ()), "warmup:new-failed"),
            },
            "evidence": (*thing["evidence"], "warmup:new-failed"),
            "state": "invalid",
        }
    project = Path(parent) / name
    added = run_command(
        inward(
            {
                "command": "add",
                "name": "warmfeat",
                "project_root": str(project),
            }
        )
    )
    if added.get("state") != "valid":
        return {
            **thing,
            "value": {
                **value,
                "failures": (*value.get("failures", ()), "warmup:add-failed"),
            },
            "evidence": (*thing["evidence"], "warmup:add-failed"),
            "state": "invalid",
        }
    # Remove warmup project only; keep parent.
    shutil.rmtree(project, ignore_errors=True)
    return {
        **thing,
        "evidence": (*thing["evidence"], "warmup:done"),
        "state": "formed",
    }


def _stats(samples_ns: tuple[int, ...]) -> dict:
    ordered = tuple(sorted(int(x) for x in samples_ns))
    n = len(ordered)
    if n == 0:
        return {
            "iterations": 0,
            "minimum_ns": None,
            "median_ns": None,
            "p95_ns": None,
            "maximum_ns": None,
            "limit_ns": LIMIT_NS,
            "verdict": "fail",
        }
    if n % 2 == 1:
        median = ordered[n // 2]
    else:
        median = (ordered[n // 2 - 1] + ordered[n // 2]) // 2
    p95_index = max(0, math.ceil(0.95 * n) - 1)
    p95 = ordered[p95_index]
    return {
        "iterations": n,
        "minimum_ns": ordered[0],
        "median_ns": median,
        "p95_ns": p95,
        "maximum_ns": ordered[-1],
        "limit_ns": LIMIT_NS,
        "verdict": "pass" if p95 <= LIMIT_NS else "fail",
    }


def _duration_ns(thing) -> int | None:
    value = thing.get("value")
    if not isinstance(value, dict):
        return None
    clock = value.get("clock")
    if not isinstance(clock, dict):
        return None
    duration = clock.get("duration_ns")
    if not isinstance(duration, int) or isinstance(duration, bool):
        return None
    return duration


def _project_path(generated) -> str | None:
    value = generated.get("value")
    if isinstance(value, dict):
        path = value.get("project_path")
        if isinstance(path, str):
            return path
    return None


def _structurally_complete_new(generated) -> bool:
    path = _project_path(generated)
    if not path:
        return False
    root = Path(path)
    if not root.is_dir():
        return False
    for rel in REQUIRED_NEW_RELATIVE:
        if not (root / rel).is_file():
            return False
    value = generated.get("value")
    if not isinstance(value, dict):
        return False
    package = value.get("package")
    if not isinstance(package, str):
        return False
    for rel in (
        f"{package}/compose.py",
        f"{package}/parts.py",
        f"{package}/features.py",
        f"{package}/boundary.py",
        f"{package}/core.py",
        "tests/test_program.py",
        "tests/test_signature.py",
    ):
        if not (root / rel).is_file():
            return False
    return True


def _structurally_complete_add(generated, feature: str) -> bool:
    value = generated.get("value")
    if not isinstance(value, dict):
        return False
    if generated.get("state") != "valid":
        return False
    features = value.get("features")
    if not isinstance(features, tuple) or feature not in features:
        return False
    path = value.get("project_path")
    package = value.get("package")
    if not isinstance(path, str) or not isinstance(package, str):
        return False
    parts = Path(path) / package / "parts.py"
    if not parts.is_file():
        return False
    text = parts.read_text(encoding="utf-8")
    return f"def {feature}(" in text


def _hard_stop(thing) -> bool:
    """Stop only on clock-boundary hard failures, not generation fails."""
    evidence = thing.get("evidence") or ()
    return any(
        item.startswith("measure_new:clock-failed") or item.startswith("measure_add:clock-failed")
        for item in evidence
    )


def host_benchmark_main(argv=None):
    """Process entry for ``python -m unified.generator.benchmark``."""
    import sys

    from ..boundary import host_render

    explicit = argv is not None
    raw = list(sys.argv[1:] if argv is None else argv)
    iterations = 20
    i = 0
    while i < len(raw):
        if raw[i] == "--iterations" and i + 1 < len(raw):
            try:
                iterations = int(raw[i + 1])
            except ValueError:
                iterations = -1
            i += 2
            continue
        i += 1
    result = run_benchmark(inward({"command": "benchmark", "iterations": iterations}))
    sys.stdout.write(host_render(result))
    sys.stdout.write("\n")
    code = 0 if result.get("state") == "valid" else 1
    if isinstance(result.get("value"), dict):
        value = result["value"]
        new = value.get("new") or {}
        add = value.get("add") or {}
        sys.stderr.write(
            f"L9 {value.get('l9_verdict', 'fail').upper()}: "
            f"new p95={new.get('p95_ns')} ns, add p95={add.get('p95_ns')} ns, "
            f"limit={LIMIT_NS} ns\n"
        )
    if explicit:
        return code
    raise SystemExit(code)


if __name__ == "__main__":
    host_benchmark_main()
