# semibin2

`semibin2` packages SemiBin 2.6.0 for TAFFISH.

- command: `taf-semibin2`; kind: `tool`; package: `2.6.0-r2`
- image: `ghcr.io/taffish/semibin2:2.6.0-r2`
- packaging license: Apache-2.0; upstream software: MIT
- upstream: https://github.com/BigDataBiology/SemiBin
- immutable source: `v2.6.0`, commit `851bbb2ee444b1df2d49f56c794ba731fda69327`

## What This App Packages

A thin automatic-command wrapper around `SemiBin2`, CPU PyTorch and its
runtime dependencies. Version 2.6.0 adds argcomplete/static shell completion,
the `check-install` alias and earlier diagnostics for invalid inputs or missing
external tools. Minimums are Python 3.11, pandas 3 and PyTorch 2.4. The existing
Python full-header API remains available; CLI concatenation still prefixes IDs.

Runtime comes from the exact Bioconda package
`semibin=2.6.0=pyhdfd78af_0`, SHA256
`fd66ea04d54db8bbee2db28bcc73fcc1e57c7bf3c79e9af2b0f512a244a14443`.
The official wheel has SHA256
`fd6667d9df602da1acf379bb067a4a78d035d18189ccea470d842b7d2677d342`
(official release digest; the runtime uses the separately verified Conda archive).
Every Conda dependency is fixed by URL/build and independently SHA256-verified.
Fixed digests/checksums detect changed bytes, not permanent retention: registry or
Conda artifacts may disappear, and Debian APT indexes can change. Dockerfile
comments identify these sources and the successor-release repair boundary.

### Packaging revision r2

This is a same-upstream packaging repair, not an algorithm or dependency
update. The public r1 image contained `/opt/semibin2/share/testdata` with mode
0644 after `COPY --chmod=0644`, preventing ordinary Apptainer users from traversing
the directory and opening its smoke scripts. r2 fixes directory traversal permissions
at build time while retaining ordinary-file modes.

Resource-runtime cancellation is also hardened to preserve the first INT/TERM/HUP
while cleaning owned directories. Pending cancellation is established before restoring
handlers; signal masking protects only handler transitions, not the long-running body
or child processes. `semibin-db --version` and
new resource manifests' `app_release` are synchronized to `2.6.0-r2`. Existing valid
r1 resource records remain verifiable and reusable without rewriting them.
The upstream commit, Conda lock and checksums, twelve models, scientific code and
scientific command/output interfaces remain unchanged. The canonical Action is not
modified. See Testing for the candidate validation and its boundaries.

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
The upstream NotebookLM documentation assistant is an external service, not a
container GUI or runtime dependency.

## Container Contents

