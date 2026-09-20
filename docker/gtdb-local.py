"""TAFFISH storage-only adaptation: preserve local GTDB, prohibit implicit download.

The upstream analysis algorithms are unchanged. A complete database is prepared
explicitly with semibin-db; this module never writes to a shared database root.
"""
import os
from pathlib import Path


def download_GTDB_to(logger, GTDB_dir):
    raise RuntimeError('Implicit/legacy GTDB download is disabled in this image. '
                       'Use semibin-db install with a fixed recipe, then pass '
                       '--reference-db to the prepared member directory.')


def find_or_download_gtdb(logger, GTDB_reference_dir, force):
    if force:
        raise RuntimeError('Shared GTDB is immutable; --force is disabled. '
                           'Prepare a new resource version with semibin-db.')
    value = GTDB_reference_dir or os.environ.get('TAFFISH_SEMIBIN_DB_DIR')
    if not value:
        raise RuntimeError('GTDB not selected: pass --reference-db DIRECTORY '
                           'or TAFFISH_SEMIBIN_DB_DIR with an actual read-only bind.')
    root = Path(value)
    for name in ('GTDB', 'GTDB.index', 'GTDB.dbtype'):
        if not (root / name).is_file():
            raise RuntimeError(f'Missing GTDB member {root / name}; prepare the database '
                               'explicitly with semibin-db. No download was attempted.')
    logger.info(f'Using local read-only GTDB: {root}')
    return str(root / 'GTDB')
