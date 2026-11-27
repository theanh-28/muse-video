"""Portable advisory locks for the local Studio's single-writer transactions."""
from __future__ import annotations

import os
import threading
from pathlib import Path


class ProcessLockError(RuntimeError):
    pass


class ProcessFileLock:
    """A re-entrant per-process wrapper around an OS-released advisory lock."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._thread_lock = threading.RLock()
        self._owner: int | None = None
        self._depth = 0
        self._handle = None

    def __enter__(self) -> "ProcessFileLock":
        self._thread_lock.acquire()
        owner = threading.get_ident()
        if self._owner == owner:
            self._depth += 1
            return self
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle = self.path.open("a+b")
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            self._lock_handle(handle)
        except Exception:
            self._thread_lock.release()
            raise
        self._owner = owner
        self._depth = 1
        self._handle = handle
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._owner != threading.get_ident():
            self._thread_lock.release()
            raise RuntimeError("process lock released by a non-owner thread")
        self._depth -= 1
        if self._depth == 0:
            handle = self._handle
            self._owner = None
            self._handle = None
            try:
                if handle is not None:
                    self._unlock_handle(handle)
                    handle.close()
            finally:
                self._thread_lock.release()
        else:
            self._thread_lock.release()

    @staticmethod
    def _lock_handle(handle) -> None:
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ProcessLockError("Studio storage is already being modified by another process") from exc
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ProcessLockError("Studio storage is already being modified by another process") from exc

    @staticmethod
    def _unlock_handle(handle) -> None:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
