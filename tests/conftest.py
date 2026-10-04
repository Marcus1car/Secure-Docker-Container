import os
import stat

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def repo_root():
    return REPO_ROOT


@pytest.fixture
def samples_dir():
    return os.path.join(REPO_ROOT, "samples")


@pytest.fixture
def rules_path():
    """The real rule index, so these tests are a regression guard for B1."""
    return os.path.join(REPO_ROOT, "yara-rules", "index.yar")


@pytest.fixture
def whitelist_path():
    return os.path.join(REPO_ROOT, "config", "whitelist.json")


@pytest.fixture
def eicar_bytes():
    """The EICAR test string, assembled at runtime.

    Split so the literal signature never appears in a committed source file —
    an on-disk copy can be quarantined by a host antivirus before the test
    ever runs.
    """
    head = "X5O!P%@AP[4\\PZX54(P^)7CC)7}"
    tail = "$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    return (head + tail).encode()


@pytest.fixture
def make_script(tmp_path):
    """Write an executable /bin/sh script into tmp_path and return its path."""

    def _make(name, body):
        path = tmp_path / name
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return str(path)

    return _make
