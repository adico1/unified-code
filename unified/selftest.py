"""Dependency-free deterministic test runner for Unified Code.

Tests are plain functions with plain ``assert`` statements.  This module owns
the small amount of discovery, parametrization and temporary-boundary support
that the repository actually uses; no third-party test framework is required.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import importlib
import importlib.util
import inspect
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.modules.setdefault("unified.selftest", sys.modules[__name__])

PROFILE_PATH = (
    Path(__file__).resolve().parents[1]
    / "seed"
    / "verification"
    / "TEST_PROFILES.json"
)


@contextlib.contextmanager
def raises(expected, match=None):
    observed = SimpleNamespace(value=None)
    try:
        yield observed
    except expected as error:
        observed.value = error
        if match is not None and re.search(match, str(error)) is None:
            raise AssertionError(f"exception {error!r} does not match {match!r}")
    else:
        raise AssertionError(f"did not raise {expected}")


def skip(reason):
    raise unittest.SkipTest(reason)


def _parametrize(names, values, ids=None):
    del ids
    fields = (
        tuple(item.strip() for item in names.split(","))
        if isinstance(names, str)
        else tuple(names)
    )

    def decorate(function):
        existing = tuple(getattr(function, "__selftest_cases__", ({},)))
        additions = []
        for value in values:
            row = value if len(fields) > 1 else (value,)
            if len(row) != len(fields):
                raise ValueError("selftest:parametrize-arity")
            additions.append(dict(zip(fields, row)))
        function.__selftest_cases__ = tuple(
            {**base, **addition}
            for base in existing
            for addition in additions
        )
        return function

    return decorate


def _skipif(condition, reason):
    def decorate(function):
        function.__selftest_skip__ = reason if condition else None
        return function

    return decorate


mark = SimpleNamespace(parametrize=_parametrize, skipif=_skipif)


def _monkeypatch():
    undo_stack = []

    def patch_attribute(target, name, value=...):
        if value is ...:
            dotted, value = target, name
            module_name, attribute_path = dotted.split(".", 1)
            target = importlib.import_module(module_name)
            parts = attribute_path.split(".")
            for part in parts[:-1]:
                target = getattr(target, part)
            name = parts[-1]
        existed = hasattr(target, name)
        previous = getattr(target, name, None)
        setattr(target, name, value)
        undo_stack.append(
            lambda: setattr(target, name, previous)
            if existed
            else delattr(target, name)
        )

    def patch_item(mapping, name, value):
        existed = name in mapping
        previous = mapping.get(name)
        mapping[name] = value
        undo_stack.append(
            lambda: mapping.__setitem__(name, previous)
            if existed
            else mapping.__delitem__(name)
        )

    def patch_environment(name, value):
        patch_item(os.environ, name, str(value))

    def delete_environment(name, raising=True):
        if name not in os.environ:
            if raising:
                raise KeyError(name)
            return
        previous = os.environ.pop(name)
        undo_stack.append(lambda: os.environ.__setitem__(name, previous))

    def change_directory(path):
        previous = Path.cwd()
        os.chdir(path)
        undo_stack.append(lambda: os.chdir(previous))

    def undo():
        for operation in reversed(undo_stack):
            operation()
        undo_stack.clear()

    return SimpleNamespace(
        setattr=patch_attribute,
        setitem=patch_item,
        setenv=patch_environment,
        delenv=delete_environment,
        chdir=change_directory,
        undo=undo,
    )


def _capture(output, errors):
    positions = [0, 0]

    def readouterr():
        out = output.getvalue()[positions[0] :]
        err = errors.getvalue()[positions[1] :]
        positions[:] = (len(output.getvalue()), len(errors.getvalue()))
        return SimpleNamespace(out=out, err=err)

    return SimpleNamespace(readouterr=readouterr)


def _load(path, ordinal):
    name = f"uc_selftest_{ordinal}_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _profile():
    declaration = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    if declaration.get("format_version") != "UC-TEST-PROFILES-1":
        raise ValueError("selftest:profile-version")
    return declaration


def _files(arguments, profile=None):
    roots = arguments or ("tests",)
    discovered = []
    for raw in roots:
        path = Path(raw)
        discovered.extend(
            sorted(path.glob("test_*.py")) if path.is_dir() else (path,)
        )
    files = tuple(dict.fromkeys(item.resolve() for item in discovered))
    declaration = _profile()
    selected = profile or os.environ.get(
        "UC_SELFTEST_PROFILE", declaration["default_profile"]
    )
    profiles = declaration.get("profiles") or {}
    if selected not in profiles:
        raise ValueError("selftest:unknown-profile")
    excluded = set(profiles[selected].get("exclude_files") or ())
    return tuple(path for path in files if path.name not in excluded), selected


def _functions(module):
    return tuple(
        value
        for _name, value in sorted(
            inspect.getmembers(module, inspect.isfunction),
            key=lambda item: item[1].__code__.co_firstlineno,
        )
        if value.__name__.startswith("test_") and value.__module__ == module.__name__
    )


def _invoke(function, parameters, temporary):
    patch = _monkeypatch()
    output = io.StringIO()
    errors = io.StringIO()
    fixtures = {
        "tmp_path": temporary,
        "monkeypatch": patch,
        "capsys": _capture(output, errors),
    }
    unknown = set(inspect.signature(function).parameters) - set(parameters) - set(fixtures)
    if unknown:
        raise ValueError(f"selftest:unknown-fixtures:{','.join(sorted(unknown))}")
    arguments = {
        name: parameters.get(name, fixtures.get(name))
        for name in inspect.signature(function).parameters
    }
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            function(**arguments)
    finally:
        patch.undo()


def _local_report(paths, profile):
    started = time.monotonic_ns()
    results = []
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    with tempfile.TemporaryDirectory(prefix="uc-selftest-") as owner:
        owner_path = Path(owner).resolve()
        for ordinal, path in enumerate(paths):
            module = _load(path, ordinal)
            for function in _functions(module):
                cases = tuple(getattr(function, "__selftest_cases__", ({},)))
                for case_index, parameters in enumerate(cases):
                    identity = f"{path.name}::{function.__name__}[{case_index}]"
                    test_root = owner_path / str(len(results))
                    test_root.mkdir()
                    try:
                        reason = getattr(function, "__selftest_skip__", None)
                        if reason:
                            raise unittest.SkipTest(reason)
                        _invoke(function, parameters, test_root)
                    except unittest.SkipTest as error:
                        results.append({"id": identity, "status": "skip", "error": str(error)})
                    except BaseException as error:
                        results.append(
                            {
                                "id": identity,
                                "status": "fail",
                                "error": f"{type(error).__name__}:{error}",
                            }
                        )
                    else:
                        results.append({"id": identity, "status": "pass", "error": None})
    failures = [item for item in results if item["status"] == "fail"]
    return {
        "passed": sum(item["status"] == "pass" for item in results),
        "skipped": sum(item["status"] == "skip" for item in results),
        "failed": len(failures),
        "total": len(results),
        "duration_ns": time.monotonic_ns() - started,
        "profile": profile,
        "files": len(paths),
        "failures": failures,
        "results": results,
        "ok": not failures,
    }


def _run_shard_boundary(item):
    ordinal, paths, profile = item
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            "--profile",
            profile,
            *(str(path) for path in paths),
        ],
        cwd=str(Path.cwd()),
        capture_output=True,
        text=True,
        check=False,
    )
    lines = completed.stdout.splitlines()
    try:
        report = json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError):
        detail = (completed.stderr or completed.stdout or "no-report").strip()
        identity = f"shard-{ordinal}::worker[0]"
        report = {
            "passed": 0,
            "skipped": 0,
            "failed": 1,
            "total": 1,
            "duration_ns": 0,
            "failures": [
                {"id": identity, "status": "fail", "error": f"worker:{detail}"}
            ],
            "results": [],
            "ok": False,
        }
    return ordinal, report


def _parallel_reports(files, workers, profile):
    batches = tuple(
        tuple(files[index::workers])
        for index in range(workers)
        if files[index::workers]
    )
    indexed = tuple(
        (ordinal, paths, profile)
        for ordinal, paths in enumerate(batches)
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        completed = executor.map(_run_shard_boundary, indexed)
        return tuple(report for _ordinal, report in completed)


def _worker_count(requested, file_count):
    configured = requested if requested is not None else os.environ.get(
        "UC_SELFTEST_WORKERS", "4"
    )
    try:
        workers = int(configured)
    except (TypeError, ValueError) as error:
        raise ValueError("selftest:invalid-workers") from error
    if workers < 1:
        raise ValueError("selftest:invalid-workers")
    return max(1, min(workers, max(1, file_count)))


def run(paths=(), workers=None, profile=None):
    started = time.monotonic_ns()
    files, selected_profile = _files(paths, profile)
    worker_count = _worker_count(workers, len(files))
    reports = (
        (_local_report(files, selected_profile),)
        if worker_count == 1
        else _parallel_reports(files, worker_count, selected_profile)
    )
    failures = [
        failure
        for report in reports
        for failure in report["failures"]
    ]
    return {
        "format": "uc-selftest-1",
        "passed": sum(report["passed"] for report in reports),
        "skipped": sum(report["skipped"] for report in reports),
        "failed": sum(report["failed"] for report in reports),
        "total": sum(report["total"] for report in reports),
        "duration_ns": time.monotonic_ns() - started,
        "profile": selected_profile,
        "files": len(files),
        "workers": worker_count,
        "failures": failures,
        "ok": not failures,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m unified.selftest")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--profile")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("paths", nargs="*")
    arguments = parser.parse_args(argv)
    files, selected_profile = _files(arguments.paths, arguments.profile)
    report = (
        _local_report(files, selected_profile)
        if arguments.worker
        else run(
            arguments.paths,
            workers=arguments.workers,
            profile=arguments.profile,
        )
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
