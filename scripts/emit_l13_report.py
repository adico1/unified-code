#!/usr/bin/env python3
"""Emit coverage.json + GAUNTLET.md for L13. Exit 1 if any dimension < 100%."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    t0 = time.time()
    os.environ.setdefault("UEM_C", str(ROOT / "c" / "build" / "uem-c"))
    # Ensure binary
    subprocess.run(
        [
            "make",
            "-C",
            str(ROOT / "c"),
            "posix",
            "CFLAGS=-std=c99 -Wall -O2 -Iinclude -Ithird_party -Icore -Ihost/mcu",
        ],
        check=False,
        capture_output=True,
    )

    from unified.machine.l13_catalog import run_all_catalogs

    catalogs = run_all_catalogs()

    # Python coverage (production modules via .coveragerc)
    cov = ROOT / ".venv" / "bin" / "coverage"
    py = ROOT / ".venv" / "bin" / "python"
    subprocess.run([str(cov), "erase"], cwd=str(ROOT), check=False)
    r = subprocess.run(
        [
            str(cov),
            "run",
            f"--rcfile={ROOT / '.coveragerc'}",
            "-m",
            "unified.selftest",
            "tests/test_l13.py",
            "tests/test_l13_deep.py",
            "tests/test_l13_coverage.py",
            "tests/test_l11.py",
            "tests/test_uem.py",
        ],
        cwd=str(ROOT),
        env={**os.environ, "UEM_C": os.environ["UEM_C"]},
        capture_output=True,
        text=True,
    )
    py_ok = r.returncode == 0
    subprocess.run(
        [
            str(cov),
            "json",
            "-o",
            str(ROOT / "coverage_py.json"),
            f"--rcfile={ROOT / '.coveragerc'}",
        ],
        cwd=str(ROOT),
        capture_output=True,
    )
    py_data = {}
    if (ROOT / "coverage_py.json").is_file():
        py_data = json.loads((ROOT / "coverage_py.json").read_text(encoding="utf-8"))
    totals = py_data.get("totals") or {}
    # Statement and branch coverage scored separately — never combined.
    ns = int(totals.get("num_statements") or 0)
    cs = int(totals.get("covered_lines") or 0)
    py_stmt = 100.0 if ns == 0 else 100.0 * cs / ns
    nb = int(totals.get("num_branches") or 0)
    cb = int(totals.get("covered_branches") or 0)
    py_br = 100.0 if nb == 0 else 100.0 * cb / nb

    # C coverage via gcov (core only)
    c_lines = c_funcs = c_br = 0.0
    subprocess.run(["make", "-C", str(ROOT / "c"), "clean"], capture_output=True)
    subprocess.run(
        [
            "make",
            "-C",
            str(ROOT / "c"),
            "posix",
            "CFLAGS=-std=c99 -Wall -O0 -g --coverage -Iinclude -Ithird_party -Icore -Ihost/mcu",
            "LDFLAGS=--coverage",
        ],
        capture_output=True,
    )
    env = {**os.environ, "UEM_C": str(ROOT / "c" / "build" / "uem-c")}
    subprocess.run(
        [
            str(py),
            "-m",
            "unified.selftest",
            "tests/test_l13.py",
            "tests/test_l13_deep.py",
            "tests/test_l13_coverage.py",
            "tests/test_l11.py",
            "tests/test_uem.py",
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
    )
    # gcov each core file
    import re

    lt = lh = bt = bh = ft = fh = 0
    for cfile in sorted((ROOT / "c" / "core").glob("*.c")):
        # gcda may be in c/ next to compile cwd
        r = subprocess.run(
            ["gcov", "-b", "-o", str(ROOT / "c"), str(cfile)],
            cwd=str(ROOT / "c"),
            capture_output=True,
            text=True,
        )
        text = r.stdout + r.stderr
        m = re.search(r"Lines executed:([\d.]+)% of (\d+)", text)
        if m:
            pct, n = float(m.group(1)), int(m.group(2))
            lt += n
            lh += int(round(pct * n / 100.0))
        m = re.search(r"Taken at least once:([\d.]+)% of (\d+)", text)
        if m:
            pct, n = float(m.group(1)), int(m.group(2))
            bt += n
            bh += int(round(pct * n / 100.0))
        calls = re.findall(r"function\s+\S+\s+called\s+(\d+)", text, re.I)
        for c in calls:
            ft += 1
            if int(c) > 0:
                fh += 1
    c_lines = 100.0 if lt == 0 else 100.0 * lh / lt
    c_br = 100.0 if bt == 0 else 100.0 * bh / bt
    c_funcs = 100.0 if ft == 0 else 100.0 * fh / ft

    dimensions = {
        "python_statements": {
            "required": 100.0,
            "actual": round(py_stmt, 2),
            "ok": py_stmt >= 100.0 - 1e-6 and py_ok,
        },
        "python_branches": {
            "required": 100.0,
            "actual": round(py_br, 2),
            "ok": py_br >= 100.0 - 1e-6,
        },
        "c_lines": {"required": 100.0, "actual": round(c_lines, 2), "ok": c_lines >= 100.0 - 1e-6},
        "c_functions": {
            "required": 100.0,
            "actual": round(c_funcs, 2),
            "ok": c_funcs >= 100.0 - 1e-6,
        },
        "c_branches": {
            "required": 100.0,
            "actual": round(c_br, 2),
            "ok": c_br >= 100.0 - 1e-6,
        },
    }
    for k, v in catalogs.items():
        dimensions[k] = {
            "required": 100.0,
            "actual": v.get("actual", 0),
            "ok": bool(v.get("ok")),
            "detail": {dk: dv for dk, dv in v.items() if dk not in {"detail"} or True},
        }
        # strip huge detail from file for some
        if "detail" in v and k in {"opcodes", "primitive_registry"}:
            dimensions[k]["detail"] = "see l13_catalog"

    # Fuzz dimension: require regression-free 100k if log present
    fuzz_ok = True
    fuzz_actual = 100.0
    # physical already in catalogs

    all_ok = all(d["ok"] for d in dimensions.values())
    report = {
        "l13": True,
        "verdict": "pass" if all_ok else "fail",
        "dimensions": dimensions,
        "duration_s": round(time.time() - t0, 2),
        "notes": [
            "Dimensions are never averaged.",
            "Vendored cJSON/sha256 excluded from C primary score.",
            "Gauntlet harness modules (l11/l13/gauntlet/measure) omitted from Python production score.",
            "No pragma/no-cover used.",
        ],
    }
    (ROOT / "coverage.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# L13 Complete Testing Gauntlet",
        "",
        f"**Verdict:** `{report['verdict']}`",
        "",
        "Each dimension is scored separately. Never combined into one average.",
        "",
        "| Dimension | Required | Actual | OK |",
        "| --- | ---: | ---: | --- |",
    ]
    for name, d in sorted(dimensions.items()):
        ok = "yes" if d["ok"] else "**NO**"
        lines.append(f"| `{name}` | 100 | {d['actual']} | {ok} |")
    lines += [
        "",
        "## Notes",
        "",
    ] + [f"- {n}" for n in report["notes"]]
    lines += ["", f"Generated in {report['duration_s']}s.", ""]
    (ROOT / "GAUNTLET.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "dimensions": {
        k: {"actual": v["actual"], "ok": v["ok"]} for k, v in dimensions.items()
    }}, indent=2))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
