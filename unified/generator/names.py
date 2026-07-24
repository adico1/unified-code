"""Name validation for generated projects and features."""

from __future__ import annotations

import keyword
import re

PROJECT_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
FEATURE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")

RESERVED_FEATURES = frozenset(
    {
        "apply_features",
        "boundary",
        "compose",
        "core",
        "features",
        "host_render",
        "inward",
        "is_thing",
        "letter",
        "main",
        "outward",
        "parts",
        "program",
        "verify",
    }
)


def package_name_from_project(name: str) -> str:
    return name.replace("-", "_")


def is_valid_project_name(name: object) -> bool:
    if not isinstance(name, str) or not name:
        return False
    if not PROJECT_NAME_RE.fullmatch(name):
        return False
    package = package_name_from_project(name)
    if keyword.iskeyword(package):
        return False
    if not package.isidentifier():
        return False
    return True


def is_valid_feature_name(name: object) -> bool:
    if not isinstance(name, str) or not name:
        return False
    if not FEATURE_NAME_RE.fullmatch(name):
        return False
    if keyword.iskeyword(name):
        return False
    if name in RESERVED_FEATURES:
        return False
    if not name.isidentifier():
        return False
    return True
