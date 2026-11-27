from __future__ import annotations

import pytest

from animation_studio.storage.locking import ProcessFileLock, ProcessLockError


def test_second_writer_is_rejected_while_the_first_lock_is_held(tmp_path):
    path = tmp_path / "studio.lock"
    first = ProcessFileLock(path)
    second = ProcessFileLock(path)
    with first:
        with pytest.raises(ProcessLockError):
            with second:
                pass
    with second:
        pass
