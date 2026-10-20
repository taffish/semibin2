#!/usr/bin/env python3
"""Offline positive and negative tests for license archives; not a substitute for metagenomic scientific validation."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('notices', Path(__file__).with_name('conda-licenses.py'))
notices = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notices)


class NoticeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.prefix, self.cache, self.output = root/'env', root/'pkgs', root/'notices'
        (self.prefix/'conda-meta').mkdir(parents=True)
        for name in ['semibin', 'python', 'pytorch', 'numpy', 'samtools', 'hmmer']:
            self.add_package(name, ['lib/'+name], True)
        self.add_package('metadata', [], False)

    def add_package(self, name, files, with_notice, license_name=None):
        identity = name+'-1.0-build0'
        info = self.cache/identity/'info'
        info.mkdir(parents=True)
        record = dict(name=name, version='1.0', build='build0', files=files)
        if license_name:
            record['license'] = license_name
        (info/'index.json').write_text(json.dumps(record))
        (self.prefix/'conda-meta'/(identity+'.json')).write_text(json.dumps(record))
        if with_notice:
            (info/'licenses').mkdir()
            (info/'licenses/COPYING').write_text('Copyright fixture; permission fixture.\n')

    def test_split_freetype_provider(self):
        self.add_package('freetype', ['lib/libfreetype.so'], True, 'GPL-2.0-only OR FTL')
        self.add_package('libfreetype6', ['lib/libfreetype.so.6'], False, 'GPL-2.0-only OR FTL')
        self.collect()
        notices.verify(self.output)
        inventory = json.loads((self.output/'inventory.json').read_text())
        consumer = next(p for p in inventory['packages'] if p['name']=='libfreetype6')
        self.assertEqual('freetype', consumer['notice_provider']['name'])

    def test_missing_freetype_provider_fails(self):
        self.add_package('libfreetype6', ['lib/libfreetype.so.6'], False, 'GPL-2.0-only OR FTL')
        with self.assertRaisesRegex(RuntimeError, 'FreeType notice provider missing'):
            self.collect()

    def test_gcc_exception_and_gpl(self):
        relative = 'share/licenses/gcc-libs/RUNTIME.LIBRARY.EXCEPTION'
        self.add_package('libgcc', [relative], False, 'GPL-3.0-only WITH GCC-exception-3.1')
        target = self.prefix/relative
        target.parent.mkdir(parents=True)
        target.write_text('Original GCC exception fixture\n')
        common = self.prefix/'common-licenses'
        common.mkdir()
        (common/'GPL-3').write_text('Full GPL fixture\n')
        with patch.object(notices, 'COMMON_LICENSES', common):
            self.collect()
        notices.verify(self.output)
        self.assertEqual('Full GPL fixture\n',
            (self.output/'libgcc-1.0-build0/supplementary/GPL-3').read_text())

    def test_sqlite_original_header_comment(self):
        self.add_package('libsqlite', ['include/sqlite3.h'], False, 'blessing')
        target = self.prefix/'include/sqlite3.h'
        target.parent.mkdir()
        original = b'/* The author disclaims copyright; here is a blessing. */'
        target.write_bytes(original + b'\nint example;\n')
        self.collect()
        self.assertEqual(original,
            (self.output/'libsqlite-1.0-build0/installed/sqlite3-header-notice.txt').read_bytes())

    def test_sqlite_unknown_header_fails(self):
        self.add_package('libsqlite', ['include/sqlite3.h'], False, 'blessing')
        target = self.prefix/'include/sqlite3.h'
        target.parent.mkdir()
        target.write_text('/* different license */')
        with self.assertRaisesRegex(RuntimeError, 'dedication missing'):
            self.collect()

    def test_python_licenses_module_is_not_a_notice_directory(self):
        relative = 'lib/python3.12/site-packages/packaging/licenses/__pycache__/__init__.pyc'
        self.add_package('packaging', [relative], True)
        target = self.prefix/relative
        target.parent.mkdir(parents=True)
        target.write_bytes(b'bytecode fixture')
        self.collect()
        self.assertFalse(list(self.output.rglob('*.pyc')))

    def collect(self):
        notices.collect(self.prefix, self.cache, self.output)

    def test_original_supplement_and_hash(self):
        self.add_package('supplement', ['bin/tool'], False)
        meta = self.prefix/'conda-meta/supplement-1.0-build0.json'
        record = json.loads(meta.read_text()); record['sha256'] = 'a' * 64
        meta.write_text(json.dumps(record))
        directory = self.prefix/'supplement'; directory.mkdir()
        content = b'Original permission fixture\n'
        (directory/'LICENSE').write_bytes(content)
        entry = {'supplement': {'package_sha256': 'a'*64, 'files': [dict(
            path='LICENSE', sha256=hashlib.sha256(content).hexdigest(), source='fixture://original')]}}
        (directory/'inventory.json').write_text(json.dumps(entry))
        with patch.object(notices, 'SUPPLEMENTARY', directory):
            self.collect()
        self.assertEqual(content, (self.output/'supplement-1.0-build0/upstream/LICENSE').read_bytes())

    def test_supplement_corruption_fails(self):
        self.add_package('supplement', ['bin/tool'], False)
        meta = self.prefix/'conda-meta/supplement-1.0-build0.json'
        record = json.loads(meta.read_text()); record['sha256'] = 'a' * 64
        meta.write_text(json.dumps(record))
        directory = self.prefix/'supplement'; directory.mkdir()
        (directory/'LICENSE').write_bytes(b'changed')
        (directory/'inventory.json').write_text(json.dumps({'supplement': {
            'package_sha256': 'a'*64, 'files': [dict(path='LICENSE', sha256='0'*64, source='fixture://original')]}}))
        with patch.object(notices, 'SUPPLEMENTARY', directory):
            with self.assertRaisesRegex(RuntimeError, 'source checksum mismatch'):
                self.collect()

    def test_complete_and_metadata_only(self):
        self.collect()
        notices.verify(self.output)
        inventory = json.loads((self.output/'inventory.json').read_text())
        self.assertEqual(7, len(inventory['packages']))
        self.assertEqual('metadata-only', next(p for p in inventory['packages'] if p['name']=='metadata')['status'])

    def test_no_overwrite(self):
        self.collect()
        with self.assertRaises(FileExistsError):
            self.collect()

    def test_unresolved_payload_fails(self):
        self.add_package('unresolved', ['lib/example.so'], False)
        with self.assertRaisesRegex(RuntimeError, 'notice review required'):
            self.collect()

    def test_missing_archived_notice_fails(self):
        self.collect()
        (self.output/'hmmer-1.0-build0/info/licenses/COPYING').unlink()
        with self.assertRaises(FileNotFoundError):
            notices.verify(self.output)

    def test_corrupt_archived_notice_fails(self):
        self.collect()
        (self.output/'hmmer-1.0-build0/info/licenses/COPYING').write_text('corrupt')
        with self.assertRaisesRegex(RuntimeError, 'integrity failed'):
            notices.verify(self.output)

    def test_inventory_escape_fails(self):
        self.collect()
        path = self.output/'inventory.json'
        data = json.loads(path.read_text())
        data['packages'][0]['files'][0]['path'] = '../outside'
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError, 'unsafe inventory path'):
            notices.verify(self.output)

    def test_cache_identity_mismatch_fails(self):
        path = self.cache/'numpy-1.0-build0/info/index.json'
        data = json.loads(path.read_text())
        data['version'] = '2.0'
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError, 'cache identity mismatch'):
            self.collect()


if __name__ == '__main__':
    unittest.main()
