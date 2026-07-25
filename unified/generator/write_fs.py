"""Filesystem write boundary for generation (L7).

Only this module performs host filesystem mutation for the generator.
Plans arrive as data; this part materializes them or fails without partial
project corruption.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from ..thing import is_thing


def write_project(thing):
    """Write a verified plan to disk through an explicit boundary."""
    if not is_thing(thing):
        return {
            "value": thing,
            "depths": (),
            "axes": (),
            "evidence": ("boundary:write_project", "write:rejected-non-thing"),
            "state": "invalid",
        }

    if thing["state"] != "valid":
        return {
            **thing,
            "evidence": (*thing["evidence"], "boundary:write_project", "write:refused-non-valid"),
            "state": thing["state"] if thing["state"] in {"invalid", "absent", "false", "unknown", "formed"} else "invalid",
        }

    value = thing["value"]
    if not isinstance(value, dict):
        return {
            **thing,
            "evidence": (*thing["evidence"], "boundary:write_project", "write:value-not-map"),
            "state": "invalid",
        }

    mode = value.get("write_mode")
    if mode == "create_project":
        return _write_create(thing, value)
    if mode == "update_project":
        return _write_update(thing, value)
    return {
        **thing,
        "evidence": (*thing["evidence"], "boundary:write_project", "write:unknown-mode"),
        "state": "invalid",
    }


def _write_create(thing, value):
    project_path = Path(value["project_path"])
    files = value["files"]

    if project_path.exists():
        return {
            **thing,
            "evidence": (*thing["evidence"], "boundary:write_project", "write:exists"),
            "state": "invalid",
        }

    parent = project_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = None
    try:
        tmp_dir = Path(tempfile.mkdtemp(prefix=".uc-new-", dir=str(parent)))
        for rel, content in files.items():
            target = tmp_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        _write_snapshot(tmp_dir, files)
        os.replace(tmp_dir, project_path)
        tmp_dir = None
    except OSError as exc:
        if tmp_dir is not None and tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        if project_path.exists() and not any(project_path.iterdir()):
            shutil.rmtree(project_path, ignore_errors=True)
        return {
            **thing,
            "evidence": (
                *thing["evidence"],
                "boundary:write_project",
                f"write:failed:{type(exc).__name__}",
            ),
            "state": "invalid",
        }

    written = tuple(sorted(files))
    return {
        **thing,
        "value": {
            **value,
            "written": written,
        },
        "evidence": (
            *thing["evidence"],
            "boundary:write_project",
            f"write:created:{len(written)}",
        ),
        "state": "valid",
    }


def _write_update(thing, value):
    project_path = Path(value["project_path"])
    files = value["files"]
    backups: dict[Path, str | None] = {}
    written_paths: list[str] = []
    baselines = value.get("file_baselines") or {}
    plan_mtimes = value.get("file_mtimes") or {}
    snapshot = _read_snapshot(project_path)

    # Refuse to overwrite manual edits or files newer than the plan snapshot.
    for rel, new_content in files.items():
        target = project_path / rel
        if not target.is_file():
            continue
        try:
            current = target.read_text(encoding="utf-8")
        except OSError as exc:
            return {
                **thing,
                "evidence": (
                    *thing["evidence"],
                    "boundary:write_project",
                    f"write:failed:{type(exc).__name__}",
                ),
                "state": "invalid",
            }
        baseline = baselines.get(rel)
        if baseline is not None and current != baseline and current != new_content:
            return {
                **thing,
                "evidence": (
                    *thing["evidence"],
                    "boundary:write_project",
                    "write:manual-edit-conflict",
                    f"write:conflict:{rel}",
                ),
                "state": "invalid",
            }
        # Snapshot-based manual edit: disk differs from last successful generation.
        if snapshot and rel in snapshot:
            import hashlib

            disk_hash = hashlib.sha256(current.encode("utf-8")).hexdigest()
            if disk_hash != snapshot[rel] and current != new_content:
                return {
                    **thing,
                    "evidence": (
                        *thing["evidence"],
                        "boundary:write_project",
                        "write:manual-edit-conflict",
                        f"write:conflict:{rel}",
                    ),
                    "state": "invalid",
                }
        expected_mtime = plan_mtimes.get(rel)
        if expected_mtime is not None:
            try:
                actual_mtime = target.stat().st_mtime_ns
            except OSError:
                actual_mtime = None
            if actual_mtime is not None and actual_mtime > expected_mtime:
                if baseline is None or current != baseline:
                    return {
                        **thing,
                        "evidence": (
                            *thing["evidence"],
                            "boundary:write_project",
                            "write:stale-plan",
                            f"write:stale:{rel}",
                        ),
                        "state": "invalid",
                    }

    try:
        for rel, content in files.items():
            target = project_path / rel
            if ".." in Path(rel).parts or Path(rel).is_absolute():
                raise ValueError("unsafe path")
            if target.exists():
                backups[target] = target.read_text(encoding="utf-8")
            else:
                backups[target] = None
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            written_paths.append(rel)
        # Merge snapshot for written files
        merged = dict(snapshot or {})
        import hashlib

        for rel, content in files.items():
            merged[rel] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        _write_snapshot(project_path, None, hashes=merged)
    except (OSError, ValueError) as exc:
        _restore_backups(backups)
        return {
            **thing,
            "evidence": (
                *thing["evidence"],
                "boundary:write_project",
                f"write:failed:{type(exc).__name__}",
                "write:rolled-back",
            ),
            "state": "invalid",
        }

    return {
        **thing,
        "value": {
            **value,
            "written": tuple(written_paths),
        },
        "evidence": (
            *thing["evidence"],
            "boundary:write_project",
            f"write:updated:{len(written_paths)}",
        ),
        "state": "valid",
    }


def _write_snapshot(project_path: Path, files: dict[str, str] | None, hashes: dict | None = None) -> None:
    import hashlib
    import json

    snap_dir = project_path / ".uc"
    snap_dir.mkdir(parents=True, exist_ok=True)
    if hashes is None:
        hashes = {
            rel: hashlib.sha256(content.encode("utf-8")).hexdigest()
            for rel, content in (files or {}).items()
        }
    (snap_dir / "snapshot.json").write_text(
        json.dumps({"files": hashes}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_snapshot(project_path: Path) -> dict[str, str] | None:
    import json

    path = project_path / ".uc" / "snapshot.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    files = data.get("files")
    if not isinstance(files, dict):
        return None
    return {str(k): str(v) for k, v in files.items()}


def _restore_backups(backups: dict[Path, str | None]) -> None:
    for path, content in backups.items():
        try:
            if content is None:
                if path.exists():
                    path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                # Use binary open so rollback is independent of Path.write_text
                # patches used in tests of the write boundary.
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)
        except OSError:
            continue
