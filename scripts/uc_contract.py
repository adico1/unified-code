#!/usr/bin/env python3
"""Milestone 1 application acceptance contract — single script tool.

Repository self-hosting is reported separately as Milestone 2 and never blocks
the seed-to-application contract.

Usage:
  python3 scripts/uc_contract.py plan              # ordered work plan
  python3 scripts/uc_contract.py status            # live criterion status
  python3 scripts/uc_contract.py verify [--quick]  # run gates (quick=no L13)
  python3 scripts/uc_contract.py report            # 14-point final report JSON
  python3 scripts/uc_contract.py ledger            # refresh branch ledger only
  python3 scripts/uc_contract.py conservation      # baseline conservation only

Exit codes:
  0  — Milestone 1 application contract green
  1  — one or more Milestone 1 criteria fail (report lists them)
  2  — tool/environment error
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CROOT = ROOT / "c"
BASELINE_JSON = CROOT / "tests" / "branch_baseline.json"
LEDGER_JSON = CROOT / "tests" / "branch_ledger.json"
HISTORY_JSON = CROOT / "tests" / "branch_ledger_history.json"
COVERAGE_JSON = ROOT / "coverage.json"
GAUNTLET_MD = ROOT / "GAUNTLET.md"
AUDIT_MD = ROOT / "AUDIT_STANDARD_TEN.md"
BASELINE_COMMIT = "3a0bf81"
PY = ROOT / ".venv" / "bin" / "python"
UC = ROOT / ".venv" / "bin" / "uc"
UEM_C = CROOT / "build" / "uem-c"

# ---------------------------------------------------------------------------
# Plan: ordered phases from the acceptance contract / blocker unblocker
# ---------------------------------------------------------------------------

PLAN_PHASES: list[dict[str, Any]] = [
    {
        "id": "P0",
        "name": "Contract measurement freeze",
        "status_key": "baseline_frozen",
        "goal": "Keep 3a0bf81 baseline; never re-freeze until current_open=0",
        "actions": [
            "Refuse to rewrite c/tests/branch_baseline.json",
            "Run scripts/uc_contract.py conservation after every batch",
            "Require: ambiguous_arcs=0, unmapped_arcs=0, conservation holds",
        ],
        "acceptance": [
            "baseline_commit == 3a0bf81",
            "baseline_open == 311",
            "conservation equation holds",
        ],
    },
    {
        "id": "P1",
        "name": "C branch closure (remaining ledger)",
        "status_key": "c_branches_closed",
        "goal": "current_open=0 under frozen baseline; L13 c_branches 100%",
        "order": [
            "semantic decode verification (image/STOP/primitive)",
            "expression evaluator paths",
            "machine second arms and boundaries",
            "primitive registry paths",
            "decimal signs and rounding",
            "short-circuit operand combinations",
            "allocator failures",
            "runtime/ticket failures",
            "redundant/impossible: production simplify (decode.c:10/93/94 last)",
        ],
        "rules": [
            "reachable → semantic test with exact assertions",
            "redundant → simplify production without behavior loss",
            "impossible → encode invariant earlier; remove dead arm",
            "no coverage gaming; no excludes; no 100% of zero",
            "any new_arc closed in same operation",
        ],
        "acceptance": [
            "current_open == 0",
            "missing_arcs_measured == 0",
            "unmapped_arcs == 0",
            "unclassified_arcs == 0",
            "ambiguous_arcs == 0",
            "C branches hit == total and total > 0",
        ],
    },
    {
        "id": "P2",
        "name": "uc unfold one-command pipeline",
        "status_key": "uc_unfold_exists",
        "goal": "seed → validated, generated, built, verified, installed application",
        "pipeline": [
            "validate seed",
            "derive declarations",
            "assemble symbolic program",
            "resolve dependency graph",
            "generate UEM-16 bytecode",
            "generate Python host",
            "generate C99 host",
            "generate event routes and handlers",
            "generate boundaries and ticket handling",
            "generate tests, mutations, fuzz, goldens",
            "build C interpreter/application",
            "execute Python and C applications",
            "compare canonical results",
            "run L1–L13 gauntlet",
            "publish signed deterministic build manifest",
            "atomically install valid application",
        ],
        "cli": "uc unfold <seed> --output <directory> --verify --run",
        "atomicity": [
            "build only in temp dir",
            "install only after all gates pass",
            "on failure: preserve diagnostics, ticket if unhandled, leave prior output",
        ],
        "acceptance": [
            "uc unfold command registered and documented",
            "exit 0 only after full verify+run",
            "no partial install on failure",
        ],
    },
    {
        "id": "P3",
        "name": "Independent task-ledger seed proof",
        "status_key": "task_ledger_seed",
        "goal": "One seed (not text/invoice) unfolds to a usable app",
        "seed_path": "seed/declarations/task_ledger.json",
        "domain": [
            "add task",
            "complete task",
            "list tasks",
            "reject malformed commands",
            "deterministic order",
            "persist only via OUTWARD",
            "ticket only on unhandled failure",
        ],
        "proof_command": (
            "uc unfold seed/declarations/task_ledger.json "
            "--output /tmp/uc-task-ledger --verify --run"
        ),
        "acceptance": [
            "seed exists and is sole app source",
            "generated tree has 0 manual edits",
            "app runs immediately after unfold",
        ],
    },
    {
        "id": "P4",
        "name": "Milestone 2 root-seed fixed-point bootstrap",
        "status_key": "standard_ten_pass",
        "goal": "Later: AUDIT_STANDARD_TEN repository self-hosting verdict pass",
        "gaps": [
            "gap.seed-expresses-full-framework",
            "gap.no-app-control-flow-in-host",
            "gap.oop-exprfail",
            "gap.declarations-as-python",
            "gap.dual-host-not-single-machine-surface",
            "gap.generated-tests-and-docs",
            "gap.clean-room-full-tree",
        ],
        "acceptance": [
            "scripts/audit_standard_ten.py verdict == pass",
            "open standard.gap tickets == 0",
        ],
    },
    {
        "id": "P5",
        "name": "Full gauntlet + CI",
        "status_key": "full_gauntlet",
        "goal": "L1–L13 all 100%; CI runs same one-command unfold proof",
        "acceptance": [
            "Python statements/branches 100%",
            "C lines/functions/branches 100% nonzero denoms",
            "opcodes 16/16, primitives 100%, mutations 100%",
            "Py/C differential exact equality",
            "ASan pass, UBSan pass",
            "fuzz configured target zero mismatches",
            "deterministic rebuild byte-identical",
            "CI workflow invokes uc_contract verify + unfold proof",
        ],
    },
    {
        "id": "P6",
        "name": "Publish evidence",
        "status_key": "docs_published",
        "goal": "LAW/SPEC/README/GAUNTLET + signed manifest reflect truth",
        "acceptance": [
            "GAUNTLET.md matches live L13",
            "coverage.json branch_ledger conservation",
            "manifest hashes seed, bytecode, binaries, gauntlet evidence",
            "git status clean after commit of complete contract only",
        ],
    },
]


# ---------------------------------------------------------------------------
# Criterion model
# ---------------------------------------------------------------------------

def Criterion(
    id: str,
    name: str,
    phase: str,
    required: Any,
    actual: Any,
    ok: bool,
    evidence: str = "",
    blocker: str = "",
) -> dict[str, Any]:
    """Plain-data criterion row (no class — Standard Ten rule 5)."""
    return {
        "id": id,
        "name": name,
        "phase": phase,
        "required": required,
        "actual": actual,
        "ok": ok,
        "evidence": evidence,
        "blocker": blocker,
    }


def ContractStatus(
    timestamp: str,
    git_head: str,
    baseline_commit: str,
    criteria: list | None = None,
    conservation: dict | None = None,
    phases: list | None = None,
    blockers: list | None = None,
    contract_pass: bool = False,
    self_hosting_pass: bool = False,
    self_hosting_blockers: list | None = None,
) -> dict[str, Any]:
    """Plain-data contract status (no class)."""
    return {
        "timestamp": timestamp,
        "git_head": git_head,
        "baseline_commit": baseline_commit,
        "criteria": list(criteria or []),
        "conservation": dict(conservation or {}),
        "phases": list(phases or []),
        "blockers": list(blockers or []),
        "contract_pass": bool(contract_pass),
        "application_conformance": "pass" if contract_pass else "fail",
        "self_hosting_pass": bool(self_hosting_pass),
        "self_hosting_conformance": "pass" if self_hosting_pass else "open",
        "self_hosting_blockers": list(self_hosting_blockers or []),
    }


def contract_status_to_dict(st: dict[str, Any]) -> dict[str, Any]:
    criteria = st.get("criteria") or []
    return {
        "timestamp": st.get("timestamp"),
        "git_head": st.get("git_head"),
        "baseline_commit": st.get("baseline_commit"),
        "contract_pass": st.get("contract_pass"),
        "blockers": st.get("blockers"),
        "application_conformance": st.get("application_conformance"),
        "self_hosting_pass": st.get("self_hosting_pass"),
        "self_hosting_conformance": st.get("self_hosting_conformance"),
        "self_hosting_blockers": st.get("self_hosting_blockers"),
        "conservation": st.get("conservation"),
        "criteria": list(criteria),
        "phases": st.get("phases"),
        "summary": {
            "total": len(criteria),
            "passed": sum(1 for c in criteria if c.get("ok")),
            "failed": sum(1 for c in criteria if not c.get("ok")),
        },
    }


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 600,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    e = os.environ.copy()
    if env:
        e.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=e,
    )


def _git_head() -> str:
    r = _run(["git", "rev-parse", "--short", "HEAD"])
    return (r.stdout or "").strip() or "unknown"


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _py() -> str:
    return str(PY) if PY.is_file() else sys.executable


# ---------------------------------------------------------------------------
# Live measurements
# ---------------------------------------------------------------------------

def measure_conservation() -> dict[str, Any]:
    baseline = _load_json(BASELINE_JSON) or {}
    ledger = _load_json(LEDGER_JSON) or {}
    history = _load_json(HISTORY_JSON) or {}

    baseline_open = int(
        ledger.get("baseline_open")
        or baseline.get("baseline_open")
        or 0
    )
    resolved = int(ledger.get("resolved_by_test") or 0)
    removed = int(ledger.get("removed_by_refactor") or 0)
    new_arcs = int(ledger.get("new_arcs") or 0)
    remapped = int(ledger.get("remapped_arcs") or 0)
    ambiguous = int(ledger.get("ambiguous_arcs") or 0)
    current_open = int(ledger.get("current_open") or ledger.get("missing_arcs_measured") or 0)
    unmapped = int(ledger.get("unmapped_arcs") or 0)
    unclassified = int(ledger.get("unclassified_arcs") or 0)
    measured = int(ledger.get("missing_arcs_measured") or current_open)
    in_ledger = int(ledger.get("missing_arcs_in_ledger") or measured)
    hit = ledger.get("branches_hit")
    total = ledger.get("branches_total")

    left = baseline_open + new_arcs
    right = resolved + removed + current_open
    cons_holds = left == right
    meas_holds = measured == in_ledger + unmapped

    return {
        "baseline_commit": baseline.get("baseline_commit") or ledger.get("baseline_commit"),
        "baseline_open": baseline_open,
        "resolved_by_test": resolved,
        "removed_by_refactor": removed,
        "new_arcs": new_arcs,
        "remapped_arcs": remapped,
        "ambiguous_arcs": ambiguous,
        "current_open": current_open,
        "still_baseline_open": ledger.get("still_baseline_open"),
        "missing_arcs_measured": measured,
        "missing_arcs_in_ledger": in_ledger,
        "unmapped_arcs": unmapped,
        "unclassified_arcs": unclassified,
        "branches_hit": hit,
        "branches_total": total,
        "conservation": {
            "equation": "baseline_open + new_arcs == resolved_by_test + removed_by_refactor + current_open",
            "left": left,
            "right": right,
            "holds": cons_holds,
        },
        "measurement": {
            "equation": "missing_arcs_measured == missing_arcs_in_ledger + unmapped_arcs",
            "holds": meas_holds,
        },
        "history_note": history.get("note"),
        "ledger_path": str(LEDGER_JSON.relative_to(ROOT)) if LEDGER_JSON.is_file() else None,
        "baseline_path": str(BASELINE_JSON.relative_to(ROOT)) if BASELINE_JSON.is_file() else None,
    }


def measure_uc_unfold() -> dict[str, Any]:
    """Probe whether uc unfold exists and task-ledger seed exists."""
    cli = ROOT / "unified" / "generator" / "cli.py"
    text = cli.read_text(encoding="utf-8") if cli.is_file() else ""
    has_unfold = "unfold" in text and (
        'command == "unfold"' in text or 'command=="unfold"' in text
    )
    seed = ROOT / "seed" / "declarations" / "task_ledger.json"
    # Try running uc unfold --help-ish
    r = None
    if UC.is_file():
        r = _run([str(UC), "unfold"], timeout=30)
    return {
        "uc_binary": str(UC) if UC.is_file() else None,
        "unfold_in_cli_source": has_unfold,
        "task_ledger_seed_exists": seed.is_file(),
        "task_ledger_seed_path": str(seed.relative_to(ROOT)) if seed.is_file() else None,
        "probe_exit": None if r is None else r.returncode,
        "probe_stdout_tail": (r.stdout or "")[-300:] if r else "",
        "ok": has_unfold and seed.is_file(),
    }


def measure_l13_snapshot() -> dict[str, Any]:
    cov = _load_json(COVERAGE_JSON) or {}
    dims = cov.get("dimensions") or {}
    out: dict[str, Any] = {"verdict": cov.get("verdict"), "dimensions": {}}
    for k, d in dims.items():
        if not isinstance(d, dict):
            continue
        out["dimensions"][k] = {
            "ok": d.get("ok"),
            "actual": d.get("actual"),
            "raw": d.get("raw"),
        }
    bl = cov.get("branch_ledger") or {}
    if bl:
        out["branch_ledger"] = bl
    return out


def measure_standard_ten() -> dict[str, Any]:
    audit = AUDIT_MD.read_text(encoding="utf-8") if AUDIT_MD.is_file() else ""
    verdict = "unknown"
    if "**Verdict:** `pass`" in audit:
        verdict = "pass"
    elif "**Verdict:** `fail`" in audit:
        verdict = "fail"
    gaps = []
    for line in audit.splitlines():
        if line.strip().startswith("- **gap."):
            gaps.append(line.strip()[4:].split("**")[0] if "**" in line else line.strip())
    return {
        "verdict": verdict,
        "open_gaps": gaps,
        "ok": verdict == "pass",
        "audit_path": str(AUDIT_MD.relative_to(ROOT)) if AUDIT_MD.is_file() else None,
    }


# ---------------------------------------------------------------------------
# Status assembly
# ---------------------------------------------------------------------------

def build_status() -> dict[str, Any]:
    cons = measure_conservation()
    unfold = measure_uc_unfold()
    l13 = measure_l13_snapshot()
    ten = measure_standard_ten()
    dims = l13.get("dimensions") or {}

    def dim_ok(name: str, require_100: bool = True) -> dict[str, Any]:
        d = dims.get(name) or {}
        actual = d.get("actual")
        ok = bool(d.get("ok"))
        if require_100 and actual is not None:
            try:
                ok = ok and float(actual) >= 100.0 - 1e-9
            except (TypeError, ValueError):
                ok = False
        raw = d.get("raw") or {}
        evidence = f"actual={actual}"
        if raw.get("hit") is not None:
            evidence += f" hit/total={raw.get('hit')}/{raw.get('total')}"
        return Criterion(
            id=f"l13.{name}",
            name=f"L13 dimension {name}",
            phase="P1/P5",
            required=100.0 if require_100 else True,
            actual=actual if actual is not None else d.get("ok"),
            ok=ok,
            evidence=evidence,
            blocker="" if ok else f"dimension {name} not at required 100%",
        )

    criteria: list[dict[str, Any]] = []

    # Baseline frozen
    bl_ok = (
        cons.get("baseline_commit") == BASELINE_COMMIT
        and cons.get("baseline_open") == 311
        and BASELINE_JSON.is_file()
    )
    criteria.append(
        Criterion(
            "baseline.frozen",
            "Branch baseline frozen at 3a0bf81 with open=311",
            "P0",
            {"commit": BASELINE_COMMIT, "open": 311},
            {"commit": cons.get("baseline_commit"), "open": cons.get("baseline_open")},
            bl_ok,
            evidence=str(BASELINE_JSON.relative_to(ROOT)) if BASELINE_JSON.is_file() else "missing",
            blocker="" if bl_ok else "baseline file missing or wrong commit/open count",
        )
    )

    # Conservation
    ch = bool((cons.get("conservation") or {}).get("holds"))
    criteria.append(
        Criterion(
            "baseline.conservation",
            "baseline_open + new_arcs == resolved + removed + current_open",
            "P0",
            True,
            cons.get("conservation"),
            ch,
            evidence=json.dumps(cons.get("conservation")),
            blocker="" if ch else "conservation equation broken",
        )
    )
    mh = bool((cons.get("measurement") or {}).get("holds"))
    criteria.append(
        Criterion(
            "ledger.measurement",
            "missing_arcs_measured == in_ledger + unmapped",
            "P0",
            True,
            cons.get("measurement"),
            mh,
            evidence=json.dumps(cons.get("measurement")),
            blocker="" if mh else "ledger measurement reconciliation broken",
        )
    )
    criteria.append(
        Criterion(
            "ledger.unmapped",
            "unmapped_arcs == 0",
            "P0",
            0,
            cons.get("unmapped_arcs"),
            cons.get("unmapped_arcs") == 0,
            blocker="" if cons.get("unmapped_arcs") == 0 else "unmapped arcs present",
        )
    )
    criteria.append(
        Criterion(
            "ledger.unclassified",
            "unclassified_arcs == 0",
            "P0",
            0,
            cons.get("unclassified_arcs"),
            cons.get("unclassified_arcs") == 0,
        )
    )
    criteria.append(
        Criterion(
            "ledger.ambiguous",
            "ambiguous_arcs == 0",
            "P0",
            0,
            cons.get("ambiguous_arcs"),
            cons.get("ambiguous_arcs") == 0,
        )
    )

    # Branch closure complete
    co = cons.get("current_open")
    criteria.append(
        Criterion(
            "branches.current_open_zero",
            "current_open == 0",
            "P1",
            0,
            co,
            co == 0,
            evidence=f"resolved_by_test={cons.get('resolved_by_test')} still_baseline_open={cons.get('still_baseline_open')}",
            blocker="" if co == 0 else f"{co} baseline-relative open arcs remain",
        )
    )
    hit, total = cons.get("branches_hit"), cons.get("branches_total")
    br_ok = (
        isinstance(hit, int)
        and isinstance(total, int)
        and total > 0
        and hit == total
    )
    criteria.append(
        Criterion(
            "branches.c_100",
            "C branches 100% nonzero denominator",
            "P1",
            "hit==total>0",
            f"{hit}/{total}",
            br_ok,
            blocker="" if br_ok else f"C branches incomplete: {hit}/{total}",
        )
    )

    # L13 dimensions from last coverage.json (not re-running unless verify)
    for name in (
        "python_statements",
        "python_branches",
        "c_lines",
        "c_functions",
        "c_branches",
        "python_c_differential",
    ):
        if name in dims:
            criteria.append(dim_ok(name, require_100=True))

    l13_verdict = l13.get("verdict")
    criteria.append(
        Criterion(
            "l13.verdict",
            "L13 overall pass",
            "P5",
            "pass",
            l13_verdict,
            l13_verdict == "pass",
            evidence=str(COVERAGE_JSON.relative_to(ROOT)) if COVERAGE_JSON.is_file() else "no coverage.json",
            blocker="" if l13_verdict == "pass" else f"L13 verdict={l13_verdict!r}",
        )
    )

    # unfold
    criteria.append(
        Criterion(
            "unfold.cli",
            "uc unfold implemented in CLI",
            "P2",
            True,
            unfold.get("unfold_in_cli_source"),
            bool(unfold.get("unfold_in_cli_source")),
            evidence=json.dumps({k: unfold[k] for k in ("uc_binary", "unfold_in_cli_source", "probe_exit")}),
            blocker="" if unfold.get("unfold_in_cli_source") else "uc unfold not in unified/generator/cli.py",
        )
    )
    criteria.append(
        Criterion(
            "unfold.task_ledger_seed",
            "seed/declarations/task_ledger.json exists",
            "P3",
            True,
            unfold.get("task_ledger_seed_exists"),
            bool(unfold.get("task_ledger_seed_exists")),
            blocker="" if unfold.get("task_ledger_seed_exists") else "task_ledger seed missing",
        )
    )

    # Standard Ten
    criteria.append(
        Criterion(
            "standard_ten.audit",
            "Standard Ten audit pass",
            "P4",
            "pass",
            ten.get("verdict"),
            bool(ten.get("ok")),
            evidence=f"gaps={ten.get('open_gaps')}",
            blocker="" if ten.get("ok") else f"Standard Ten fail; gaps={ten.get('open_gaps')}",
        )
    )

    application_criteria = [c for c in criteria if c["phase"] != "P4"]
    blockers = [
        c["blocker"]
        for c in application_criteria
        if not c["ok"] and c["blocker"]
    ]
    self_hosting_blockers = [
        c["blocker"]
        for c in criteria
        if c["phase"] == "P4" and not c["ok"] and c["blocker"]
    ]
    # Phase rollup
    phase_status = []
    for ph in PLAN_PHASES:
        # map phase to criteria prefix
        pid = ph["id"]
        related = [c for c in criteria if pid in c["phase"] or c["phase"].startswith(pid)]
        if pid == "P0":
            related = [c for c in criteria if c["id"].startswith("baseline") or c["id"].startswith("ledger")]
        elif pid == "P1":
            related = [c for c in criteria if c["id"].startswith("branches") or c["id"] == "l13.c_branches"]
        elif pid == "P2":
            related = [c for c in criteria if c["id"].startswith("unfold.cli")]
        elif pid == "P3":
            related = [c for c in criteria if c["id"].startswith("unfold.task")]
        elif pid == "P4":
            related = [c for c in criteria if c["id"].startswith("standard_ten")]
        elif pid == "P5":
            related = [c for c in criteria if c["id"].startswith("l13") or c["id"].startswith("branches.c")]
        elif pid == "P6":
            related = []
        ok = all(c["ok"] for c in related) if related else False
        phase_status.append(
            {
                "id": pid,
                "name": ph["name"],
                "ok": ok,
                "goal": ph.get("goal"),
                "related_failed": [c["id"] for c in related if not c["ok"]],
            }
        )

    st = ContractStatus(
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        git_head=_git_head(),
        baseline_commit=BASELINE_COMMIT,
        criteria=criteria,
        conservation=cons,
        phases=phase_status,
        blockers=blockers,
        contract_pass=all(c["ok"] for c in application_criteria),
        self_hosting_pass=all(c["ok"] for c in criteria if c["phase"] == "P4"),
        self_hosting_blockers=self_hosting_blockers,
    )
    return st


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_plan(_: argparse.Namespace) -> int:
    print("# Unified Code complete-contract plan")
    print(f"# Baseline freeze: {BASELINE_COMMIT}")
    print(f"# Tool: scripts/uc_contract.py")
    print()
    for ph in PLAN_PHASES:
        print(f"## {ph['id']}: {ph['name']}")
        print(f"Goal: {ph.get('goal')}")
        if ph.get("cli"):
            print(f"CLI: `{ph['cli']}`")
        if ph.get("proof_command"):
            print(f"Proof: `{ph['proof_command']}`")
        if ph.get("pipeline"):
            print("Pipeline:")
            for step in ph["pipeline"]:
                print(f"  - {step}")
        if ph.get("order"):
            print("Order:")
            for step in ph["order"]:
                print(f"  - {step}")
        if ph.get("gaps"):
            print("Gaps:")
            for g in ph["gaps"]:
                print(f"  - {g}")
        if ph.get("actions"):
            print("Actions:")
            for a in ph["actions"]:
                print(f"  - {a}")
        if ph.get("rules"):
            print("Rules:")
            for r in ph["rules"]:
                print(f"  - {r}")
        print("Acceptance:")
        for a in ph.get("acceptance") or []:
            print(f"  - {a}")
        print()
    print("## Conservation (always)")
    print("```text")
    print("baseline_open + new_arcs")
    print("  = resolved_by_test + removed_by_refactor + current_open")
    print("```")
    print("Do not re-freeze baseline until current_open == 0.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    st = build_status()
    if args.json:
        print(json.dumps(contract_status_to_dict(st), indent=2, sort_keys=True))
    else:
        print(f"contract_pass: {st["contract_pass"]}")
        print(f"git_head: {st["git_head"]}")
        print(f"baseline: {st["baseline_commit"]}")
        print()
        cons = st["conservation"]
        print("## Conservation")
        for k in (
            "baseline_open",
            "resolved_by_test",
            "removed_by_refactor",
            "new_arcs",
            "remapped_arcs",
            "ambiguous_arcs",
            "current_open",
            "branches_hit",
            "branches_total",
        ):
            print(f"  {k}: {cons.get(k)}")
        print(f"  conservation_holds: {(cons.get('conservation') or {}).get('holds')}")
        print(f"  measurement_holds: {(cons.get('measurement') or {}).get('holds')}")
        print()
        print("## Phases")
        for ph in st["phases"]:
            mark = "OK" if ph["ok"] else "FAIL"
            print(f"  [{mark}] {ph['id']} {ph['name']}")
            if ph.get("related_failed"):
                print(f"         failed: {', '.join(ph['related_failed'])}")
        print()
        print("## Criteria")
        for c in st["criteria"]:
            mark = "OK" if c["ok"] else "FAIL"
            print(f"  [{mark}] {c["id"]}: required={c["required"]!r} actual={c["actual"]!r}")
            if c["blocker"]:
                print(f"         blocker: {c["blocker"]}")
        if st["blockers"]:
            print()
            print("## Blockers")
            for b in st["blockers"]:
                print(f"  - {b}")
    return 0 if st["contract_pass"] else 1


def cmd_conservation(_: argparse.Namespace) -> int:
    cons = measure_conservation()
    print(json.dumps(cons, indent=2, sort_keys=True))
    ok = (
        (cons.get("conservation") or {}).get("holds")
        and (cons.get("measurement") or {}).get("holds")
        and cons.get("unmapped_arcs") == 0
        and cons.get("ambiguous_arcs") == 0
    )
    return 0 if ok else 1


def cmd_ledger(_: argparse.Namespace) -> int:
    script = CROOT / "scripts" / "branch_ledger.py"
    if not script.is_file():
        print("missing c/scripts/branch_ledger.py", file=sys.stderr)
        return 2
    r = _run([_py(), str(script)], cwd=CROOT, timeout=180)
    sys.stdout.write(r.stdout or "")
    sys.stderr.write(r.stderr or "")
    return 0 if r.returncode in (0, 1) else 2  # 1 = work remains


def cmd_verify(args: argparse.Namespace) -> int:
    """Run verification gates. Full L13 unless --quick."""
    results: dict[str, Any] = {"steps": [], "ok": True}
    t0 = time.time()

    def step(name: str, cmd: list[str], cwd: Path | None = None, timeout: int = 600) -> None:
        print(f"=== {name} ===", flush=True)
        r = _run(cmd, cwd=cwd, timeout=timeout, env={"UEM_C": str(UEM_C)})
        entry = {
            "name": name,
            "cmd": cmd,
            "exit": r.returncode,
            "ok": r.returncode == 0,
            "stdout_tail": (r.stdout or "")[-500:],
            "stderr_tail": (r.stderr or "")[-500:],
        }
        results["steps"].append(entry)
        if r.returncode != 0:
            results["ok"] = False
            print(f"FAIL {name} exit={r.returncode}", flush=True)
            if r.stdout:
                print(r.stdout[-1000:])
            if r.stderr:
                print(r.stderr[-1000:], file=sys.stderr)
        else:
            print(f"OK {name}", flush=True)

    # always: conservation + ledger refresh
    step("branch_ledger", [_py(), str(CROOT / "scripts" / "branch_ledger.py")], cwd=CROOT)
    # dependency-free self-test subset or full
    if args.quick:
        step(
            "selftest-core",
            [
                _py(),
                "-m",
                "unified.selftest",
                "tests/test_binding_mutations.py",
                "tests/test_oom_mutations.py",
                "tests/test_uem.py",
            ],
        )
    else:
        step(
            "make_posix",
            ["make", "-C", str(CROOT), "clean"],
            timeout=120,
        )
        step(
            "make_posix_build",
            [
                "make",
                "-C",
                str(CROOT),
                "posix",
                "CFLAGS=-std=c99 -Wall -O2 -Iinclude -Ithird_party -Icore -Ihost/mcu",
            ],
            timeout=180,
        )
        step(
            "c_run_tests",
            ["bash", str(CROOT / "scripts" / "run_tests.sh")],
            cwd=CROOT,
            timeout=300,
        )
        if not args.skip_sanitizers:
            step(
                "c_l11_full",
                ["bash", str(CROOT / "scripts" / "run_l11_full.sh")],
                cwd=CROOT,
                timeout=600,
            )
        if not args.skip_l13:
            step("l13", ["bash", str(ROOT / "scripts" / "run_l13.sh")], timeout=900)
        step(
            "standard_ten_audit",
            [_py(), str(ROOT / "scripts" / "audit_standard_ten.py")],
            timeout=180,
        )

    # contract status after gates
    st = build_status()
    results["contract"] = contract_status_to_dict(st)
    results["duration_s"] = round(time.time() - t0, 3)
    results["ok"] = results["ok"] and st["contract_pass"]

    out = ROOT / "contract_status.json"
    out.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")
    print(f"contract_pass={st["contract_pass"]} steps_ok={all(s['ok'] for s in results['steps'])}")
    if st["blockers"]:
        print("blockers:")
        for b in st["blockers"]:
            print(f"  - {b}")
    return 0 if results["ok"] else 1


def cmd_report(args: argparse.Namespace) -> int:
    """14-point final report structure from live data (honest incomplete)."""
    st = build_status()
    cons = st["conservation"]
    unfold = measure_uc_unfold()
    ten = measure_standard_ten()
    l13 = measure_l13_snapshot()

    report = {
        "1_public_commit_sha": st["git_head"],
        "2_uc_unfold_command": (
            "uc unfold seed/declarations/task_ledger.json "
            "--output /tmp/uc-task-ledger --verify --run"
        ),
        "2_uc_unfold_implemented": unfold.get("unfold_in_cli_source"),
        "3_seed_developer_written_line_count": None,
        "3_task_ledger_seed_exists": unfold.get("task_ledger_seed_exists"),
        "4_manual_generated_tree_edits": None,
        "5_generated_files_and_line_counts": None,
        "6_build_and_execution_timings": None,
        "7_python_c_canonical_outputs": None,
        "8_l1_l13_results": {
            "verdict": l13.get("verdict"),
            "dimensions": l13.get("dimensions"),
        },
        "9_coverage_hit_total": {
            "c_branches": f"{cons.get('branches_hit')}/{cons.get('branches_total')}",
            "current_open": cons.get("current_open"),
            "missing_arcs_measured": cons.get("missing_arcs_measured"),
        },
        "10_branch_conservation_equation": cons.get("conservation"),
        "10_measurement_equation": cons.get("measurement"),
        "10_fields": {
            "baseline_open": cons.get("baseline_open"),
            "resolved_by_test": cons.get("resolved_by_test"),
            "removed_by_refactor": cons.get("removed_by_refactor"),
            "new_arcs": cons.get("new_arcs"),
            "remapped_arcs": cons.get("remapped_arcs"),
            "ambiguous_arcs": cons.get("ambiguous_arcs"),
            "current_open": cons.get("current_open"),
        },
        "11_mutation_fuzz_sanitizer": "see last verify run / coverage.json",
        "12_deterministic_rebuild_hashes": None,
        "13_git_status": _run(["git", "status", "-sb"]).stdout,
        "14_unmet_criteria": [
            {"id": c["id"], "blocker": c["blocker"] or c["name"]}
            for c in st["criteria"]
            if not c["ok"]
        ],
        "standard_ten": ten,
        "unfold": unfold,
        "contract_pass": st["contract_pass"],
        "plan_phases": [
            {"id": p["id"], "name": p["name"], "goal": p.get("goal")}
            for p in PLAN_PHASES
        ],
        "timestamp": st["timestamp"],
        "complete_claim_allowed": False if not st["contract_pass"] else True,
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("# Final report (honest — complete only if contract_pass true)")
        print(f"contract_pass: {report['contract_pass']}")
        print(f"1. public commit SHA: {report['1_public_commit_sha']}")
        print(f"2. uc unfold: implemented={report['2_uc_unfold_implemented']}")
        print(f"   command: {report['2_uc_unfold_command']}")
        print(f"3. task_ledger seed exists: {report['3_task_ledger_seed_exists']}")
        print(f"8. L13 verdict: {(report['8_l1_l13_results'] or {}).get('verdict')}")
        print(f"9. C branches: {report['9_coverage_hit_total']}")
        print(f"10. conservation: {report['10_branch_conservation_equation']}")
        print(f"    fields: {report['10_fields']}")
        print(f"13. git status:\n{report['13_git_status']}")
        print("14. unmet criteria:")
        for u in report["14_unmet_criteria"]:
            print(f"   - {u['id']}: {u['blocker']}")
        print()
        print("Plan phases: " + ", ".join(p["id"] for p in PLAN_PHASES))
        print("Do not claim complete while contract_pass is false.")

    out = ROOT / "contract_report.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.json:
        print(f"\nwrote {out.relative_to(ROOT)}")
    return 0 if st["contract_pass"] else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="uc_contract",
        description="Unified Code complete acceptance contract tool",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("plan", help="Print ordered work plan (P0–P6)")
    sp = sub.add_parser("status", help="Live criterion status")
    sp.add_argument("--json", action="store_true")
    sub.add_parser("conservation", help="Baseline conservation JSON only")
    sub.add_parser("ledger", help="Regenerate branch ledger from gcov")
    vp = sub.add_parser("verify", help="Run verification gates + status")
    vp.add_argument("--quick", action="store_true", help="Skip L13 and sanitizers")
    vp.add_argument("--skip-l13", action="store_true")
    vp.add_argument("--skip-sanitizers", action="store_true")
    rp = sub.add_parser("report", help="14-point final report (honest)")
    rp.add_argument("--json", action="store_true")

    args = p.parse_args(argv)
    if args.cmd == "plan":
        return cmd_plan(args)
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "conservation":
        return cmd_conservation(args)
    if args.cmd == "ledger":
        return cmd_ledger(args)
    if args.cmd == "verify":
        return cmd_verify(args)
    if args.cmd == "report":
        return cmd_report(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
