"""Packaging-layer process/directory ownership; upstream scientific logic is unchanged."""
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile

SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)


def interrupted(signum, frame):
    raise SystemExit(128 + signum)


@contextmanager
def deferred_signals():
    pending, previous = [], {}

    def remember(signum, frame):
        if not pending:
            pending.append(signum)

    def check():
        if pending:
            raise SystemExit(128 + pending[0])

    try:
        for sig in SIGNALS:
            previous[sig] = signal.signal(sig, remember)
        yield check
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        check()


def run_owned(argv, **kwargs):
    # Record signals until Popen returns; handle them after acquiring the child to avoid leaving an unowned download process.
    with deferred_signals() as check:
        child = None
        try:
            child = subprocess.Popen(argv, start_new_session=True, **kwargs)
            while True:
                check()
                try:
                    rc = child.wait(timeout=0.1)
                    return rc if rc >= 0 else 128 - rc
                except subprocess.TimeoutExpired:
                    pass
        finally:
            if child is not None:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()


@contextmanager
def owned_lock(path):
    owned = False
    try:
        with deferred_signals():
            path.mkdir(mode=0o700)
            owned = True
        yield
    finally:
        with deferred_signals():
            if owned:
                path.rmdir()


@contextmanager
def private_directory(**kwargs):
    path = None
    try:
        with deferred_signals():
            path = Path(tempfile.mkdtemp(**kwargs))
        yield path
    finally:
        with deferred_signals():
            if path is not None and path.exists():
                shutil.rmtree(path)
