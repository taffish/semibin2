# semibin2

`semibin2` packages [SemiBin](https://github.com/BigDataBiology/SemiBin) for TAFFISH.

Package identity:

- name: `semibin2`
- command: `taf-semibin2`
- kind: `tool`
- version: `2.3.0-r1`
- license: Apache-2.0 for TAFFISH packaging
- upstream: <https://github.com/BigDataBiology/SemiBin>

## What This App Packages

SemiBin2 is a metagenomic binning tool for reconstructing metagenome-assembled
genomes from contig assemblies plus abundance information. It uses
self-supervised and semi-supervised learning with sequence composition,
coverage/abundance, and built-in environment models.

This TAFFISH image installs SemiBin `2.3.0` from Bioconda, records the resolved
Conda package set, includes the upstream MIT license from the verified PyPI
source distribution, and exposes the upstream `SemiBin2` command directly.
Upstream SemiBin `2.3.0` ships only `SemiBin2`; the old `SemiBin1` command was
removed upstream.

## Scope

This app supports:

- `SemiBin2 single_easy_bin` for single-sample binning from contigs plus BAM or
  precomputed abundance
- `SemiBin2 multi_easy_bin` for multi-sample binning
- `SemiBin2 concatenate_fasta` for preparing combined multi-sample contig FASTA
- feature-generation and training subcommands provided by upstream SemiBin2
- `SemiBin2 check_install` for local runtime dependency checks
- bundled helper executables from Bioconda: `samtools`, `bedtools`, HMMER tools,
  and `prodigal`

This app does not:

- assemble reads, map reads, sort/index BAM files, or run MAG quality assessment
  for the user
- download or bundle large external databases
- provide a CUDA/GPU PyTorch runtime
- claim native `linux/arm64` support
- provide the removed upstream `SemiBin1` command

## Container Contents

- `SemiBin2`: main upstream CLI
- `python` / `python3`: Python runtime with SemiBin, PyTorch, NumPy, pandas,
  scikit-learn, igraph, safetensors, and related dependencies
- `samtools`: BAM/CRAM helper used by SemiBin workflows when needed
- `bedtools`: required upstream runtime dependency
- `hmmsearch`, `hmmscan`, `hmmpress`: HMMER commands used for marker workflows
- `prodigal`: optional upstream ORF finder when `--orf-finder prodigal` is used

The file `/opt/semibin2/share/doc/semibin2/conda-packages.txt` records the
exact Conda package set resolved during image build. `/opt/semibin2/share/doc/
semibin2/source.txt` records the upstream tag, runtime source, PyPI source
archive, SHA256, platform note, and CPU/GPU boundary.

## Usage

Access upstream help:

```sh
taf-semibin2 -- --help
taf-semibin2 -- --version
taf-semibin2 SemiBin2 single_easy_bin --help
taf-semibin2 SemiBin2 multi_easy_bin --help
taf-semibin2 SemiBin2 concatenate_fasta --help
```

Run single-sample binning with a sorted BAM:

```sh
taf-semibin2 SemiBin2 single_easy_bin \
  --environment human_gut \
  --input-fasta contigs.fa \
  --input-bam sample.sorted.bam \
  --output semibin2-single
```

Run single-sample binning from a precomputed abundance file:

```sh
taf-semibin2 SemiBin2 single_easy_bin \
  --environment human_gut \
  --input-fasta contigs.fa \
  --abundance sample_abundance.tsv \
  --output semibin2-single
```

Prepare a concatenated FASTA for multi-sample workflows:

```sh
taf-semibin2 SemiBin2 concatenate_fasta \
  --input-fasta S1.fa S2.fa S3.fa \
  --output semibin2-concat
```

Run multi-sample binning:

```sh
taf-semibin2 SemiBin2 multi_easy_bin \
  --environment global \
  --input-fasta semibin2-concat/concatenated.fa.gz \
  --input-bam S1.sorted.bam S2.sorted.bam S3.sorted.bam \
  --output semibin2-multi
```

For long-read or hybrid datasets, pass the upstream sequencing-type option:

```sh
taf-semibin2 SemiBin2 single_easy_bin \
  --sequencing-type long_read \
  --environment global \
  --input-fasta contigs.fa \
  --input-bam sample.sorted.bam \
  --output semibin2-long
```

## Command Mode

TAFFISH tool apps normally support automatic command mode. For non-option
leading commands, `taf-semibin2 SemiBin2 ...` runs the `SemiBin2` executable
inside the same container.

Use `taf-semibin2 -- --help` or `taf-semibin2 -- --version` when passing
option-leading arguments to the default upstream command.

SemiBin2 itself has subcommands. Prefer:

```sh
taf-semibin2 SemiBin2 single_easy_bin ...
taf-semibin2 SemiBin2 multi_easy_bin ...
taf-semibin2 SemiBin2 concatenate_fasta ...
```

Do not write `taf-semibin2 single_easy_bin ...`; `single_easy_bin` is not a
container executable.

## Inputs

| Input | Meaning | Notes |
| --- | --- | --- |
| `--input-fasta` / `-i` | assembled contig FASTA | plain or compressed forms accepted by upstream where supported |
| `--input-bam` / `-b` | sorted read-alignment BAM files | prepare outside this app with a mapper and samtools |
| `--abundance` / `-a` | precomputed abundance file | alternative to BAM input for supported subcommands |
| `--environment` | built-in SemiBin2 environment model | examples include `human_gut`, `ocean`, `soil`, `wastewater`, and `global` |
| `--sequencing-type` | data type | use upstream values such as `short_read` or `long_read`; `hybrid` is accepted upstream as a synonym for `long_read` in 2.3.0 |
| `--orf-finder` | ORF finder choice | default `fast-naive` does not need Prodigal; `prodigal` is bundled for users who request it |

## Output Notes

SemiBin2 writes output under the directory passed with `--output`. Typical
outputs include logs, intermediate features, bin assignment tables, and FASTA
bins under upstream-defined output directories such as `output_bins`. Exact
outputs depend on the selected subcommand, input mode, model choice, and whether
bins are produced for the dataset.

`SemiBin2 concatenate_fasta` writes `concatenated.fa.gz` in its output directory
for SemiBin `2.3.0` and renames contigs as
`<sample_name>:<original_contig_name>` by default.

## Resources, Databases, and Platform

No large external production database is bundled or downloaded at runtime. The
upstream SemiBin package includes its built-in pretrained environment model
assets; users provide assemblies, BAM files, abundance files, and optional
training data.

The image is declared as native `linux/amd64` only. `src/main.taf` requests
`--platform linux/amd64` for Docker and Podman, so Apple Silicon and other arm64
hosts can run it through container emulation when the backend supports that
mode. This is not native arm64 support.

The packaged runtime is CPU oriented. Upstream GPU execution requires a
CUDA-capable PyTorch build, GPU hardware, and backend-specific GPU runtime
options; use a custom image for that path.

## Boundaries

The smoke test is intentionally small and offline. It validates Python package
identity, core imports, SemiBin2 version/help, key subcommand help, upstream
`check_install`, and a tiny `concatenate_fasta` workflow. It does not train a
production neural model, run real metagenomic binning, benchmark bin quality,
or validate biological accuracy on real datasets.

For real analyses, prepare contigs and read-mapping/abundance inputs with
explicit upstream tools or TAFFISH flow steps before running SemiBin2. MAG
quality assessment and taxonomic annotation should be handled by separate tools
such as CheckM2/CheckM, GTDB-Tk, or other project-appropriate methods.

## Troubleshooting

- If `SemiBin2` reports missing or unsorted BAM input, sort and index BAM files
  with a mapper/samtools workflow before running SemiBin2.
- If a selected environment name is rejected, inspect `SemiBin2 single_easy_bin
  --help` or the upstream usage docs for the current list.
- If `--cuda` or GPU options fail, this image is expected to fail there because
  it is not a CUDA/GPU runtime.
- If running on an arm64 host, use Docker or Podman with amd64 emulation; this
  app is not published as native linux/arm64.

## Testing

The smoke test covers:

- SemiBin `2.3.0` package identity and import of core Python dependencies
- upstream `SemiBin2 --version`, top-level help, and major subcommand help
- `SemiBin2 check_install` against the packaged CPU runtime
- tiny synthetic `concatenate_fasta` execution and compressed output validation
- presence of helper executables including `samtools`, `bedtools`, HMMER, and
  `prodigal`

It does not replace full scientific validation on production datasets.

## License and Citation

TAFFISH app packaging: Apache-2.0.

SemiBin itself is distributed under the MIT license. Cite upstream SemiBin
according to upstream guidance. Key upstream publications include:

- SemiBin: <https://doi.org/10.1038/s41467-022-29843-y>
- SemiBin2: <https://doi.org/10.1093/bioinformatics/btad209>
