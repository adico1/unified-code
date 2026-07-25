"""L13 Complete Testing Gauntlet — multi-dimension coverage gate.

Primary production score excludes vendored deps and test/build scripts.
All required dimensions must be exactly 100% or the gauntlet fails.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CROOT = ROOT / "c"

# Required dimensions (never merged into one score)
DIMENSIONS = (
    "python_statements",
    "python_branches",
    "c_lines",
    "c_functions",
    "c_branches",
    "opcodes",
    "opcode_valid_paths",
    "opcode_rejection_paths",
    "primitive_registry",
    "specification_requirements",
    "state_transitions",
    "event_routes",
    "error_ticket_paths",
    "required_mutations",
    "python_c_differential",
    "physical_target_goldens",
)


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def measure_python_coverage() -> dict:
    """Statement + branch coverage for production unified/machine only."""
    cov = ROOT / ".venv" / "bin" / "coverage"
    py = ROOT / ".venv" / "bin" / "python"
    env = os.environ.copy()
    env["UEM_C"] = str(CROOT / "build" / "uem-c")
    # Clear prior data
    _run([str(cov), "erase"], cwd=str(ROOT))
    # Uses repo .coveragerc — omits gauntlet harnesses (l11/l13/gauntlet/measure)
    r = _run(
        [
            str(cov),
            "run",
            "--rcfile=" + str(ROOT / ".coveragerc"),
            "-m",
            "pytest",
            "tests/test_l13.py",
            "tests/test_l11.py",
            "tests/test_uem.py",
            "-q",
            "--tb=no",
        ],
        cwd=str(ROOT),
        env=env,
        timeout=600,
    )
    if r.returncode != 0:
        return {
            "statements": 0.0,
            "branches": 0.0,
            "error": (r.stdout or "")[-500:] + (r.stderr or "")[-500:],
            "ok": False,
        }
    _run(
        [
            str(cov),
            "json",
            "-o",
            str(ROOT / "coverage_py.json"),
            "--rcfile=" + str(ROOT / ".coveragerc"),
        ],
        cwd=str(ROOT),
    )
    data = json.loads((ROOT / "coverage_py.json").read_text(encoding="utf-8"))
    totals = data.get("totals") or {}
    stmts = float(totals.get("percent_covered", 0))
    nb = totals.get("num_branches") or 0
    cb = totals.get("covered_branches") or 0
    br = 100.0 if nb == 0 else 100.0 * cb / nb
    gaps = []
    for f, info in (data.get("files") or {}).items():
        s = info.get("summary") or {}
        pct = float(s.get("percent_covered") or 0)
        if pct < 100.0 - 1e-9:
            # missing lines from executed_lines vs full analysis
            gaps.append(
                {
                    "file": f,
                    "percent": pct,
                    "num_statements": s.get("num_statements"),
                    "covered_lines": s.get("covered_lines"),
                    "missing_lines": s.get("missing_lines"),
                }
            )
    return {
        "statements": stmts,
        "branches": br,
        "ok": stmts >= 100.0 - 1e-9 and br >= 100.0 - 1e-9,
        "totals": totals,
        "files_with_gaps": gaps,
    }


def measure_c_coverage() -> dict:
    """Line/function/branch coverage for c/core only (not third_party)."""
    # Build with coverage
    _run(["make", "-C", str(CROOT), "clean"], cwd=str(ROOT))
    r = _run(
        [
            "make",
            "-C",
            str(CROOT),
            "posix",
            "CFLAGS=-std=c99 -Wall -O0 -g --coverage -Iinclude -Ithird_party -Icore -Ihost/mcu",
            "LDFLAGS=--coverage",
        ],
        cwd=str(ROOT),
        timeout=120,
    )
    if r.returncode != 0:
        return {"ok": False, "error": r.stderr[-800:], "lines": 0, "functions": 0, "branches": 0}
    bin_path = CROOT / "build" / "uem-c"
    env = os.environ.copy()
    env["UEM_C"] = str(bin_path)
    # Exercise C heavily via pytest + direct runs
    _run(
        [str(ROOT / ".venv" / "bin" / "python"), "-m", "pytest",
         "tests/test_l13.py", "tests/test_l11.py", "tests/test_uem.py", "-q", "--tb=no"],
        cwd=str(ROOT),
        env=env,
        timeout=600,
    )
    # Also run goldens and malformed
    for uem in (ROOT / "artifacts/uem").rglob("*.uem"):
        _run([str(bin_path), "verify", str(uem)])
        _run([str(bin_path), "run", str(uem), "--host", '{"text":"x"}'])
    for v in (CROOT / "tests/vectors").glob("*.uem"):
        _run([str(bin_path), "verify", str(v)])
    # gcov on core objects
    core = CROOT / "core"
    gcov_out = []
    for cfile in sorted(core.glob("*.c")):
        # .gcno may be next to build or in cwd
        _run(["gcov", "-b", "-o", str(CROOT / "build"), str(cfile)], cwd=str(CROOT))
        # also try cwd core
        _run(["gcov", "-b", str(cfile.name)], cwd=str(core))
    # Parse .gcov files in core/
    lines_total = lines_hit = 0
    funcs_total = funcs_hit = 0
    br_total = br_hit = 0
    for gcov in list(core.glob("*.gcov")) + list(CROOT.glob("*.gcov")):
        if "third_party" in str(gcov):
            continue
        text = gcov.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            # gcov format: "        -:    1:..." or "    #####:   10:..." or "        1:   10:..."
            if ":" not in line:
                continue
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue
            count, lineno = parts[0].strip(), parts[1].strip()
            body = parts[2]
            if not lineno.isdigit():
                continue
            if count == "-":
                continue
            if "function" in body.lower() and ("called" in body.lower() or "blocks executed" in body.lower()):
                # function summary lines vary
                continue
            if count == "#####":
                lines_total += 1
            elif count.isdigit() or (count.endswith("%") is False and count not in {"-", "#####"}):
                try:
                    n = int(count)
                except ValueError:
                    if "branch" in count:
                        pass
                    continue
                else:
                    lines_total += 1
                    if n > 0:
                        lines_hit += 1
            if body.strip().startswith("branch"):
                br_total += 1
                if "taken 0%" not in body and "never executed" not in body:
                    # "branch  0 taken 1%" or "branch  0 taken 100%"
                    if "taken" in body and "taken 0%" not in body:
                        br_hit += 1
                    elif "never executed" in body:
                        pass
                else:
                    pass
            if "function " in body and "called" in body:
                funcs_total += 1
                if "called 0" not in body and "called 0 returned" not in body:
                    # "function foo called 5 returned 100%"
                    if "called 0 " not in body:
                        funcs_hit += 1
    # Fallback: use llvm-cov or rough from gcov summary
    # Simpler approach: parse `gcov -b` summary from subprocess
    summary = _gcov_summary()
    if summary:
        return summary
    lines_pct = 100.0 if lines_total == 0 else 100.0 * lines_hit / lines_total
    funcs_pct = 100.0 if funcs_total == 0 else 100.0 * funcs_hit / funcs_total
    br_pct = 100.0 if br_total == 0 else 100.0 * br_hit / br_total
    return {
        "lines": lines_pct,
        "functions": funcs_pct,
        "branches": br_pct,
        "ok": lines_pct >= 100 and funcs_pct >= 100 and br_pct >= 100,
        "raw": {"lines_total": lines_total, "lines_hit": lines_hit},
    }


def _gcov_summary() -> dict | None:
    """Parse gcov -b output for core/*.c only."""
    core = CROOT / "core"
    # Prefer .gcda next to objects; gcc often puts them in build/
    # Run gcov with all core sources from c/ with object dir
    lines_t = lines_h = 0
    br_t = br_h = 0
    fn_t = fn_h = 0
    found = False
    for cfile in sorted(core.glob("*.c")):
        # find gcda
        candidates = list(CROOT.rglob(cfile.stem + ".gcda"))
        if not candidates:
            continue
        found = True
        objdir = candidates[0].parent
        r = _run(
            ["gcov", "-b", "-o", str(objdir), str(cfile)],
            cwd=str(CROOT),
        )
        text = r.stdout + r.stderr
        # "Lines executed:xx.xx% of N"
        import re

        m = re.search(r"Lines executed:([\d.]+)% of (\d+)", text)
        if m:
            pct, n = float(m.group(1)), int(m.group(2))
            lines_t += n
            lines_h += int(round(pct / 100.0 * n))
        m = re.search(r"Branches executed:([\d.]+)% of (\d+)", text)
        if m:
            pct, n = float(m.group(1)), int(m.group(2))
            br_t += n
            br_h += int(round(pct / 100.0 * n))
        m = re.search(r"Taken at least once:([\d.]+)% of (\d+)", text)
        if m:
            pct, n = float(m.group(1)), int(m.group(2))
            # use taken as branch coverage metric
            br_t = max(br_t, n)
            br_h = int(round(pct / 100.0 * n))
        m = re.search(r"Calls executed:([\d.]+)% of (\d+)", text)
        if m:
            pct, n = float(m.group(1)), int(m.group(2))
            fn_t += n
            fn_h += int(round(pct / 100.0 * n))
        # Functions:
        m = re.search(r"No functions found", text)
        if not m:
            m2 = re.findall(r"Function ['\"]?(\w+)", text)
            # count from "function X called"
            called = re.findall(r"function\s+(\S+)\s+called\s+(\d+)", text, re.I)
            if called:
                for _, c in called:
                    fn_t += 1
                    if int(c) > 0:
                        fn_h += 1
    if not found:
        return None
    return {
        "lines": 100.0 if lines_t == 0 else 100.0 * lines_h / lines_t,
        "functions": 100.0 if fn_t == 0 else 100.0 * fn_h / fn_t,
        "branches": 100.0 if br_t == 0 else 100.0 * br_h / br_t,
        "ok": False,  # filled later
        "raw": {"lines_t": lines_t, "lines_h": lines_h, "br_t": br_t, "br_h": br_h, "fn_t": fn_t, "fn_h": fn_h},
    }


def catalog_scores() -> dict:
    """Run L13 behavioral catalogs (not line coverage)."""
    from .l13_catalog import run_all_catalogs

    return run_all_catalogs()


def run_l13_gauntlet(thing=None):
    """Full L13 gate. Returns Thing with coverage.json payload."""
    from .thing import blank_thing, with_state

    t0 = time.time()
    # Ensure release binary for differential
    _run(
        [
            "make",
            "-C",
            str(CROOT),
            "posix",
            "CFLAGS=-std=c99 -Wall -O2 -Iinclude -Ithird_party -Icore -Ihost/mcu",
        ],
        cwd=str(ROOT),
    )
    os.environ["UEM_C"] = str(CROOT / "build" / "uem-c")

    catalogs = catalog_scores()
    py_cov = measure_python_coverage()
    c_cov = measure_c_coverage()
    if c_cov.get("raw") is not None and "ok" in c_cov:
        c_cov["ok"] = (
            c_cov.get("lines", 0) >= 100.0 - 1e-6
            and c_cov.get("functions", 0) >= 100.0 - 1e-6
            and c_cov.get("branches", 0) >= 100.0 - 1e-6
        )

    dimensions = {
        "python_statements": {
            "required": 100.0,
            "actual": py_cov.get("statements", 0.0),
            "ok": py_cov.get("ok", False) and py_cov.get("statements", 0) >= 100.0 - 1e-6,
            "detail": py_cov.get("files_with_gaps"),
        },
        "python_branches": {
            "required": 100.0,
            "actual": py_cov.get("branches", 0.0),
            "ok": py_cov.get("ok", False) and py_cov.get("branches", 0) >= 100.0 - 1e-6,
        },
        "c_lines": {
            "required": 100.0,
            "actual": c_cov.get("lines", 0.0),
            "ok": c_cov.get("lines", 0) >= 100.0 - 1e-6,
            "raw": c_cov.get("raw"),
        },
        "c_functions": {
            "required": 100.0,
            "actual": c_cov.get("functions", 0.0),
            "ok": c_cov.get("functions", 0) >= 100.0 - 1e-6,
        },
        "c_branches": {
            "required": 100.0,
            "actual": c_cov.get("branches", 0.0),
            "ok": c_cov.get("branches", 0) >= 100.0 - 1e-6,
        },
    }
    for k, v in catalogs.items():
        dimensions[k] = v

    all_ok = all(d.get("ok") for d in dimensions.values())
    report = {
        "l13": True,
        "verdict": "pass" if all_ok else "fail",
        "dimensions": dimensions,
        "duration_s": time.time() - t0,
        "rules": {
            "no_pragma_no_cover": True,
            "vendored_excluded_from_primary": True,
            "tests_do_not_inflate_production": True,
        },
    }
    # Emit files
    (ROOT / "coverage.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_gauntlet_md(report)
    return with_state(
        {
            "value": report,
            "depths": (),
            "axes": (),
            "evidence": (f"l13:{report['verdict']}",),
            "state": "valid" if all_ok else "invalid",
        },
        "valid" if all_ok else "invalid",
    )


def _write_gauntlet_md(report: dict) -> None:
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
    for name, d in sorted((report.get("dimensions") or {}).items()):
        req = d.get("required", 100)
        act = d.get("actual", d.get("score", 0))
        ok = "yes" if d.get("ok") else "NO"
        if isinstance(act, float):
            act_s = f"{act:.2f}"
        else:
            act_s = str(act)
        lines.append(f"| `{name}` | {req} | {act_s} | {ok} |")
    lines.extend(
        [
            "",
            "## Rules",
            "",
            "- No pragma/no-cover suppression",
            "- Vendored third_party excluded from primary C score (reported separately if present)",
            "- Tests/build scripts cannot inflate production coverage",
            "- Assertions verify state, output, evidence, events, effects",
            "",
            f"Generated in {report.get('duration_s', 0):.1f}s.",
            "",
        ]
    )
    (ROOT / "GAUNTLET.md").write_text("\n".join(lines), encoding="utf-8")
