# semibin2

`semibin2` packages SemiBin 2.5.0 for TAFFISH.

- command: `taf-semibin2`; kind: `tool`; package: `2.5.0-r1`
- packaging license: Apache-2.0; upstream software: MIT
- upstream: https://github.com/BigDataBiology/SemiBin
- immutable source: `v2.5.0`, commit `de1e77d8127d000f6898a27000d70feb1e94c2f0`

## What This App Packages

A thin automatic-command wrapper around `SemiBin2`, CPU PyTorch and its
runtime dependencies. The 2.5.0 change adds `keep_full_header=True` to the Python
`SemiBin.utils.concatenate_fasta` API; it does **not** add a CLI flag.
Normal CLI concatenation still emits sample-prefixed contig identifiers.

Runtime comes from the exact Bioconda package
`semibin=2.5.0=pyhdfd78af_0`, SHA256
`4a844e4acb739f2cc7ffa1a1b66122fe49569cda4ed7b824b810c263e476e24a`.
The official wheel has SHA256
`1527d37db23d96f00affe62fa1c72de0b1f39e195ab4c57f64b4f6327eb377bc`.
Every Conda dependency is fixed by URL/build and independently SHA256-verified.

## Scope

Supports default self-supervised binning, pretrained environments, single/coassembly
and multi-sample paths, sequence features, CPU model training, local trusted custom
models, concatenation and explicit upstream skill installation.

The legacy taxonomy path includes MMseqs2 17 (the upstream recommended major range)
and explicit GTDB preparation. FragGeneScan and Prodigal remain available for
optional ORF selection. Algorithms are unchanged. Only `SemiBin/gtdb.py` is adapted:
normal analysis never downloads, `download_GTDB` and destructive `--force` fail
with preparation instructions, and an existing selected database is used read-only.
The original module remains identifiable from the pinned upstream package.

This is not a GPU image. Official optional CUDA PyTorch is a separate installation,
not enabled by `--engine gpu` or a container runtime flag.
Official entry points/extras and installation documentation expose no in-package GUI.
ATLAS and Galaxy are separate workflow/service integrations, not a hidden local GUI.

## Container Contents

`SemiBin2`, Python 3.11, CPU PyTorch, NumPy, pandas, scikit-learn, python-igraph,
samtools, bedtools, HMMER, Prodigal, FragGeneScan, MMseqs2 and `semibin-db`.
The digest-pinned micromamba base is used for a two-stage build. Build caches,
headers, static libraries, sysroots, bytecode and non-runtime tests/docs are removed
only after original Conda notices are archived. Exact package inventories, original
notice files, hashes and split-package attribution live under
`/opt/semibin2/share/{doc,licenses}`. `conda-licenses.py verify` is read-only.

## Installation

Install TAFFISH and a working Docker, Podman, or Apptainer backend first.
Apptainer requires native x86_64 Linux for this app; see the backend matrix below
for platform and emulation boundaries.

After this release is published and available in the TAFFISH index, install the
exact package version and check its wrapper identity:

```sh
taf update
taf install semibin2 2.5.0-r1
taf-semibin2-v2.5.0-r1 --version
```

The versioned command identifies package `2.5.0-r1`. The unversioned
`taf-semibin2` alias follows the latest installed local version; use
`taf-semibin2-v2.5.0-r1` when this exact package is required.

## Usage and Command Mode

```sh
taf-semibin2 SemiBin2 single_easy_bin -i contigs.fa -b reads.sorted.bam -o result -p 8 --engine cpu
taf-semibin2 SemiBin2 single_easy_bin -i contigs.fa -b reads.sorted.bam -o result -p 8 --engine cpu --environment human_gut
taf-semibin2 -- --help
taf-semibin2 -- --version
taf-semibin2 samtools --version
```

Always include `SemiBin2` before an upstream subcommand: automatic command mode
would otherwise try to execute that subcommand as an executable.
Wrapper `--help` is the short operational manual; `--version` is package identity.
For an argument containing spaces use a preserved inner quote, e.g.
`-i "'input/contigs 1.fa'"`.

## Inputs and Output Notes

Contigs and coordinate-sorted BAM must refer to the same identifiers; for multi-sample
binning, concatenate first and map reads against that concatenated reference.
Abundance input is the upstream strobealign-aemb split-contig format, with at least
five samples. Training writes `model.pt`; feature generation writes `data.csv` and
`data_split.csv`; binning writes FASTA candidates under `output_bins/`.
Use new output directories. Tiny smoke outputs do not assess real MAG completeness,
contamination, biological interpretation or suitability of an environment model.

## Backend Usage and Capability Matrix

