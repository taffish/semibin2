#!/opt/conda/bin/python
"""离线工程 smoke：小型合成数据，不代表 MAG 科学正确性验收。"""
import gzip
import importlib.metadata as md
import logging
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile


def run(*argv, fail=False, marker=None):
    r = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=150)
    if (r.returncode == 0) == fail or (marker and marker not in r.stdout):
        raise RuntimeError(f'{argv}: exit={r.returncode}\n{r.stdout[-12000:]}')
    return r.stdout


def core():
    import SemiBin, numpy, pandas, sklearn, igraph, requests, safetensors, tqdm, numexpr, torch
    assert md.version('SemiBin') == '2.5.0'
    assert torch.version.cuda is None, 'This release is explicitly CPU-only'
    assert run('SemiBin2', '--version').strip() == '2.5.0'
    for sub in ('single_easy_bin', 'multi_easy_bin', 'train_self', 'train_semi', 'bin',
                'generate_cannot_links', 'concatenate_fasta', 'install-skills'):
        assert sub in run('SemiBin2', '--help')
        run('SemiBin2', sub, '--help')
    run('SemiBin2', 'check_install', marker='Installation OK')
    # Stable text/file assertions only; no man, terminal-width or GUI rendering.
    Path('S1.fa').write_text('>c1 first description\n' + 'ACGT' * 400 + '\n')
    Path('S2.fa').write_text('>c2 second description\n' + 'TGCA' * 400 + '\n')
    run('SemiBin2', 'concatenate_fasta', '-i', 'S1.fa', 'S2.fa', '-o', 'concat')
    result = gzip.open('concat/concatenated.fa.gz', 'rt').read()
    assert result.count('>') == 2 and '>S1:c1\n' in result and 'description' not in result
    from SemiBin.utils import concatenate_fasta
    Path('full').mkdir()
    out = concatenate_fasta(['S1.fa'], 1000, 'full', ':', keep_full_header=True)
    assert '>S1:c1 first description\n' in Path(out).read_text()
    from SemiBin.gtdb import find_or_download_gtdb, download_GTDB_to
    for function, args in [(find_or_download_gtdb, (logging.getLogger(), '/missing', False)),
                           (find_or_download_gtdb, (logging.getLogger(), '/missing', True)),
                           (download_GTDB_to, (logging.getLogger(), '/missing'))]:
        try:
            function(*args)
        except RuntimeError:
            pass
        else:
            raise AssertionError('missing/forced GTDB must fail closed')


def models():
    import torch
    from SemiBin.utils import get_model_path
    from SemiBin.semi_supervised_model import model_load
    torch.set_num_threads(1)
    names = 'built_environment cat_gut chicken_caecum dog_gut global human_gut human_oral mouse_gut ocean pig_gut soil wastewater'.split()
    for name in names:
        model = model_load(get_model_path(name), torch.device('cpu')).eval()
        with torch.no_grad():
            y = model.embedding(torch.full((3, model.encoder1[0].in_features), 0.01))
        assert y.shape == (3, 100) and torch.isfinite(y).all(), name
    model.save_with_params_to('custom.pt')
    other = model_load('custom.pt', torch.device('cpu')).eval()
    with torch.no_grad():
        assert torch.equal(y, other.embedding(torch.full((3, other.encoder1[0].in_features), 0.01)))


def features():
    import pandas as pd
    import numpy as np
    import torch
    from SemiBin.semi_supervised_model import model_load
    rng = random.Random(250)
    seqs = {f'c{i}': ''.join(rng.choices('ACGT', k=6000)) for i in range(4)}
    Path('contigs.fa').write_text(''.join(f'>{name}\n{seq}\n' for name, seq in seqs.items()))
    sam = '@HD\tVN:1.6\tSO:coordinate\n' + ''.join(f'@SQ\tSN:{name}\tLN:6000\n' for name in seqs)
    for name, seq in seqs.items():
        for pos in range(1, 5800, 100):
            sam += f'r{name}_{pos}\t0\t{name}\t{pos}\t60\t100M\t*\t0\t0\t{seq[pos-1:pos+99]}\t' + 'I'*100 + '\n'
    Path('reads.sam').write_text(sam)
    run('samtools', 'view', '-b', '-o', 'reads.bam', 'reads.sam')
    run('SemiBin2', 'generate_sequence_features_single', '-i', 'contigs.fa', '-b', 'reads.bam',
        '-o', 'features', '--min-len', '1000', '--ml-threshold', '4000', '-p', '1')
    data = pd.read_csv('features/data.csv', index_col=0)
    split = pd.read_csv('features/data_split.csv', index_col=0)
    assert data.shape == (4, 138) and split.shape == (8, 136)
    assert np.isfinite(data.values).all() and np.isfinite(split.values).all()
    run('SemiBin2', 'train_self', '--data', 'features/data.csv', '--data-split', 'features/data_split.csv',
        '-o', 'trained', '--epochs', '1', '--batch-size', '1024', '--engine', 'cpu', '-p', '1')
    model = model_load('trained/model.pt', torch.device('cpu')).eval()
    with torch.no_grad():
        y = model.embedding(torch.tensor(data.values[:, :136], dtype=torch.float32))
    assert y.shape == (4, 100) and torch.isfinite(y).all()
    run('SemiBin2', 'update_model', '--model', 'trained/model.pt', '-o', 'roundtrip.pt')
    assert Path('roundtrip.pt').stat().st_size > 0


def skills():
    run('SemiBin2', 'install-skills', '--skills-dir', 'installed', marker='Installed 1 skill(s)')
    for name in ('SKILL.md', 'references/developer-guide.md', 'references/subcommands.md'):
        assert (Path('installed/semibin') / name).stat().st_size > 0
    assert not Path('.claude').exists()


def orfs():
    from SemiBin.orffinding import run_orffinder
    rng = random.Random(250)
    Path('genes.fa').write_text('>synthetic\nATG' + ''.join(rng.choices('ACGT', k=24000)) + 'TAA\n')
    for finder in ('fast-naive', 'prodigal', 'fraggenescan'):
        Path(finder).mkdir()
        result = Path(run_orffinder(str(Path('genes.fa').absolute()), 1,
                      str(Path(finder).absolute()), finder, None))
        assert result.is_file() and result.stat().st_size > 0, finder


if __name__ == '__main__':
    mode = sys.argv[1]
    with tempfile.TemporaryDirectory(prefix='taf-semibin-smoke-') as tmp:
        os.chdir(tmp)
        {'core': core, 'models': models, 'features': features, 'skills': skills, 'orfs': orfs}[mode]()
    print('PASS semibin-smoke ' + mode)