`SemiBin2`, Python 3.11, CPU PyTorch, NumPy, pandas, scikit-learn, python-igraph,
samtools, bedtools, HMMER, Prodigal, FragGeneScan, MMseqs2, argcomplete, shtab and `semibin-db`.
The digest-pinned micromamba base is used for a two-stage build. Package caches,
top-level development headers/documentation, static libraries, sysroots, bytecode,
selected site-package tests and Conda installation-test payloads are removed only after
original Conda notices are archived. Package-internal interfaces and headers,
standard-library support/test modules and upstream reference resources are retained;
this is not a claim that all headers or test-named directories are absent.
Exact package inventories, original
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
taf install semibin2 2.6.0-r2
taf-semibin2-v2.6.0-r2 --version
```

The versioned command identifies package `2.6.0-r2`. The unversioned
`taf-semibin2` alias follows the latest installed local version; use
`taf-semibin2-v2.6.0-r2` when this exact package is required.

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
| Native Linux CPU | amd64; r2 candidate validated | amd64; rootless r2 candidate validated | amd64; same-OCI read-only SIF validated |
| ARM host | explicit amd64 emulation encoded in wrapper; not separately validated in this release | same | unsupported: use native x86_64 Linux or Docker/Podman |
| GPU | unsupported CPU runtime; use CPU or separate upstream CUDA environment | same | same |
| Shared DB/custom model | optional read-only bind; synthetic reuse validated | optional read-only bind; synthetic reuse validated | read-only bind into SIF; synthetic reuse validated |
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

The fixed Zenodo record supplies MD5 `4a70301c54104e87d5615e3f2383c8b5` and
24,044,444,399 compressed bytes for `GTDB_v95.tar.gz`, but no independent SHA256.
Use `semibin-db install --gtdb-v95 --db-root /db-install --rights-reviewed`
with the actual writable backend bind shown in help. This explicitly downloads
only v95, verifies the official size/MD5, validates flat regular GTDB tar members,
then records archive/member SHA256 and attribution in the installed inventory.
MD5 is a weaker upstream integrity check, not strong cryptographic provenance;
the newly calculated SHA256 is local provenance, not upstream authentication.
`--dry-run` shows the fixed identity, exact size, checksum and license without writes.

For a custom or independently reviewed archive, the stricter SHA256 recipe path
remains available. Example first acquisition/pinning (optional, not required by
the built-in v95 selector):

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
cache, an exclusive lock, resumable HTTPS, exact recipe size/checksum, staging, full member
inventory, READY hash and no-clobber promotion. Installed members are 0755/0644.
New manifests record `app_release: 2.6.0-r2`; an existing valid r1 member remains
verifiable and is reused idempotently without rewriting its manifest or contents.
Repeat the same command to resume or verify an already complete installation.
Use `--source-dir DIR` for an offline archive import, `--dry-run` for a preview,
and `verify` / `list` for full read-only inventory checks.
A corrupt member is never overwritten; after confirming no installer is running,
an administrator may quarantine that exact member and rerun. Do not remove active
locks. Failed download partials remain private for inspection/retry.
INT/TERM/HUP return 130/143/129, reap owned subprocesses before releasing the lock,
and remove only this attempt's unpublished staging directory. A completed promotion
is retained and verified on retry. Offline imports resume after checking the saved
prefix, including an empty partial left before the first byte was copied. Empty
regular partials resume without deleting old resources; corrupt/oversized partials
and symlinks remain rejected. SIGKILL/power loss may leave a lock/stage: verify no
installer is running,
preserve the exact failed attempt for diagnosis, and recover deliberately; never
delete an entire database root. Existing members, including broken symlinks, fail
closed rather than being overwritten. There is no destructive `--force` mode.

Allow more than 100 GB for the full upstream resource plus compressed archive and
analysis workspace. `--reserve-gb` adds a free-space reserve (default 10 GiB);
the helper checks archive needs and each extraction member, but does not predict
the memory/disk cost of your subsequent taxonomy analysis. Exact download size is
recorded by the reviewed recipe, not a guessed fixed number here.

### Selection, overrides and write map

The wrapper exposes a prepared database root read-only at `/resources/semibin2`.
Priority is `TAFFISH_SEMIBIN_DB_PATH`, then personal
`$HOME/.local/share/taffish/databases/semibin2`, then `/usr/local/share`, then
`/opt/taffish/databases/semibin2`. It resolves a root symlink to its physical path;
an invalid explicit root, broken high-priority link, empty or incomplete prepared
root fails closed, without silently selecting a lower-priority root. Colons/commas
in physical mount paths are rejected; paths with spaces are supported.
Preflight checks each visible member's required files and READY/manifest hash;
use `semibin-db verify` for full data SHA256 verification after transfer or suspected
corruption. Auto-mount is not a substitute for that potentially lengthy full scan.
No upstream argv is parsed, and no GTDB member is scientifically selected: pass
`--reference-db /resources/semibin2/gtdb--95` or another explicit prepared member.
Set `TAFFISH_SEMIBIN_DB_AUTO_MOUNT=0` for setup into an empty standard root, to
disable discovery, or to use the manual three-backend binds shown in help.
After setup, unset the switch to re-enable discovery. Absence of any candidate
means no optional mount; it does not mark GTDB as available.
For Python/library integrations, `TAFFISH_SEMIBIN_DB_DIR` is the fallback container
directory when no explicit argument is supplied; it does not create a host bind.
To disable manual sharing as well, unset the backend `TAFFISH_*_RUN_ARGS`.
Missing members fail closed; no normal analysis path uses ephemeral downloads.

Temporary writes use unique `/tmp` directories. Analysis/training/skill outputs
must be user-selected writable work paths. Database setup uses only an actual
writable bind; shared DB/model reads require no root, network or write permission.
No Docker VOLUME or fake mount marker is used. Project-trained models remain
explicitly selected user inputs, not part of automatic GTDB discovery.
Complete production GTDB download
and biological taxonomy validation are not part of this tiny engineering suite.

## Troubleshooting and Boundaries

- Missing database: check the actual backend bind and exact member directory;
  use `semibin-db verify`, not legacy `download_GTDB --force`.
- Small/short contigs may yield no bins; inspect length thresholds and upstream logs.
- GPU unavailable is expected in this CPU release, not cured by `--nv`/`--gpus`.
- Advanced `install-skills` writes only where requested; it does not install a GUI.
- Completion generators target the upstream `SemiBin2` command, not the two-word
  `taf-semibin2 SemiBin2` wrapper interface. They do not modify host shell startup.
  Generate a script explicitly with
  `taf-semibin2 shtab -u --shell=bash --prog=SemiBin2 SemiBin.main.semibin_arg_parser > SemiBin2.bash`.
  Use it only in a shell exposing the actual upstream command; regenerate on upgrades.

## Testing

The 2.6.0-r2 candidate was built and validated on native Linux amd64 using the
canonical app-root context, Buildx 0.38.0 and BuildKit 0.33.1 with its builtin
frontend. Builder semantics were aligned with the publishing Action; the local
Docker Engine and per-build resource limits were not identical to CI. The Action
itself remains byte-for-byte unchanged. Published-image digest and Index confirmation
are independent post-release checks, not implied by these candidate results.

The manifest retains 19 individual exist probes and 10 independent tests. The runner
adds one combined-exist check: 30 invocations per group, 210 successful invocations
across Docker and rootless Podman normal/read-only/non-root-read-only groups, and a
same-OCI actual read-only Apptainer SIF. Every command ran fresh and offline.
Coverage includes package identity, main helps,
12-model real CPU inference, model save/load, FASTA concatenation and full-header
API, real BAM feature extraction, one-epoch training, explicit skill installation,
local GTDB policy, synthetic MMseqs database preparation/reuse and negative
resource/notice checks. Three-backend permission regressions validated 1,210 paths,
their parent chains and ordinary-user reads with UID/GID 1001 and no effective
capabilities. A deliberately bad 0644 directory was rejected in each backend;
no runtime chmod of the installed tree, writable SIF or masking bind was used.

Real-wrapper regressions passed main paths, prepared-root discovery/override/
disable, trained/bundled-model synthetic binning, trusted legacy-model conversion,
actual writable/read-only binds and ordinary-user reuse of a private admin-owned
synthetic database. Resource tests passed failure-log visibility, HTTPS/offline
partial resume, externally signalled lock/stage/promotion/copy windows, cleanup,
old-member preservation, recovery and idempotence, including valid r1 resource records
reused without rewriting provenance. INT/TERM/HUP interruption passed at six installer
windows per backend (54 injected cases), including before promotion; exits and owned
stage/lock/child cleanup were checked. These are engine/process-group injections,
not PTY keyboard-interaction tests. The runtime's nine regression tests additionally
cover 108 repeated-signal and 36 restoration cases and passed in every direct group.

The 139-package lock, archived original notices, models and two-stage pruning are
retained. CPU numerical libraries and MMseqs dominate the image; required models,
ORF executables, approximately 21 MiB of offline manual pages and 18 MiB of Easel
reference material are intentionally retained. The candidate image is 2,246,722,323
bytes (about 2.25 GB); 139 packages and 305 archived notice files passed verification.
These tiny engineering fixtures do not validate a complete production GTDB download,
full taxonomy/createtsv or separate CRAM paths, biological MAG quality, or deployment
into real system directories. Native ARM is not declared; ARM-host emulation was not
separately validated, and the image does not support GPU execution.

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