| Capability | Docker | Podman | Apptainer |
| --- | --- | --- | --- |
| Native Linux CPU | amd64 PASS, normal + read-only | amd64 PASS, normal + read-only | amd64 PASS, actual read-only SIF |
| ARM host | explicit amd64 emulation encoded in wrapper; not separately validated in this release | same | unsupported: use native x86_64 Linux or Docker/Podman |
| GPU | unsupported CPU runtime; use CPU or separate upstream CUDA environment | same | same |
| Shared DB/custom model | actual optional read-only bind | actual optional read-only bind | actual read-only bind into SIF |
| GUI | N/A, CLI package; Galaxy/ATLAS are separate services/workflows | same | same |

Use `TAFFISH_CONTAINER_BACKEND=docker|podman|apptainer` with the ordinary wrapper.
Apptainer requires Linux. See installed help for all three concrete bind commands.
Only `linux/amd64` is declared; no native ARM64 or ARM64-SIF promise is made.

## Resources, Databases, and Platform

### Bundled pretrained models

The exact upstream distribution includes twelve read-only models:
`built_environment`, `cat_gut`, `chicken_caecum`, `dog_gut`, `global`,
`human_gut`, `human_oral`, `mouse_gut`, `ocean`, `pig_gut`, `soil`,
`wastewater`. They are version-bound package resources, not a separate evolving
download family. Upstream distributes them with this MIT package; source training
datasets retain their own terms. The package is approximately 37 MB compressed,
including these weights. No model downloader or separate system installation is
needed: one administrator-provided image/SIF already permits all ordinary users
to read the same models without writing into the image. Choose an environment
explicitly and evaluate its scientific suitability.

User-trained weights and contigs/BAM/abundance files are project-specific inputs,
not a mechanically downloadable public database. For site reuse, an administrator
may place a trusted model at
`/usr/local/share/taffish/models/semibin2/PROJECT/model.pt` or
`/opt/taffish/models/semibin2/PROJECT/model.pt` (personal equivalent:
`~/.local/share/taffish/models/semibin2/PROJECT/model.pt`).
Keep version/provenance and a checksum alongside it, directories 0755 and files
0644, with administrator ownership; mount that root read-only and explicitly use
`--model /resources/PROJECT/model.pt`. Never load untrusted PyTorch model files.

### Legacy GTDB: fixed resource, explicit preparation

Default self-supervised and bundled-environment paths do not need GTDB.
Deprecated semi-supervised taxonomy can use upstream's MMseqs-formatted GTDB v95:
https://doi.org/10.5281/zenodo.4751564 (Shaojun Pan, 2021).
The record's registered terms are CC-BY-4.0; retain attribution/source and consider
the rights of any additional genomes you redistribute. No credentials are required.

Upstream supplies MD5 `4a70301c54104e87d5615e3f2383c8b5` for
`GTDB_v95.tar.gz`, but no independently published SHA256 inventory.
The first administrator acquisition must therefore be reviewed and pinned;
subsequent installs are mechanical, SHA256/size-verified and resumable.
This does not claim that a locally calculated SHA256 is upstream-authenticated.

```sh
# Explicit large first acquisition, in a new writable preparation directory.
curl -fL --retry 3 -C - -o GTDB_v95.tar.gz 'https://zenodo.org/record/4751564/files/GTDB_v95.tar.gz?download=1'
echo '4a70301c54104e87d5615e3f2383c8b5  GTDB_v95.tar.gz' | md5sum -c -
# RESOURCE_LICENSE.txt records author/title/DOI, CC-BY-4.0 URL and any site notes.
taf-semibin2 semibin-db pin --archive GTDB_v95.tar.gz --url 'https://zenodo.org/record/4751564/files/GTDB_v95.tar.gz?download=1' --id gtdb --resource-version 95 --license-file RESOURCE_LICENSE.txt --rights-reviewed > recipe.json
```

Review the fixed recipe; it lists exact archive size/SHA256 and all GTDB members.
The helper refuses links, traversal, duplicate members and unrelated files.
GTDB, GTDB.index and GTDB.dbtype are required, but this structural check is not a
production taxonomy certification. Use a new reviewed ID/version for custom sets.

Recommended roots:
`~/.local/share/taffish/databases/semibin2`,
`/usr/local/share/taffish/databases/semibin2`, or
`/opt/taffish/databases/semibin2`.
The resulting member is `gtdb--95/`.
An administrator creates the site root, owns it, and runs the same helper once
using a real writable bind; no automatic sudo/chown is performed.
Ordinary users need only read access and a read-only bind thereafter.
Site directory ownership is never changed by an ordinary user's invocation.

