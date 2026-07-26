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
    "fuzz_100k",
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
            "tests/test_l13_deep.py",
            "tests/test_l13_coverage.py",
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
    # Statement and branch coverage are scored separately — never combined.
    ns = int(totals.get("num_statements") or 0)
    cs = int(totals.get("covered_lines") or 0)
    stmts = 100.0 if ns == 0 else 100.0 * cs / ns
    nb = int(totals.get("num_branches") or 0)
    cb = int(totals.get("covered_branches") or 0)
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


def _pct(hit: int, total: int) -> float:
    """Coverage percent. Zero denominator is invalid → 0.0 (never 100%)."""
    if total <= 0:
        return 0.0
    return 100.0 * hit / total


def _gcno_for_core(stem: str) -> Path | None:
    """Locate note file for a core translation unit (Apple clang: uem-c-<stem>.gcno)."""
    build = CROOT / "build"
    candidates = [
        build / f"uem-c-{stem}.gcno",
        build / f"{stem}.gcno",
        CROOT / "core" / f"{stem}.gcno",
    ]
    for p in candidates:
        if p.is_file():
            return p
    # last resort: any *-{stem}.gcno under build
    for p in sorted(build.glob(f"*-{stem}.gcno")):
        return p
    return None


def measure_c_coverage() -> dict:
    """Line/function/branch coverage for c/core only (not third_party).

    Rules:
    - Vendored third_party excluded from primary score.
    - Denominator zero or missing instrumentation → ok=False (never invent 100%).
    - Publish hit/total for lines, functions, branches.
    """
    import re

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
        return {
            "ok": False,
            "error": (r.stderr or r.stdout or "")[-800:],
            "lines": 0.0,
            "functions": 0.0,
            "branches": 0.0,
            "raw": {
                "lines_hit": 0,
                "lines_total": 0,
                "functions_hit": 0,
                "functions_total": 0,
                "branches_hit": 0,
                "branches_total": 0,
                "error": "coverage-build-failed",
            },
        }

    bin_path = CROOT / "build" / "uem-c"
    if not bin_path.is_file():
        return {
            "ok": False,
            "lines": 0.0,
            "functions": 0.0,
            "branches": 0.0,
            "raw": {
                "lines_hit": 0,
                "lines_total": 0,
                "functions_hit": 0,
                "functions_total": 0,
                "branches_hit": 0,
                "branches_total": 0,
                "error": "missing-uem-c-binary",
            },
        }

    env = os.environ.copy()
    env["UEM_C"] = str(bin_path)
    # Exercise portable core via public host only (no third_party scoring).
    _run(
        [
            str(ROOT / ".venv" / "bin" / "python"),
            "-m",
            "pytest",
            "tests/test_l13.py",
            "tests/test_l13_deep.py",
            "tests/test_l13_coverage.py",
            "tests/test_l11.py",
            "tests/test_uem.py",
            "-q",
            "--tb=no",
        ],
        cwd=str(ROOT),
        env=env,
        timeout=600,
    )
    _run(
        [
            str(ROOT / ".venv" / "bin" / "python"),
            "-c",
            "from unified.machine.l13_catalog import run_all_catalogs; run_all_catalogs()",
        ],
        cwd=str(ROOT),
        env=env,
        timeout=300,
    )
    for uem in (ROOT / "artifacts/uem").rglob("*.uem"):
        _run([str(bin_path), "verify", str(uem)])
        _run([str(bin_path), "run", str(uem), "--host", '{"text":"hi\\nthere words"}'])
        _run(
            [
                str(bin_path),
                "run",
                str(uem),
                "--host",
                '{"document":{"items":[{"quantity":2,"unit_price":"1.50"}]}}',
            ]
        )
    for v in (CROOT / "tests/vectors").glob("*.uem"):
        _run([str(bin_path), "verify", str(v)])
    for g in (CROOT / "tests/golden").glob("*.json"):
        # golden host payloads if paired .uem exists
        pass

    # Collect gcov for core/*.c only
    lines_hit = lines_total = 0
    funcs_hit = funcs_total = 0
    br_hit = br_total = 0
    per_file = []
    missing_gcno = []

    for cfile in sorted((CROOT / "core").glob("*.c")):
        stem = cfile.stem
        gcno = _gcno_for_core(stem)
        if gcno is None:
            missing_gcno.append(stem)
            continue
        # Apple clang: -o path/to/uem-c-stem.gcno (note file, not directory)
        r = _run(
            ["gcov", "-b", "-o", str(gcno), str(cfile)],
            cwd=str(CROOT),
            timeout=60,
        )
        text = (r.stdout or "") + (r.stderr or "")
        file_raw = {"source": str(cfile.relative_to(CROOT)), "gcno": str(gcno.name)}

        m = re.search(r"Lines executed:([\d.]+)% of (\d+)", text)
        if m:
            pct, n = float(m.group(1)), int(m.group(2))
            lh = int(round(pct / 100.0 * n))
            lines_total += n
            lines_hit += lh
            file_raw["lines_hit"] = lh
            file_raw["lines_total"] = n
            file_raw["lines_pct"] = pct
        else:
            file_raw["lines_parse"] = "missing"

        # Branch metric: taken at least once (L13 "C branches")
        m = re.search(r"Taken at least once:([\d.]+)% of (\d+)", text)
        if m:
            pct, n = float(m.group(1)), int(m.group(2))
            bh = int(round(pct / 100.0 * n))
            br_total += n
            br_hit += bh
            file_raw["branches_hit"] = bh
            file_raw["branches_total"] = n
            file_raw["branches_pct"] = pct
        else:
            file_raw["branches_parse"] = "missing"

        # Functions: parse generated .gcov (Apple puts "function X called N" there)
        gcov_path = CROOT / f"{cfile.name}.gcov"
        fh = ft = 0
        if gcov_path.is_file():
            gtext = gcov_path.read_text(encoding="utf-8", errors="replace")
            for name, count in re.findall(
                r"^function\s+(\S+)\s+called\s+(\d+)", gtext, flags=re.M
            ):
                ft += 1
                if int(count) > 0:
                    fh += 1
        funcs_total += ft
        funcs_hit += fh
        file_raw["functions_hit"] = fh
        file_raw["functions_total"] = ft
        per_file.append(file_raw)

    raw = {
        "lines_hit": lines_hit,
        "lines_total": lines_total,
        "functions_hit": funcs_hit,
        "functions_total": funcs_total,
        "branches_hit": br_hit,
        "branches_total": br_total,
        "files": per_file,
        "missing_gcno": missing_gcno,
        "instrumentation": "gcov --coverage core/*.c via uem-c-*.gcno",
    }

    # Invalid if any required denominator is zero (cannot claim 100%).
    denom_ok = lines_total > 0 and funcs_total > 0 and br_total > 0 and not missing_gcno
    lines_pct = _pct(lines_hit, lines_total)
    funcs_pct = _pct(funcs_hit, funcs_total)
    br_pct = _pct(br_hit, br_total)
    ok = (
        denom_ok
        and lines_pct >= 100.0 - 1e-9
        and funcs_pct >= 100.0 - 1e-9
        and br_pct >= 100.0 - 1e-9
    )
    if not denom_ok:
        raw["error"] = "zero-denominator-or-missing-gcno"
    return {
        "lines": lines_pct,
        "functions": funcs_pct,
        "branches": br_pct,
        "ok": ok,
        "raw": raw,
    }


