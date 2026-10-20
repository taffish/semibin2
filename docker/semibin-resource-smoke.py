#!/opt/conda/bin/python
"""Offline synthetic resource and upstream URL-regression tests, never production data."""
import copy
import hashlib
import io
import importlib.machinery
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import tempfile


def run(stage, argv, fail=False, marker=None):
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, timeout=240)
    if (result.returncode == 0) == fail or (marker is not None and marker not in result.stdout):
        print(f'semibin-resource-smoke: stage={stage} exit={result.returncode}', file=sys.stderr)
        print(result.stdout[-16000:], file=sys.stderr)
        raise SystemExit(result.returncode if result.returncode > 0 else 1)
    return result.stdout


def fixture(directory):
    directory.mkdir()
    (directory / 'reference.fa').write_text('>synthetic_protein\n' + 'MKWVTFISLLFLFSSAYSRGVFRRDTHKSEIAHRFKDLGE' * 4 + '\n')
    run('fixture', ['mmseqs', 'createdb', str(directory / 'reference.fa'), str(directory / 'GTDB'), '--dbtype', '1'])
    with tarfile.open(directory / 'synthetic.tgz', 'w:gz') as archive:
        for path in sorted(directory.glob('GTDB*')):
            archive.add(path, arcname=path.name)
    (directory / 'LICENSE.txt').write_text('Wholly synthetic technical fixture; CC0-1.0. No scientific validation.\n')
    recipe = run('pin', ['semibin-db', 'pin', '--archive', str(directory / 'synthetic.tgz'),
                        '--url', 'https://example.invalid/synthetic-1.tgz', '--id', 'synthetic',
                        '--resource-version', '1', '--license-file', str(directory / 'LICENSE.txt'),
                        '--rights-reviewed'])
    (directory / 'recipe.json').write_text(recipe)
    return json.loads(recipe)


