"""Packaging-layer process/directory ownership; upstream scientific logic is unchanged."""
from contextlib import contextmanager
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile

SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)


def interrupted(signum, frame):
    # A second cancellation must not interrupt ownership cleanup or replace the first exit status.
    active = sys.exc_info()[1]
    if isinstance(active, SystemExit) and active.code in {128 + sig for sig in SIGNALS}:
        return
    raise SystemExit(128 + signum)


@contextmanager
def deferred_signals():
    pending, previous = [], {}

    def remember(signum, frame):
        if not pending:
            pending.append(signum)

    def check():
        if pending:
            interrupted(pending[0], None)

    try:
        # Only handler transitions are masked; the body and spawned children retain the caller's mask.
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
        try:
            for sig in SIGNALS:
                previous[sig] = signal.signal(sig, remember)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        yield check
    finally:
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
        try:
            try:
                # Establish the first pending cancellation before restored handlers see another signal.
                check()
            finally:
                for sig, handler in previous.items():
                    signal.signal(sig, handler)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


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
def held_parent(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        yield fd
    finally:
        os.close(fd)


def remove_owned(parent, name, fd, recursive):
    """Only clean contents through the originally opened directory descriptor."""
    def original():
        try:
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return False  # An already promoted stage is intentionally left alone.
        if not os.path.samestat(current, os.fstat(fd)):
            raise ValueError('private transaction name changed; retained for inspection: ' + name)
        return True
    if not original():
        return
    if recursive:
        for entry in os.listdir(fd):
            mode = os.stat(entry, dir_fd=fd, follow_symlinks=False).st_mode
            if stat.S_ISDIR(mode):
                # Resource stages are flat. Preserve unexpected content for diagnosis.
                raise ValueError('unexpected subdirectory in private stage: ' + entry)
            os.unlink(entry, dir_fd=fd)
    if original():
        os.rmdir(name, dir_fd=parent)


@contextmanager
def owned_lock(path):
    with held_parent(path.parent) as parent:
        fd = None
        try:
            with deferred_signals():
                path.mkdir(mode=0o700)
                fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY, dir_fd=parent)
            yield
        finally:
            with deferred_signals():
                if fd is not None:
                    try:
                        remove_owned(parent, path.name, fd, False)
                    finally:
                        os.close(fd)


@contextmanager
def private_directory(**kwargs):
    with held_parent(kwargs['dir']) as parent:
        fd = None
        try:
            with deferred_signals():
                path = Path(tempfile.mkdtemp(**kwargs))
                fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY, dir_fd=parent)
            yield path
        finally:
            with deferred_signals():
                if fd is not None:
                    try:
                        remove_owned(parent, path.name, fd, True)
                    finally:
                        os.close(fd)
