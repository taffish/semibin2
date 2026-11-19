#!/opt/conda/bin/python
"""Explicit immutable GTDB/MMseqs resource recipes; no automatic selection."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
from semibin_runtime import SIGNALS, interrupted, owned_lock, private_directory, run_owned, deferred_signals

from semibin_validation import (SCHEMA, GTDB95, canonical, directory, recipe_load, recipe_validate,
                                regular, require, safe_name, sha, verify, verify_root)


def pin_archive(args):
    regular(args.archive)
    regular(args.license_file)
    require(args.license_file.stat().st_size <= 1024**2, 'license exceeds 1 MiB')
    # First acquisition is trust-on-first-use, NOT an upstream-authenticated hash.
    # The operator reviews source/rights before distributing this immutable recipe.
    selected = []
    with tarfile.open(args.archive, 'r:*') as archive:
        for member in archive:
            if member.isdir() and member.name in ('.', './'):
                continue
            safe_name(member.name)
            require(member.name.startswith('GTDB') and member.isfile() and not member.issparse(),
                    'expected flat regular GTDB members, no links or unrelated files')
            selected.append(member.name)
    recipe = recipe_validate(dict(schema=SCHEMA, id=args.id, version=args.resource_version,
        source=args.url, license=args.license_file.read_text(), files=[dict(name=args.archive.name,
        url=args.url, sha256=sha(args.archive), size=args.archive.stat().st_size, extract=selected)]))
    print(json.dumps(recipe, indent=2))




def command(stage, argv, cwd=None):
    # A disk-backed bounded diagnostic tail avoids storing large progress logs in RAM.
    with tempfile.TemporaryFile() as log:
        code = run_owned(argv, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
        if code:
            log.seek(max(0, log.tell() - 32768))
            print(f'semibin-db: stage={stage} exit={code}', file=sys.stderr)
            print('\n'.join(log.read().decode(errors='replace').splitlines()[-100:]), file=sys.stderr)
            raise SystemExit(code)


def obtain(item, cache, source_dir):
    algorithm = 'sha256' if 'sha256' in item else 'md5'
    checksum = item[algorithm]
    blob = cache / checksum
    partial = cache / (checksum + '.part')
    for path in (blob, partial):
        if os.path.lexists(path):
            regular(path)
    if blob.exists():
        require(blob.stat().st_size == item['size'] and sha(blob, algorithm) == checksum, 'corrupt cache; inspect exact file: ' + str(blob))
        return blob
    if source_dir is not None:
        source = source_dir / item['name']
        regular(source)
        # Interrupted offline imports also resume only after checking their prefix.
        partial_exists = partial.exists()
        offset = partial.stat().st_size if partial_exists else 0
        require(offset <= source.stat().st_size, 'oversize local partial')
        with source.open('rb') as inp:
            if offset:
                with partial.open('rb') as old:
                    for chunk in iter(lambda: old.read(8 * 1024**2), b''):
                        require(inp.read(len(chunk)) == chunk, 'corrupt local partial prefix')
            # An interrupted import may have created an empty regular file.
            # Existence, not length, chooses append versus exclusive creation.
            with partial.open('ab' if partial_exists else 'xb') as out:
                shutil.copyfileobj(inp, out, 8 * 1024**2)
    else:
        require(not partial.exists() or partial.stat().st_size <= item['size'], 'oversize partial cache')
        if not partial.exists() or partial.stat().st_size < item['size']:
            command('download', ['curl', '--fail', '--location', '--proto', '=https', '--proto-redir', '=https',
                                '--connect-timeout', '30', '--speed-limit', '1024', '--speed-time', '120',
                                '--retry', '3', '--retry-delay', '3', '--continue-at', '-',
                                '--max-filesize', str(item['size']), '--output', str(partial), item['url']])
    regular(partial)
    require(partial.stat().st_size == item['size'] and sha(partial, algorithm) == checksum,
            'download checksum/size mismatch; private partial retained: ' + str(partial))
    partial.chmod(0o600)
    partial.rename(blob)
    return blob


def install(root, recipe, source_dir, reserve):
    directory(root, writable=True)
    unit = recipe['id'] + '--' + recipe['version']
    identity = hashlib.sha256(canonical(recipe)).hexdigest()
    destination = root / unit
    if os.path.lexists(destination):
        records = verify_root(root)
        require(records[unit]['recipe_sha256'] == identity, 'existing ID has a different recipe; use a new version')
        print('already complete: ' + str(destination))
        return
    lock = root / '.install.lock'
    require(not os.path.lexists(lock), 'install lock exists; do not remove an active lock: ' + str(lock))
    with owned_lock(lock):
        require(unit not in verify_root(root, allow_empty=True), 'destination appeared; verify before retry')
        cache = root / '.downloads'
        if not os.path.lexists(cache):
            cache.mkdir(mode=0o700)
        directory(cache, writable=True)
        require(stat.S_IMODE(cache.stat().st_mode) == 0o700, 'cache must have mode 0700')
        pending = {}
        for item in recipe['files']:
            checksum = item.get('sha256', item.get('md5'))
            if not (cache / checksum).exists():
                pending[checksum] = item['size']
        # Conservative preflight; extraction is checked again per member. The
        # explicit extra reserve covers user-estimated makedb/taxonomy workspace.
        required = sum(pending.values()) + reserve
        require(shutil.disk_usage(root).free >= required, f'insufficient space: need {required} free bytes')
        blobs = [(item, obtain(item, cache, source_dir)) for item in recipe['files']]
        with private_directory(prefix='.' + unit + '.stage-', dir=root) as stage:
            for item, blob in blobs:
                with tarfile.open(blob, 'r:*') as archive:
                    all_members = archive.getmembers()
                    if item['extract'] == 'flat-GTDB':
                        members = [m.name for m in all_members if not (m.isdir() and m.name in ('.', './'))]
                        require(len(set(members)) == len(members), 'duplicate archive member')
                        for name in members:
                            safe_name(name)
                            require(name.startswith('GTDB'), 'unexpected non-GTDB archive member')
                    else:
                        members = item['extract']
                    for name in members:
                        matches = [m for m in all_members if m.name == name]
                        require(len(matches) == 1 and matches[0].isfile() and not matches[0].issparse(),
                                'missing/duplicate/non-regular database member')
                        require(shutil.disk_usage(stage).free >= matches[0].size + reserve, 'insufficient extraction space')
                        with archive.extractfile(matches[0]) as inp, (stage / name).open('xb') as out:
                            shutil.copyfileobj(inp, out, 8 * 1024**2)
            require(all((stage / name).is_file() for name in ('GTDB', 'GTDB.index', 'GTDB.dbtype')),
                    'required GTDB files missing')
            (stage / 'recipe.json').write_bytes(canonical(recipe) + b'\n')
            (stage / 'RESOURCE_LICENSE.txt').write_text(recipe['source'] + '\n\n' + recipe['license'] + '\n')
            inventory = [dict(name=p.name, size=p.stat().st_size, sha256=sha(p)) for p in sorted(stage.iterdir())]
            record = dict(schema='taffish.semibin.db.v1', app_release='2.6.1-r1', resource=unit,
                          recipe_sha256=identity, files=inventory,
                          archives=[dict(name=item['name'], sha256=sha(blob), size=blob.stat().st_size,
                              source_verification='sha256' if 'sha256' in item else 'upstream-md5-only')
                              for item, blob in blobs])
            (stage / 'manifest.json').write_bytes(canonical(record) + b'\n')
            (stage / 'READY').write_text(sha(stage / 'manifest.json') + '\n')
            for path in stage.iterdir():
                path.chmod(0o644)
            stage.chmod(0o755)
            verify(stage, unit, identity)
            command('promote', ['mv', '-T', '-n', '--', str(stage), str(destination)])
            require(not stage.exists(), 'destination appeared; refusing overwrite')
        # Delete only this recipe's verified private downloads after promotion.
        for blob in {blob for _, blob in blobs}:
            blob.unlink()
        print('installed: ' + str(destination))


def main():
    parser = argparse.ArgumentParser(description='Prepare one fixed database/taxonomy recipe. Analysis never downloads.',
        epilog='Use an existing installer-owned private/site root. Members: 0755/0644. No --force; '
        'quarantine exact damaged members only after confirming no installer is running. '
        'Repeat network installation to resume. Always use actual writable/read-only backend binds.')
    parser.add_argument('--version', action='version', version='semibin-db 2.6.1-r1')
    sub = parser.add_subparsers(dest='command', required=True)
    pin = sub.add_parser('pin', help='reviewed local archive to immutable recipe; no network')
    pin.add_argument('--archive', required=True, type=Path)
    pin.add_argument('--url', required=True)
    pin.add_argument('--id', required=True)
    pin.add_argument('--resource-version', required=True)
    pin.add_argument('--license-file', required=True, type=Path)
    pin.add_argument('--rights-reviewed', required=True, action='store_true')
    prepare = sub.add_parser('install')
    selector = prepare.add_mutually_exclusive_group(required=True)
    selector.add_argument('--recipe', type=Path)
    selector.add_argument('--gtdb-v95', action='store_true', help='fixed official 24 GB legacy GTDB v95; upstream MD5 only')
    prepare.add_argument('--db-root', required=True, type=Path)
    prepare.add_argument('--source-dir', type=Path, help='already acquired recipe members, no network')
    prepare.add_argument('--rights-reviewed', action='store_true', required=True,
                         help='confirm acquisition and intended sharing rights for every recipe member')
    prepare.add_argument('--dry-run', action='store_true')
    prepare.add_argument('--reserve-gb', type=float, default=10, help='extra free-space reserve, default 10 GiB')
    check = sub.add_parser('verify')
    check.add_argument('--db-root', required=True, type=Path)
    check.add_argument('--id', required=True, help='exact prepared member ID: recipe-id--version')
    inventory = sub.add_parser('list', help='verify every visible installed member; never select one automatically')
    inventory.add_argument('--db-root', required=True, type=Path)
    args = parser.parse_args()
    if args.command == 'pin':
        pin_archive(args)
        return
    require(args.db_root.is_absolute(), '--db-root must be absolute')
    if args.command == 'list':
        print(json.dumps(list(verify_root(args.db_root, allow_empty=True).values()), indent=2))
        return
    if args.command == 'verify':
        records = verify_root(args.db_root)
        require(safe_name(args.id) in records, 'selected member not installed: ' + args.id)
        print(json.dumps(records[args.id], indent=2))
        return
    require(0 <= args.reserve_gb < 1000000, 'invalid reserve')
    recipe = recipe_validate(GTDB95) if args.gtdb_v95 else recipe_load(args.recipe)
    if args.dry_run:
        print(json.dumps(dict(resource=recipe['id'] + '--' + recipe['version'], recipe=recipe,
            recipe_sha256=hashlib.sha256(canonical(recipe)).hexdigest(),
            download_bytes=sum(f['size'] for f in recipe['files']), reserve_bytes=int(args.reserve_gb * 1024**3),
            destination=str(args.db_root / (recipe['id'] + '--' + recipe['version'])),
            network=args.source_dir is None), indent=2))
        return
    install(args.db_root, recipe, args.source_dir, int(args.reserve_gb * 1024**3))


if __name__ == '__main__':
    for sig in SIGNALS:
        signal.signal(sig, interrupted)
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, tarfile.TarError) as error:
        print('semibin-db: stage=prepare-or-verify exit=1: ' + str(error), file=sys.stderr)
        sys.exit(1)
