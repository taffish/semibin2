#!/usr/bin/env python3
"""Preserve installed Conda notices before cache pruning; verify without writes."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

COMMON_LICENSES = Path('/usr/share/common-licenses')
SUPPLEMENTARY = Path('/tmp/upstream-notices')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(root, relative):
    rel = PurePosixPath(relative)
    require(not rel.is_absolute() and '..' not in rel.parts and rel.parts,
            f'unsafe inventory path: {relative}')
    path = root / relative
    require(path.resolve().is_relative_to(root.resolve()), f'escaping path: {relative}')
    return path


def collect(prefix, cache, root):
    metadata = sorted((prefix / 'conda-meta').glob('*.json'))
    require(metadata, 'installed Conda metadata is missing')
    root.mkdir(parents=True, exist_ok=False)
    packages = []
    for meta in metadata:
        record = json.loads(meta.read_text())
        name, version, build = (record[k] for k in ('name', 'version', 'build'))
        identity = f'{name}-{version}-{build}'
        require(re.fullmatch(r'[A-Za-z0-9_.+-]+', identity), 'unsafe package identity')
        package_sha256 = record.get('sha256')
        if not package_sha256:
            # micromamba 1.5 explicit MD5 installs do not fill record.sha256.
            # Independently hash the still-present original archive; the
            # Dockerfile also checks every archive against the committed SHA list.
            archives = [cache / (identity + suffix) for suffix in ('.conda', '.tar.bz2')]
            archives = [p for p in archives if p.is_file()]
            if archives:
                require(len(archives) == 1, 'ambiguous package archive: ' + identity)
                checksum = hashlib.sha256()
                with archives[0].open('rb') as stream:
                    for block in iter(lambda: stream.read(8 * 1024**2), b''):
                        checksum.update(block)
                package_sha256 = checksum.hexdigest()
        source = Path(record.get('link', {}).get('source', cache / identity))
        require(source.resolve().is_relative_to(cache.resolve()), f'cache escape: {identity}')
        info = source / 'info'
        require((info / 'index.json').is_file(), f'missing package info: {identity}')
        index = json.loads((info / 'index.json').read_text())
        require(all(index[k] == record[k] for k in ('name', 'version', 'build')),
                f'package cache identity mismatch: {identity}')
        about_path = info / 'about.json'
        about = json.loads(about_path.read_text()) if about_path.is_file() else {}
        copied = []

        def preserve(path, relative, origin, *, data=None, **provenance):
            data = path.read_bytes() if data is None else data
            require(data, f'empty notice: {identity}/{relative}')
            target = safe_path(root, f'{identity}/{relative}')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(0o644)
            copied.append(dict(path=str(target.relative_to(root)), origin=origin,
                               bytes=len(data), sha256=digest(data), **provenance))

        license_dir = info / 'licenses'
        if license_dir.is_dir():
            for path in sorted(license_dir.rglob('*')):
                if path.is_file():
                    require(path.resolve().is_relative_to(info.resolve()),
                            f'escaping package notice: {path}')
                    relative = 'info/licenses/' + str(path.relative_to(license_dir))
                    preserve(path, relative, 'package-info')
        # Preserve installed/vendored notices even if their parent test/doc is pruned.
        for relative in sorted(record.get('files', [])):
            if not re.search(r'(license|copying|copyright|notice)',
                             PurePosixPath(relative).name, re.I) and not relative.startswith('share/licenses/'):
                continue
            path = safe_path(prefix, relative)
            if path.is_file():
                preserve(path, 'installed/' + relative, 'installed-file')
        license_name = about.get('license', record.get('license'))
        # A few Bioconda packages omit their upstream notice payload. These
        # exact package identities receive original, independently hashed text.
        supplements = SUPPLEMENTARY / 'inventory.json'
        if not copied and supplements.is_file():
            entries = json.loads(supplements.read_text())
            if name in entries:
                entry = entries[name]
                require(package_sha256 == entry['package_sha256'],
                        'supplement package identity changed: ' + name)
                for notice in entry['files']:
                    original = safe_path(SUPPLEMENTARY, notice['path'])
                    require(digest(original.read_bytes()) == notice['sha256'],
                            'supplement source checksum mismatch: ' + name)
                    preserve(original, 'upstream/' + original.name, 'upstream-original',
                             source=notice['source'], source_sha256=notice['sha256'])
                if name == 'fraggenescan':
                    # The actual upstream 1.32 README says unversioned GNU GPL;
                    # Bioconda metadata says BSD. Preserve both facts, not a
                    # substituted BSD notice. Include full GPL texts.
                    for version in ('GPL-2', 'GPL-3'):
                        preserve(COMMON_LICENSES / version, 'supplementary/' + version,
                                 'debian-common-license', source='/usr/share/common-licenses/' + version)
        # GCC split runtimes ship their exception under share/licenses. Retain
        # the full GPL-3 text from the digest-pinned Debian builder as well.
        if name in {'libgcc', 'libgfortran5', 'libgomp', 'libstdcxx'}:
            require(license_name == 'GPL-3.0-only WITH GCC-exception-3.1',
                    f'GCC runtime license changed: {name}')
            require(any('RUNTIME.LIBRARY.EXCEPTION' in f['path'] for f in copied),
                    f'GCC runtime exception missing: {name}')
            preserve(COMMON_LICENSES / 'GPL-3', 'supplementary/GPL-3',
                     'debian-common-license', source='/usr/share/common-licenses/GPL-3')
        # SQLite's distributed header contains its original public-domain
        # dedication. Preserve the complete first comment before pruning SDKs.
        if name == 'libsqlite' and not copied:
            require(license_name == 'blessing', 'SQLite license changed')
            header = safe_path(prefix, 'include/sqlite3.h').read_bytes()
            require(header.startswith(b'/*') and b'*/' in header, 'SQLite header comment missing')
            notice = header[:header.index(b'*/') + 2]
            require(b'The author disclaims copyright' in notice and b'here is a blessing' in notice,
                    'SQLite public-domain dedication missing')
            preserve(None, 'installed/sqlite3-header-notice.txt', 'installed-header-comment',
                     data=notice, source='include/sqlite3.h', source_sha256=digest(header),
                     source_byte_range=[0, len(notice)])
        status = 'preserved' if copied else ('metadata-only' if not record.get('files') else 'unresolved')
        packages.append(dict(name=name, version=version, build=build,
            subdir=record.get('subdir'), url=record.get('url'),
            package_sha256=package_sha256, package_md5=record.get('md5'),
            license=license_name,
            upstream_license_note=('Original 1.32 README specifies GNU GPL without a version; '
                'Bioconda BSD label is not used as a replacement license.' if name == 'fraggenescan' else None),
            declared_license_files=about.get('license_file'),
            installed_file_count=len(record.get('files', [])), status=status, files=copied))
    # conda-forge distributes the FreeType notices in the matching freetype
    # output, while libfreetype6 contains only the shared library. Copy the
    # provider's original notices and record the exact installed identity.
    by_name = {p['name']: p for p in packages}
    consumer = by_name.get('libfreetype6')
    if consumer and consumer['status'] == 'unresolved':
        provider = by_name.get('freetype')
        require(provider and provider['status'] == 'preserved'
                and provider['version'] == consumer['version']
                and provider['license'] == consumer['license'],
                'matching FreeType notice provider missing')
        consumer['notice_provider'] = {k: provider[k] for k in ('name', 'version', 'build')}
        identity = '-'.join(consumer[k] for k in ('name', 'version', 'build'))
        for entry in provider['files']:
            if entry['origin'] != 'package-info':
                continue
            data = safe_path(root, entry['path']).read_bytes()
            relative = f'{identity}/shared/{entry["path"]}'
            target = safe_path(root, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(0o644)
            consumer['files'].append(dict(path=relative, origin='split-package-notice',
                provider_path=entry['path'], bytes=len(data), sha256=digest(data)))
        require(consumer['files'], 'FreeType provider has no original package notices')
        consumer['status'] = 'preserved'
    payload = dict(schema=1, packages=packages)
    (root / 'inventory.json').write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
    for directory in [root] + sorted(p for p in root.rglob('*') if p.is_dir()):
        directory.chmod(0o755)
    (root / 'inventory.json').chmod(0o644)
    unresolved = [p['name'] for p in packages if p['status'] == 'unresolved']
    require(not unresolved, 'notice review required: ' + ', '.join(unresolved))
    verify(root)


def verify(root):
    payload = json.loads((root / 'inventory.json').read_text())
    require(payload.get('schema') == 1, 'unsupported notice inventory schema')
    packages = payload['packages']
    require(packages and len({p['name'] for p in packages}) == len(packages),
            'missing or duplicate package inventory')
    names = {p['name'] for p in packages}
    require({'semibin', 'python', 'pytorch', 'numpy', 'samtools', 'hmmer'} <= names,
            'critical runtime package missing from notice inventory')
    checked = set()
    by_name = {p['name']: p for p in packages}
    for package in packages:
        files = package['files']
        if package['status'] == 'metadata-only':
            require(not files and package['installed_file_count'] == 0,
                    'metadata-only package has a payload')
        else:
            require(package['status'] == 'preserved' and files,
                    f'notice not preserved: {package["name"]}')
        provider_identity = package.get('notice_provider')
        if provider_identity:
            provider = by_name.get(provider_identity['name'])
            require(provider and all(provider[k] == provider_identity[k]
                    for k in ('name', 'version', 'build'))
                    and provider['version'] == package['version']
                    and provider['license'] == package['license'],
                    'notice provider identity mismatch')
        for entry in files:
            require(entry['path'] not in checked, 'duplicate notice path')
            checked.add(entry['path'])
            content = safe_path(root, entry['path']).read_bytes()
            require(len(content) == entry['bytes'] and digest(content) == entry['sha256'],
                    f'notice integrity failed: {entry["path"]}')
            if entry['origin'] == 'split-package-notice':
                require(provider_identity and any(
                    f['path'] == entry['provider_path'] and f['sha256'] == entry['sha256']
                    for f in provider['files']), 'split-package notice provenance mismatch')
    require(checked, 'empty notice archive')
    print(f'PASS conda-notices packages={len(packages)} files={len(checked)}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['collect', 'verify'])
    parser.add_argument('--prefix', type=Path, default=Path('/opt/conda'))
    parser.add_argument('--cache', type=Path, default=Path('/opt/conda/pkgs'))
    parser.add_argument('--root', type=Path, default=Path('/opt/semibin2/share/licenses/conda'))
    args = parser.parse_args()
    if args.mode == 'collect':
        collect(args.prefix, args.cache, args.root)
    else:
        verify(args.root)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        print(f'conda-notices: {error}', file=sys.stderr, flush=True)
        raise SystemExit(1)
