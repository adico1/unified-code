"""Dependency-free deterministic test runner for Unified Code.

Tests are plain functions with plain ``assert`` statements.  This module owns
the small amount of discovery, parametrization and temporary-boundary support
that the repository actually uses; no third-party test framework is required.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import importlib.util
import inspect
import io
import json
import os
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.modules.setdefault("unified.selftest", sys.modules[__name__])


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


def _files(arguments):
    roots = arguments or ("tests",)
    discovered = []
    for raw in roots:
        path = Path(raw)
        discovered.extend(
            sorted(path.glob("test_*.py")) if path.is_dir() else (path,)
        )
    return tuple(dict.fromkeys(item.resolve() for item in discovered))


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


def run(paths=()):
    started = time.monotonic_ns()
    results = []
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    with tempfile.TemporaryDirectory(prefix="uc-selftest-") as owner:
        owner_path = Path(owner).resolve()
        for ordinal, path in enumerate(_files(paths)):
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
        "format": "uc-selftest-1",
        "passed": sum(item["status"] == "pass" for item in results),
        "skipped": sum(item["status"] == "skip" for item in results),
        "failed": len(failures),
        "total": len(results),
        "duration_ns": time.monotonic_ns() - started,
        "failures": failures,
        "ok": not failures,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m unified.selftest")
    parser.add_argument("paths", nargs="*")
    arguments = parser.parse_args(argv)
    report = run(arguments.paths)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