`semibin-db install --recipe recipe.json --db-root /db-install --rights-reviewed`
uses an installer-owned root (not group/world writable), private 0700 download
cache, an exclusive lock, resumable HTTPS, exact size/SHA256, staging, full member
inventory, READY hash and no-clobber promotion. Installed members are 0755/0644.
Repeat the same command to resume or verify an already complete installation.
Use `--source-dir DIR` for an offline archive import, `--dry-run` for a preview,
and `verify` / `list` for full read-only inventory checks.
A corrupt member is never overwritten; after confirming no installer is running,
an administrator may quarantine that exact member and rerun. Do not remove active
locks. Failed download partials remain private for inspection/retry.

Allow more than 100 GB for the full upstream resource plus compressed archive and
analysis workspace. `--reserve-gb` adds a free-space reserve (default 10 GiB);
the helper checks archive needs and each extraction member, but does not predict
the memory/disk cost of your subsequent taxonomy analysis. Exact download size is
recorded by the reviewed recipe, not a guessed fixed number here.

### Selection, overrides and write map

We deliberately use **explicit parameters plus a shared directory**, preserving
the thin wrapper and avoiding argv parsing or silent cross-root scientific selection.
There is no automatic host discovery/mount. The optional host root is overridden by
the user's backend bind, and `--reference-db DIRECTORY` selects the member.
For Python/library integrations, `TAFFISH_SEMIBIN_DB_DIR` is the fallback container
directory when no explicit argument is supplied; it does not create a host bind.
To disable sharing, unset the backend `TAFFISH_*_RUN_ARGS` and use project paths.
Missing members fail closed; no normal analysis path uses ephemeral downloads.

Temporary writes use unique `/tmp` directories. Analysis/training/skill outputs
must be user-selected writable work paths. Database setup uses only an actual
writable bind; shared DB/model reads require no root, network or write permission.
No Docker VOLUME or fake mount marker is used. Complete production GTDB download
and biological taxonomy validation are not part of this tiny engineering suite.

## Troubleshooting and Boundaries

- Missing database: check the actual backend bind and exact member directory;
  use `semibin-db verify`, not legacy `download_GTDB --force`.
- Small/short contigs may yield no bins; inspect length thresholds and upstream logs.
- GPU unavailable is expected in this CPU release, not cured by `--nv`/`--gpus`.
- Advanced `install-skills` writes only where requested; it does not install a GUI.
- The added full-header API option preserves the upstream implementation unchanged.

## Testing

The 2.5.0-r1 candidate passed native amd64 engineering validation on xjp;
this is a prepared candidate, not a claim of publication.
Smoke covers package identity, all main helps, 12-model real CPU inference, model
save/load, FASTA concatenation and full-header API, real BAM feature extraction,
one-epoch training, explicit skill installation, local GTDB policy, synthetic
MMseqs database preparation/reuse and negative resource/notice checks.
All 125 exact manifest checks passed independently in fresh offline Docker/Podman
normal/read-only containers and an actual same-OCI read-only SIF. All 93 real-wrapper
checks passed, including arguments with spaces, ordinary UID, actual writable/readonly
binds, custom-model reads and write denial. An administrator installed one root-owned
synthetic database; 20 permission/reuse checks and 16 exact cleanup checks passed.
Six HTTPS-resume/failure-log checks passed across three backends. Three additional
wrapper tests each ran trained and built-in model binning, including reclustering/HMMER,
and checked all four synthetic input contigs were preserved in outputs.
No complete production GTDB or biological MAG quality validation is claimed.
No backend exception is needed; native ARM and ARM-host emulation are not separately
validated for this candidate. The native-platform and supported-backend axes both pass.

Final image: 2,250,626,075 bytes (about 2.25 GB), dominated by CPU numerical libraries
and MMseqs runtime variants. Package download caches, headers/sysroots and static
libraries are excluded from the final copied runtime. Small upstream Easel reference
material remains with its packaged helper utilities; no required model/training data
is removed. The Conda notice inventory covers 137 packages and 300 original/supplementary
files, verified before pruning and again in each backend.

## License and Citation

TAFFISH packaging: Apache-2.0. SemiBin: MIT. Dependencies keep their original
licenses; full archived notices and their checksummed inventory are in the image.
FragGeneScan 1.32's original README says GNU GPL without a version, despite the
Bioconda BSD metadata label. The original README and full GPL-2/GPL-3 texts are
retained; we do not replace that declaration with a BSD notice. Corresponding
unmodified upstream source: https://downloads.sourceforge.net/project/fraggenescan/FragGeneScan1.32.tar.gz
(SHA256 54db8dab643f791aae7b05c310fe0d88ecb07db306211185c4c8524734f334c4).
GTDB resource attribution/terms are separate from the software license.

Cite SemiBin (Pan et al. 2022), DOI
https://doi.org/10.1038/s41467-022-29843-y, and SemiBin2 (Pan et al. 2023), DOI
https://doi.org/10.1093/bioinformatics/btad209, plus resources used.
