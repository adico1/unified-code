#!/usr/bin/env python3
"""Shared gcov branch-arc enumeration for L13 and the branch ledger.

Authoritative branch metric = count of individual gcov branch arcs, not
rounded "Taken at least once:X% of N" summary lines (those can disagree
by O(files) arcs with int(round(pct/100*n))).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

CROOT = Path(__file__).resolve().parents[1]
CORE = CROOT / "core"
BUILD = CROOT / "build"

CORE_STEMS = ("alloc", "decimal", "decode", "expr", "machine", "primitives")

# Stable identity: survives reordering of files; shifts only when the
# compiler renumbers branch_id on that source line (source edit).
def arc_id(file: str, line: int, branch_id: int) -> str:
    stem = file if file.endswith(".c") else f"{file}.c"
    if stem.startswith("core/"):
        stem = stem[5:]
    return f"{stem}:{line}:b{branch_id}"


def ensure_gcov(stems: tuple[str, ...] = CORE_STEMS) -> None:
    for stem in stems:
        cfile = CORE / f"{stem}.c"
        if not cfile.is_file():
            continue
        gcno = BUILD / f"{stem}.gcno"
        if not gcno.is_file():
            # legacy Apple single-link notes
            alts = list(BUILD.glob(f"*-{stem}.gcno"))
            if not alts:
                continue
            gcno = alts[0]
        subprocess.run(
            ["gcov", "-b", "-o", str(gcno), str(cfile)],
            cwd=str(CROOT),
            capture_output=True,
            text=True,
        )


def parse_gcov_file(gcov_path: Path) -> list[dict]:
    """Parse one .gcov file into every branch arc (taken and missing)."""
    if not gcov_path.is_file():
        return []
    text = gcov_path.read_text(encoding="utf-8", errors="replace")
    file_stem = gcov_path.name.replace(".gcov", "")
    if not file_stem.endswith(".c"):
        file_stem = f"{file_stem}.c"
    arcs: list[dict] = []
    current_src_line = 0
    current_expr = ""
    for ln in text.splitlines():
        m = re.match(r"^\s*([#\d\-]+):\s*(\d+):(.*)$", ln)
        if m:
            current_src_line = int(m.group(2))
            current_expr = m.group(3).strip()
            continue
        bm = re.match(
            r"^\s*branch\s+(\d+)\s+(taken\s+(\d+)%|never executed)(.*)$",
            ln,
            re.I,
        )
        if not bm or current_src_line <= 0:
            continue
        bid = int(bm.group(1))
        never = "never" in bm.group(2).lower()
        pct = 0 if never else int(bm.group(3) or 0)
        taken = (not never) and pct > 0
        aid = arc_id(file_stem, current_src_line, bid)
        arcs.append(
            {
                "file": file_stem,
                "line": current_src_line,
                "branch_id": bid,
                "arc_id": aid,
                "key": aid,
                "taken": taken,
                "never": never,
                "pct": pct,
                "expression": current_expr[:160],
                "missing_arc": (
                    None
                    if taken
                    else ("never-executed" if never else "taken-0%")
                ),
            }
        )
    return arcs


def collect_core_arcs(stems: tuple[str, ...] = CORE_STEMS) -> list[dict]:
    """All branch arcs for core stems (after ensure_gcov)."""
    ensure_gcov(stems)
    arcs: list[dict] = []
    for stem in stems:
        gcov = CROOT / f"{stem}.c.gcov"
        arcs.extend(parse_gcov_file(gcov))
    return arcs


def summarize_arcs(arcs: list[dict]) -> dict:
    total = len(arcs)
    hit = sum(1 for a in arcs if a["taken"])
    missing = [a for a in arcs if not a["taken"]]
    by_file: dict[str, dict] = {}
    for a in arcs:
        f = a["file"]
        slot = by_file.setdefault(
            f, {"branches_hit": 0, "branches_total": 0, "missing_arcs": 0}
        )
        slot["branches_total"] += 1
        if a["taken"]:
            slot["branches_hit"] += 1
        else:
            slot["missing_arcs"] += 1
    return {
        "branches_hit": hit,
        "branches_total": total,
        "missing_arcs_measured": total - hit,
        "missing": missing,
        "by_file": by_file,
    }
