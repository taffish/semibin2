semibin2 2.3.0-r1

Purpose:
  Package SemiBin2 for TAFFISH. SemiBin2 bins metagenomic contigs into
  metagenome-assembled genomes using sequence composition, abundance, and
  built-in environment models.

Usage:
  taf-semibin2 -- --help
  taf-semibin2 -- --version
  taf-semibin2 SemiBin2 single_easy_bin --environment human_gut -i contigs.fa -b sample.sorted.bam -o semibin2-out
  taf-semibin2 SemiBin2 multi_easy_bin --environment global -i concatenated.fa.gz -b S1.bam S2.bam -o semibin2-multi
  taf-semibin2 SemiBin2 concatenate_fasta --input-fasta S1.fa S2.fa --output concat

Common workflows:
  taf-semibin2 SemiBin2 check_install
  taf-semibin2 SemiBin2 single_easy_bin --help
  taf-semibin2 SemiBin2 multi_easy_bin --help
  taf-semibin2 SemiBin2 concatenate_fasta --help

Packaged commands:
  SemiBin2    Main upstream SemiBin2 CLI.
  python      Python runtime with SemiBin, PyTorch, NumPy, pandas, sklearn,
              igraph, safetensors, and related dependencies.
  samtools    BAM/CRAM helper used by upstream workflows when needed.
  bedtools    Required SemiBin runtime dependency.
  hmmsearch   HMMER command used by marker-related workflows.
  hmmscan     HMMER command used by marker-related workflows.
  hmmpress    HMMER helper.
  prodigal    Optional ORF finder when --orf-finder prodigal is requested.

Upstream help and version:
  taf-semibin2 -- --help
  taf-semibin2 -- --version
  taf-semibin2 SemiBin2 --help
  taf-semibin2 SemiBin2 single_easy_bin --help
  taf-semibin2 SemiBin2 multi_easy_bin --help
  taf-semibin2 SemiBin2 concatenate_fasta --help

Inputs:
  -i, --input-fasta    Contig FASTA or concatenated multi-sample FASTA.
  -b, --input-bam      Sorted BAM files prepared outside this app.
  -a, --abundance      Precomputed abundance input where supported upstream.
  --environment        Built-in model environment, such as human_gut, ocean,
                       soil, wastewater, or global.
  --sequencing-type    Data type such as short_read or long_read.

Key outputs:
  --output directory   SemiBin2 output directory with logs, features, tables,
                       and bins when the selected workflow produces bins.
  concatenated.fa.gz   Output of concatenate_fasta in SemiBin 2.3.0; contig
                       names become sample_name:original_contig_name by default.
  output_bins/         Upstream bin FASTA directory for successful binning runs.

Platform and resources:
  This image is packaged and validated as linux/amd64. Docker and Podman runs
  request linux/amd64 automatically from the TAFFISH wrapper; arm64 hosts use
  backend emulation when available.
  The image is CPU oriented. Upstream CUDA/GPU use requires a custom GPU-capable
  PyTorch image and backend GPU runtime options.

Boundaries:
  This app does not assemble reads, map reads, sort/index BAM files, assess MAG
  quality, or download production databases.
  SemiBin2 built-in pretrained model assets are supplied by the packaged
  upstream distribution; user assemblies and abundance/BAM inputs are external.
  The smoke test checks CLI/import/check_install and a tiny concatenate_fasta
  path, not production model training or biological bin quality.

Detailed documentation:
  https://semibin.readthedocs.io/en/latest/
  https://github.com/BigDataBiology/SemiBin

Wrapper options:
  taf-semibin2 --help       Show this TAFFISH help.
  taf-semibin2 --version    Show TAFFISH wrapper version.
  taf-semibin2 --compile    Compile the TAFFISH wrapper.
  taf-semibin2 -- --help    Pass option-leading arguments to the default SemiBin2 command.

Notes:
  Because this is a command-mode tool app, use "taf-semibin2 SemiBin2 ..."
  for SemiBin2 subcommands. A bare "taf-semibin2 single_easy_bin ..." asks
  TAFFISH to run a container executable named "single_easy_bin".
