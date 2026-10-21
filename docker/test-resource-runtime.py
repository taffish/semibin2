#!/usr/bin/env python3
"""Independent signal regression tests for directory/subprocess ownership windows; confined to private test directories."""
import importlib.machinery
import hashlib
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

source = Path(sys.argv.pop(1)) if len(sys.argv) > 1 else Path('/usr/local/bin')
sys.path.insert(0, str(source))
import semibin_runtime as runtime


class Ownership(unittest.TestCase):
    def setUp(self):
        self.previous = {s: signal.signal(s, runtime.interrupted) for s in runtime.SIGNALS}
        self.addCleanup(lambda: [signal.signal(s, h) for s, h in self.previous.items()])

    def test_child_creation_and_wait(self):
        real = subprocess.Popen
        for sig in runtime.SIGNALS:
            for phase in ('allocation', 'waiting'):
                children = []
                fired = False
                def inject():
                    nonlocal fired
                    if not fired:
                        fired = True
                        os.kill(os.getpid(), sig)
                def spawn(*args, **kwargs):
                    child = real(*args, **kwargs)
                    children.append(child)
                    if phase == 'allocation':
                        inject()
                    else:
                        wait = child.wait
                        def waiting(*a, **kw):
                            inject()
                            return wait(*a, **kw)
                        child.wait = waiting
                    return child
                with self.subTest(sig=sig, phase=phase), patch.object(subprocess, 'Popen', spawn):
                    with self.assertRaises(SystemExit) as result:
                        runtime.run_owned([sys.executable, '-c', 'import time; time.sleep(30)'])
                    self.assertEqual(result.exception.code, 128 + sig)
                    self.assertEqual(len(children), 1)
                    self.assertIsNotNone(children[0].poll())

    def test_early_directory(self):
        real = tempfile.mkdtemp
        for sig in runtime.SIGNALS:
            with tempfile.TemporaryDirectory() as root:
                def make(**kwargs):
                    path = real(**kwargs)
                    os.kill(os.getpid(), sig)
                    return path
                with patch.object(tempfile, 'mkdtemp', make), self.assertRaises(SystemExit) as result:
                    with runtime.private_directory(dir=root):
                        self.fail('signal ignored')
                self.assertEqual(result.exception.code, 128 + sig)
                self.assertEqual(list(Path(root).iterdir()), [])

    def test_early_lock_and_existing_lock(self):
        real = Path.mkdir
        for sig in runtime.SIGNALS:
            with tempfile.TemporaryDirectory() as root:
                lock = Path(root) / 'lock'
                def make(path, *args, **kwargs):
                    real(path, *args, **kwargs)
                    if path == lock:
                        os.kill(os.getpid(), sig)
                with patch.object(Path, 'mkdir', make), self.assertRaises(SystemExit) as result:
                    with runtime.owned_lock(lock):
                        self.fail('signal ignored')
                self.assertEqual(result.exception.code, 128 + sig)
                self.assertFalse(lock.exists())
                lock.mkdir()
                with self.assertRaises(FileExistsError):
                    with runtime.owned_lock(lock):
                        self.fail('stole another lock')
                self.assertTrue(lock.exists())

    def test_promotion_preserves_destination(self):
        for sig in runtime.SIGNALS:
            with tempfile.TemporaryDirectory() as root:
                root = Path(root)
                destination = root / 'old'
                destination.mkdir()
                (destination / 'sentinel').write_text('OLD')
                with self.assertRaises(SystemExit):
                    with runtime.private_directory(dir=root) as stage:
                        (stage / 'new').write_text('NEW')
                        os.kill(os.getpid(), sig)
                self.assertEqual((destination / 'sentinel').read_text(), 'OLD')
                self.assertEqual(list(root.iterdir()), [destination])
                with self.assertRaises(SystemExit):
                    with runtime.private_directory(dir=root) as stage:
                        (stage / 'new').write_text('NEW')
                        stage.rename(root / 'published')
                        os.kill(os.getpid(), sig)
                self.assertEqual((root / 'published/new').read_text(), 'NEW')

    def test_repeated_signals_during_cleanup(self):
        real_signal, real_rmtree = signal.signal, shutil.rmtree
        phases = ('before-install', 'between-install', 'cleanup',
                  'before-restore', 'between-restore', 'after-restore')
        for repeat in range(2):
            for phase in phases:
                for first in runtime.SIGNALS:
                    for second in runtime.SIGNALS:
                        with self.subTest(repeat=repeat, phase=phase, first=first, second=second):
                            with tempfile.TemporaryDirectory() as root:
                                root = Path(root)
                                lock = root / 'lock'
                                stage = None
                                armed, fired = False, False
                                handlers = {sig: signal.getsignal(sig) for sig in runtime.SIGNALS}
                                mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])

                                def inject():
                                    nonlocal fired
                                    if armed and not fired:
                                        fired = True
                                        os.kill(os.getpid(), second)

                                def change(signum, handler):
                                    installing = getattr(handler, '__name__', '') == 'remember'
                                    restoring = handler is runtime.interrupted
                                    if ((phase == 'before-install' and installing and signum == signal.SIGINT)
                                        or (phase == 'between-install' and installing and signum == signal.SIGTERM)
                                        or (phase == 'before-restore' and restoring and signum == signal.SIGINT)
                                        or (phase == 'between-restore' and restoring and signum == signal.SIGTERM)):
                                        inject()
                                    result = real_signal(signum, handler)
                                    if phase == 'after-restore' and restoring and signum == signal.SIGHUP:
                                        inject()
                                    return result

                                def remove(path, *args, **kwargs):
                                    if phase == 'cleanup' and Path(path) == stage:
                                        inject()
                                    return real_rmtree(path, *args, **kwargs)

                                try:
                                    with patch.object(signal, 'signal', change), patch.object(shutil, 'rmtree', remove):
                                        with self.assertRaises(SystemExit) as result:
                                            with runtime.owned_lock(lock):
                                                with runtime.private_directory(dir=root) as stage:
                                                    (stage / 'sentinel').write_text('ENGINEERING_SIGNAL_FIXTURE_ONLY')
                                                    armed = True
                                                    os.kill(os.getpid(), first)
                                    self.assertTrue(fired, 'second signal injection was not exercised')
                                    self.assertFalse(stage.exists(), 'second signal interrupted stage cleanup')
                                    self.assertFalse(lock.exists(), 'second signal interrupted lock cleanup')
                                    self.assertEqual(result.exception.code, 128 + first, 'first cancellation was replaced')
                                    self.assertEqual({sig: signal.getsignal(sig) for sig in runtime.SIGNALS}, handlers)
                                    self.assertEqual(signal.pthread_sigmask(signal.SIG_BLOCK, []), mask)
                                finally:
                                    for sig, handler in handlers.items():
                                        real_signal(sig, handler)
                                    signal.pthread_sigmask(signal.SIG_SETMASK, mask)

    def test_first_pending_or_new_signal_during_handler_restore(self):
        real_signal = signal.signal
        for phase in ('before-restore', 'between-restore', 'after-restore'):
            for first in (None, *runtime.SIGNALS):
                for second in runtime.SIGNALS:
                    with self.subTest(phase=phase, first=first, second=second):
                        armed, fired = False, False
                        handlers = {sig: signal.getsignal(sig) for sig in runtime.SIGNALS}
                        mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])

                        def change(signum, handler):
                            nonlocal fired
                            selected = {'before-restore': signal.SIGINT,
                                        'between-restore': signal.SIGTERM,
                                        'after-restore': signal.SIGHUP}[phase]
                            match = armed and not fired and signum == selected and handler is runtime.interrupted
                            if match and phase != 'after-restore':
                                fired = True
                                os.kill(os.getpid(), second)
                            result = real_signal(signum, handler)
                            if match and phase == 'after-restore':
                                fired = True
                                os.kill(os.getpid(), second)
                            return result

                        try:
                            with patch.object(signal, 'signal', change), self.assertRaises(SystemExit) as result:
                                with runtime.deferred_signals():
                                    if first is not None:
                                        os.kill(os.getpid(), first)
                                    armed = True
                            self.assertTrue(fired, 'restore signal injection was not exercised')
                            self.assertEqual(result.exception.code, 128 + (first if first is not None else second))
                            self.assertEqual({sig: signal.getsignal(sig) for sig in runtime.SIGNALS}, handlers)
                            self.assertEqual(signal.pthread_sigmask(signal.SIG_BLOCK, []), mask)
                        finally:
                            for sig, handler in handlers.items():
                                real_signal(sig, handler)
                            signal.pthread_sigmask(signal.SIG_SETMASK, mask)

    def test_signal_guard_is_not_sticky_or_general_exception_suppression(self):
        # Reuse this process after caught cancellations; unrelated errors are not cancellation state.
        for original in (None, ValueError('unrelated error'), SystemExit(7)):
            for sig in runtime.SIGNALS:
                with self.subTest(original=repr(original), sig=sig):
                    def deliver():
                        with self.assertRaises(SystemExit) as result:
                            os.kill(os.getpid(), sig)
                        self.assertEqual(result.exception.code, 128 + sig)
                    if original is None:
                        deliver()
                    else:
                        try:
                            raise original
                        except (ValueError, SystemExit):
                            deliver()
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, 'preserved error'):
                with runtime.private_directory(dir=root):
                    raise ValueError('preserved error')
            self.assertEqual(list(Path(root).iterdir()), [])
        for original in (ValueError('unrelated deferred error'), SystemExit(7)):
            for sig in runtime.SIGNALS:
                with self.subTest(deferred_original=repr(original), sig=sig):
                    with self.assertRaises(SystemExit) as result:
                        with runtime.deferred_signals():
                            os.kill(os.getpid(), sig)
                            raise original
                    self.assertEqual(result.exception.code, 128 + sig)

    def test_deferred_body_preserves_callers_signal_mask(self):
        previous = signal.pthread_sigmask(signal.SIG_BLOCK, [signal.SIGUSR1])
        expected = previous | {signal.SIGUSR1}
        try:
            with runtime.deferred_signals():
                self.assertEqual(signal.pthread_sigmask(signal.SIG_BLOCK, []), expected)
                child = subprocess.check_output([sys.executable, '-c',
                    'import signal; print(sorted(int(s) for s in signal.pthread_sigmask(signal.SIG_BLOCK, [])))'])
                self.assertEqual(child.decode().strip(), str(sorted(int(s) for s in expected)))
            self.assertEqual(signal.pthread_sigmask(signal.SIG_BLOCK, []), expected)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous)

    def test_offline_partial_variants(self):
        helper = source / ('semibin-db.py' if (source / 'semibin-db.py').exists() else 'semibin-db')
        module = importlib.machinery.SourceFileLoader('partial_subject', str(helper)).load_module()
        payload = b'synthetic engineering fixture, no biological data' * 20
        digest = hashlib.sha256(payload).hexdigest()
        item = dict(name='fixture.tgz', size=len(payload), sha256=digest)
        for case, prefix in [('missing', None), ('empty', b''), ('prefix', payload[:23]),
                             ('complete', payload), ('corrupt', b'X'), ('oversize', payload+b'X'),
                             ('symlink', b'')]:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                archive = root / 'fixture.tgz'; archive.write_bytes(payload)
                cache = root / 'cache'; cache.mkdir(mode=0o700)
                sentinel = cache / 'unrelated-old'; sentinel.write_bytes(b'KEEP')
                partial = cache / (digest+'.part')
                if case == 'symlink':
                    partial.symlink_to(sentinel)
                elif prefix is not None:
                    partial.write_bytes(prefix)
                if case in ('corrupt', 'oversize', 'symlink'):
                    before = partial.read_bytes()
                    with self.assertRaises(ValueError):
                        module.obtain(item, cache, root)
                    self.assertEqual(partial.read_bytes(), before)
                    self.assertFalse((cache / digest).exists())
                else:
                    result = module.obtain(item, cache, root)
                    self.assertEqual(result.read_bytes(), payload)
                    self.assertFalse(partial.exists())
                self.assertEqual(sentinel.read_bytes(), b'KEEP')
                self.assertEqual(archive.read_bytes(), payload)


if __name__ == '__main__':
    unittest.main()