def resources():
    source = Path.cwd() / 'source'
    recipe = fixture(source)
    root = Path.cwd() / 'resources'; root.mkdir(mode=0o755)
    install = ['semibin-db', 'install', '--recipe', str(source / 'recipe.json'),
               '--db-root', str(root), '--source-dir', str(source), '--reserve-gb', '0', '--rights-reviewed']
    run('dry-run', install + ['--dry-run'], marker='synthetic--1')
    official = json.loads(run('official-preview', ['semibin-db', 'install', '--gtdb-v95',
        '--db-root', str(root), '--rights-reviewed', '--dry-run']))
    assert official['download_bytes'] == 24044444399
    assert 'CC-BY-4.0' in official['recipe']['license'] and 'MD5 only' in official['recipe']['license']
    assert official['resource'] == 'gtdb--95' and len(official['recipe_sha256']) == 64
    assert not list(root.iterdir())
    # Missing, empty, nonempty and complete partial files can recover; corrupt, oversized or symlinked files must fail closed.
    archive_bytes = (source / recipe['files'][0]['name']).read_bytes()
    digest = recipe['files'][0]['sha256']
    for label, prefix in [('empty', b''), ('prefix', archive_bytes[:17]),
                          ('complete', archive_bytes), ('corrupt', b'BAD'),
                          ('oversize', archive_bytes+b'X'), ('symlink', None)]:
        scratch = Path.cwd() / ('partial-'+label); scratch.mkdir(mode=0o755)
        cache = scratch / '.downloads'; cache.mkdir(mode=0o700)
        old = scratch / 'unrelated-old'; old.mkdir(); (old / 'sentinel').write_bytes(b'KEEP')
        partial = cache / (digest+'.part')
        if label == 'symlink': partial.symlink_to(old / 'sentinel')
        else: partial.write_bytes(prefix)
        attempt = install.copy(); attempt[attempt.index('--db-root')+1] = str(scratch)
        reject = label in ('corrupt','oversize','symlink')
        before = partial.read_bytes()
        run('partial-'+label, attempt, fail=reject)
        if reject:
            assert partial.read_bytes() == before and not (scratch / 'synthetic--1').exists()
        else:
            run('partial-'+label+'-idempotent', attempt, marker='already complete:')
            run('partial-'+label+'-verify', ['semibin-db','verify','--db-root',str(scratch),'--id','synthetic--1'])
        assert (old / 'sentinel').read_bytes() == b'KEEP'
        assert not (scratch / '.install.lock').exists() and not list(scratch.glob('.*.stage-*'))
    run('install', install, marker='installed:')
    member = root / 'synthetic--1'
    identity = (member / 'READY').read_bytes()
    run('idempotent', install, marker='already complete:')
    assert (member / 'READY').read_bytes() == identity
    # Exercise the official MD5-only/flat-GTDB branch with an independent synthetic catalog; never access the 24 GB resource.
    sys.path.insert(0, '/usr/local/bin')
    helper = importlib.machinery.SourceFileLoader('resource_fixture', '/usr/local/bin/semibin-db').load_module()
    synthetic_catalog = copy.deepcopy(recipe)
    item = synthetic_catalog['files'][0]
    item['md5'] = hashlib.md5((source / item['name']).read_bytes()).hexdigest()
    del item['sha256']
    item['extract'] = 'flat-GTDB'
    helper.GTDB95 = synthetic_catalog
    helper.recipe_validate(synthetic_catalog)
    md5root = Path.cwd() / 'md5-only'; md5root.mkdir(mode=0o755)
    helper.install(md5root, synthetic_catalog, source, 0)
    md5record = helper.verify(md5root / 'synthetic--1', 'synthetic--1')
    assert md5record['archives'][0]['source_verification'] == 'upstream-md5-only'
    assert md5record['archives'][0]['sha256'] == recipe['files'][0]['sha256']
    helper.install(md5root, synthetic_catalog, source, 0)
    verify = ['semibin-db', 'verify', '--db-root', str(root), '--id', 'synthetic--1']
    record = json.loads(run('verify', verify))
    assert len(record['files']) >= 5 and not list(root.glob('*.stage-*'))
    assert len(json.loads(run('list', ['semibin-db', 'list', '--db-root', str(root)]))) == 1
    run('installed-read', ['mmseqs', 'convert2fasta', str(member / 'GTDB'), 'shared.fa'])
    assert '>synthetic_protein' in Path('shared.fa').read_text()
    import logging
    from SemiBin.gtdb import find_or_download_gtdb
    assert find_or_download_gtdb(logging.getLogger(), str(member), False) == str(member / 'GTDB')
    # Explicit second selection; no automatic fallback to another member.
    recipe2 = copy.deepcopy(recipe); recipe2['id'] = 'second'
    (source / 'second.json').write_text(json.dumps(recipe2))
    second = install.copy(); second[second.index('--recipe') + 1] = str(source / 'second.json')
    run('second-member', second, marker='installed:')
    assert len(json.loads(run('partial-inventory', ['semibin-db', 'list', '--db-root', str(root)]))) == 2
    bad = copy.deepcopy(recipe); bad['id'] = 'bad'; bad['files'][0]['sha256'] = '0' * 64
    (source / 'bad.json').write_text(json.dumps(bad))
    wrong = install.copy(); wrong[wrong.index('--recipe') + 1] = str(source / 'bad.json')
    run('checksum-rejected', wrong, fail=True, marker='checksum/size mismatch')
    assert not (root / 'bad--1').exists() and not (root / '.install.lock').exists()
    (root / '.install.lock').mkdir()
    run('lock-rejected', wrong, fail=True, marker='install lock exists')
    (root / '.install.lock').rmdir()
    for name, body in [('GTDB', b'X'), ('extra', b'X')]:
        path = member / name
        original = path.read_bytes() if path.exists() else None
        path.write_bytes(body)
        run('inventory-rejected-' + name, verify, fail=True)
        run('no-overwrite-' + name, install, fail=True)
        if original is None: path.unlink()
        else: path.write_bytes(original)
    (member / 'GTDB.dbtype').chmod(0o666)
    run('permission-rejected', verify, fail=True, marker='permission drift')
    (member / 'GTDB.dbtype').chmod(0o644)
    run('restored', verify)
    broken = root / 'broken--1'
    broken.symlink_to(root / 'missing')
    badlink = copy.deepcopy(recipe); badlink['id'] = 'broken'
    (source / 'broken.json').write_text(json.dumps(badlink))
    attempt = install.copy(); attempt[attempt.index('--recipe') + 1] = str(source / 'broken.json')
    run('broken-member-preserved', attempt, fail=True)
    assert broken.is_symlink() and not broken.exists()
    # Validate selected tar members without ever extractall-ing untrusted paths.
    for kind in ('symlink', 'duplicate', 'traversal'):
        archive_path = source / (kind + '.tgz')
        with tarfile.open(archive_path, 'w:gz') as archive:
            for name in ('GTDB', 'GTDB.index', 'GTDB.dbtype'):
                item = tarfile.TarInfo(name)
                item.size = 1
                if name == 'GTDB.dbtype' and kind == 'symlink':
                    item.type = tarfile.SYMTYPE; item.linkname = '/etc/passwd'; item.size = 0
                if name == 'GTDB.dbtype' and kind == 'traversal': item.name = '../GTDB.dbtype'
                archive.addfile(item, io.BytesIO(b'X'))
                if name == 'GTDB.dbtype' and kind == 'duplicate': archive.addfile(item, io.BytesIO(b'X'))
        run('pin-reject-' + kind, ['semibin-db', 'pin', '--archive', str(archive_path),
            '--url', 'https://example.invalid/bad.tgz', '--id', kind, '--resource-version', '1',
            '--license-file', str(source / 'LICENSE.txt'), '--rights-reviewed'], fail=True)


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'resources'
    try:
        with tempfile.TemporaryDirectory(prefix='taf-semibin-resource-') as scratch:
            os.chdir(scratch)
            {'resources': resources}[mode]()
        print('semibin-resource-smoke: stage=' + mode + ' PASS')
    except Exception as error:
        print(f'semibin-resource-smoke: stage={mode} exit=1: {error}', file=sys.stderr)
        raise