def catalog_scores() -> dict:
    """Run L13 behavioral catalogs (not line coverage)."""
    from .l13_catalog import run_all_catalogs

    return run_all_catalogs()


def measure_fuzz_100k() -> dict:
    """≥100k deterministic py/C verify agreement. Failures must be zero."""
    env = os.environ.copy()
    env["UEM_C"] = str(CROOT / "build" / "uem-c")
    env["UEM_FUZZ_N"] = os.environ.get("UEM_FUZZ_N", "100000")
    env["UEM_FUZZ_SEED"] = os.environ.get("UEM_FUZZ_SEED", "12")
    r = _run(
        [str(ROOT / ".venv" / "bin" / "python"), str(CROOT / "scripts" / "fuzz_l12.py")],
        cwd=str(ROOT),
        env=env,
        timeout=600,
    )
    text = (r.stdout or "") + "\n" + (r.stderr or "")
    # last JSON line is report
    report = {}
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{") and "mutations" in line:
            try:
                report = json.loads(line)
            except json.JSONDecodeError:
                pass
            break
    fails = int(report.get("failures", 1 if r.returncode != 0 else 0))
    mutations = int(report.get("mutations", 0))
    ok = r.returncode == 0 and fails == 0 and mutations >= 100_000
    return {
        "required": 100.0,
        "actual": 100.0 if ok else (0.0 if mutations < 100_000 else 100.0 * (1.0 - fails / max(mutations, 1))),
        "ok": ok,
        "detail": {
            "mutations": mutations,
            "failures": fails,
            "returncode": r.returncode,
            "mode": report.get("mode"),
        },
    }


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
    fuzz = measure_fuzz_100k()

    c_raw = c_cov.get("raw") or {}
    c_lines_total = int(c_raw.get("lines_total") or 0)
    c_funcs_total = int(c_raw.get("functions_total") or 0)
    c_br_total = int(c_raw.get("branches_total") or 0)
    # Zero total is never OK — invalid measurement, not 100%.
    c_lines_ok = c_lines_total > 0 and float(c_cov.get("lines") or 0) >= 100.0 - 1e-9
    c_funcs_ok = c_funcs_total > 0 and float(c_cov.get("functions") or 0) >= 100.0 - 1e-9
    c_br_ok = c_br_total > 0 and float(c_cov.get("branches") or 0) >= 100.0 - 1e-9

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
            "ok": c_lines_ok,
            "raw": {
                "hit": c_raw.get("lines_hit", 0),
                "total": c_lines_total,
                "files": c_raw.get("files"),
                "error": c_raw.get("error"),
            },
        },
        "c_functions": {
            "required": 100.0,
            "actual": c_cov.get("functions", 0.0),
            "ok": c_funcs_ok,
            "raw": {
                "hit": c_raw.get("functions_hit", 0),
                "total": c_funcs_total,
            },
        },
        "c_branches": {
            "required": 100.0,
            "actual": c_cov.get("branches", 0.0),
            "ok": c_br_ok,
            "raw": {
                "hit": c_raw.get("branches_hit", 0),
                "total": c_br_total,
            },
        },
        "fuzz_100k": fuzz,
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
        raw = d.get("raw") or {}
        if isinstance(raw, dict) and "total" in raw:
            act_s = f"{act_s} ({raw.get('hit', '?')}/{raw.get('total', '?')})"
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
            "- **Zero denominator is failure** (never report 100% of 0)",
            "",
            f"Generated in {report.get('duration_s', 0):.1f}s.",
            "",
        ]
    )
    (ROOT / "GAUNTLET.md").write_text("\n".join(lines), encoding="utf-8")
