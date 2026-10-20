#!/usr/bin/env python3
"""Independent signal regression tests for directory/subprocess ownership windows; confined to private test directories."""
import importlib.machinery
import hashlib
import os
from pathlib import Path
import signal
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
