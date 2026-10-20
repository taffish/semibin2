semibin2 2.6.0-r1

Purpose:
  Bin metagenomic contigs with CPU self-supervised learning or a built-in model.

Usage:
  taf-semibin2 SemiBin2 single_easy_bin -i contigs.fa -b reads.sorted.bam -o bins -p 8 --engine cpu
  taf-semibin2 SemiBin2 single_easy_bin -i contigs.fa -b reads.sorted.bam -o bins --environment human_gut -p 8 --engine cpu
  taf-semibin2 -- --help
  taf-semibin2 -- --version

Common tasks:
  taf-semibin2 SemiBin2 concatenate_fasta -i sample1.fa sample2.fa -o concat
  taf-semibin2 SemiBin2 multi_easy_bin -i concat/concatenated.fa.gz -b sample1.bam sample2.bam -o multi -p 8 --engine cpu
  taf-semibin2 SemiBin2 generate_sequence_features_single -i contigs.fa -b reads.sorted.bam -o features -p 8
  taf-semibin2 SemiBin2 train_self --data features/data.csv --data-split features/data_split.csv -o trained --engine cpu -p 8
  taf-semibin2 SemiBin2 bin -i contigs.fa --data features/data.csv --model trained/model.pt -o bins --engine cpu -p 8

Required inputs:
  Contig FASTA plus coordinate-sorted BAM mapped to those exact contig IDs.
  For multi-sample input, map reads to the concatenated reference first.
  FASTA sample filenames must be unique; concatenate adds sample:contig IDs.
  --abundance accepts strobealign-aemb split-contig tables for at least 5 samples.
  Only load model files you trust; do not overwrite your reference or inputs.

Common options and outputs:
  -p threads; --engine cpu; --sequencing-type long_read for long-read assemblies.
  --environment selects one of 12 packaged pretrained models; no download needed.
  Default self-supervised mode trains from the supplied sample, without GTDB.
  Outputs include data.csv, data_split.csv, model.pt (when trained), output_bins/.
  Use a new output directory: upstream may overwrite existing output files.

Backend and platform:
  Native linux/amd64 only; Docker/Podman select amd64 automatically on ARM hosts.
  Docker:    TAFFISH_CONTAINER_BACKEND=docker taf-semibin2 SemiBin2 check_install
  Podman:    TAFFISH_CONTAINER_BACKEND=podman taf-semibin2 SemiBin2 check_install
  Apptainer: TAFFISH_CONTAINER_BACKEND=apptainer taf-semibin2 SemiBin2 check_install
  Apptainer needs native x86_64 Linux. macOS/ARM: use Docker/Podman emulation.
  GPU is unsupported in this CPU image on all three backends; use this CPU path
  or a separate GPU PyTorch environment following upstream installation docs.

Legacy GTDB preparation:
  Needed only for deprecated semi-supervised taxonomy paths, not the defaults.
  --gtdb-v95 selects the fixed official 24 GB archive; terms: CC-BY-4.0, MD5 only.
  mkdir -p "$HOME/.local/share/taffish/databases/semibin2"
  DBROOT="$HOME/.local/share/taffish/databases/semibin2"
  chmod 755 "$DBROOT"
  export TAFFISH_SEMIBIN_DB_AUTO_MOUNT=0
  Docker:
    TAFFISH_CONTAINER_BACKEND=docker TAFFISH_DOCKER_RUN_ARGS="--user $(id -u):$(id -g) -v '$DBROOT:/db-install'" taf-semibin2 semibin-db install --gtdb-v95 --db-root /db-install --rights-reviewed
  Podman:
    TAFFISH_CONTAINER_BACKEND=podman TAFFISH_PODMAN_RUN_ARGS="--userns keep-id -v '$DBROOT:/db-install'" taf-semibin2 semibin-db install --gtdb-v95 --db-root /db-install --rights-reviewed
  Apptainer:
    TAFFISH_CONTAINER_BACKEND=apptainer TAFFISH_APPTAINER_RUN_ARGS="--bind '$DBROOT:/db-install'" taf-semibin2 semibin-db install --gtdb-v95 --db-root /db-install --rights-reviewed
  Preview: --dry-run; offline: --source-dir DIR; custom: --recipe recipe.json.
  Repeat to resume/verify after Ctrl-C/TERM; then unset TAFFISH_SEMIBIN_DB_AUTO_MOUNT.

Read-only site database or custom-model reuse:
  Set ROOT to your administrator's prepared database or model root.
  export TAFFISH_SEMIBIN_DB_AUTO_MOUNT=0; ROOT=/usr/local/share/taffish/databases/semibin2
  Docker:
    export TAFFISH_CONTAINER_BACKEND=docker
    export TAFFISH_DOCKER_RUN_ARGS="-v '$ROOT:/resources:ro'"
  Podman:
    export TAFFISH_CONTAINER_BACKEND=podman
    export TAFFISH_PODMAN_RUN_ARGS="-v '$ROOT:/resources:ro'"
  Apptainer:
    export TAFFISH_CONTAINER_BACKEND=apptainer
    export TAFFISH_APPTAINER_RUN_ARGS="--bind '$ROOT:/resources:ro'"
  Then, with any of these backend selections:
    taf-semibin2 semibin-db verify --db-root /resources --id gtdb--95
    taf-semibin2 SemiBin2 generate_cannot_links -i contigs.fa -o links --reference-db /resources/gtdb--95 -p 8
  For a custom-model root, instead pass --model /resources/PROJECT/model.pt to bin.
  Auto root: TAFFISH_SEMIBIN_DB_PATH > personal path > /usr/local/share > /opt/taffish.
  Auto members appear under /resources/semibin2; select the member explicitly.
  TAFFISH_SEMIBIN_DB_AUTO_MOUNT=0 disables discovery; manual binds remain usable.
  Invalid roots fail closed. Full GTDB needs >100 GB plus archive/workspace.

Immediate notes:
  Select pretrained environments explicitly; do not combine --model with --environment.
  For paths with spaces, preserve inner quotes: -i "'input/contigs 1.fa'".

More help:
  taf-semibin2 SemiBin2 single_easy_bin --help
  taf-semibin2 semibin-db --help
  https://github.com/taffish/semibin2

Wrapper options:
  taf-semibin2 --help       Show this usage help.
  taf-semibin2 --version    Show wrapper version.
