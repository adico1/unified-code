"""Repository-test storage boundary.

Pytest normally retains every ``tmp_path`` until the whole session finishes.
Generated application suites are large enough that this turns completed tests
into an unrelated disk requirement. Release only the current test's paths after
all of its assertions and teardown have completed.
"""

import shutil

import pytest


@pytest.fixture(autouse=True)
def release_completed_test_storage(request, tmp_path):
    yield
    parent = tmp_path.parent
    prefix = tmp_path.name
    for path in tuple(parent.iterdir()):
        if path.name == prefix or path.name.startswith(prefix + "-"):
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
