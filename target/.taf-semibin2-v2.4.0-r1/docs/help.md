taf-semibin2 2.4.0-r1

Purpose:
  Run SemiBin2 metagenomic binning with sequence composition, abundance and
  bundled pretrained environment models.

Usage:
  taf-semibin2 -- --help
  taf-semibin2 -- --version
  taf-semibin2 SemiBin2 single_easy_bin --environment human_gut -i contigs.fa -b sample.sorted.bam -o semibin2-out
  taf-semibin2 SemiBin2 multi_easy_bin --environment global -i concatenated.fa.gz -b S1.bam S2.bam -o semibin2-multi
  taf-semibin2 SemiBin2 concatenate_fasta --input-fasta S1.fa S2.fa --output concat
  taf-semibin2 SemiBin2 install-skills --skills-dir .claude/skills

Common commands:
  taf-semibin2 SemiBin2 check_install
  taf-semibin2 SemiBin2 single_easy_bin --help
  taf-semibin2 SemiBin2 multi_easy_bin --help
  taf-semibin2 SemiBin2 concatenate_fasta --help
  taf-semibin2 SemiBin2 install-skills --help

Packaged runtime:
  SemiBin2    Main upstream CLI and bundled environment models.
  python      Python 3.11 with SemiBin, CPU PyTorch, NumPy, pandas, sklearn,
              igraph, safetensors and related dependencies.
  samtools    BAM/CRAM helper.
  bedtools    Coverage helper required by SemiBin workflows.
  hmmsearch   HMMER marker-search command.
  hmmscan     HMMER scan command.
  hmmpress    HMMER profile preparation helper.
  prodigal    Optional ORF finder for --orf-finder prodigal.

Inputs:
  -i, --input-fasta    Assembled contig FASTA or concatenated FASTA.
  -b, --input-bam      Sorted alignment files prepared outside this app.
  -a, --abundance      Precomputed abundance input where supported.
  --environment        Bundled model such as human_gut, ocean, soil,
                       wastewater or global.
  --sequencing-type    short_read, long_read or the hybrid synonym.

Key outputs:
  --output directory   Logs, features, tables and bin FASTA files.
  concatenated.fa.gz   concatenate_fasta output with sample-prefixed contigs.
  output_bins/         Bin FASTA directory when binning produces bins.
  SemiBinRun.log       Run log including the 2.4.0 end-of-run binning summary.

Version 2.4.0:
  Requires Python 3.10 or newer; this image uses Python 3.11.
  Adds install-skills and a final binning summary, and fixes --cannot-name,
  abundance-plus-environment validation, GTDB extraction errors, logging and
  paired-array length checks.

Agent skill installation:
  install-skills copies an upstream-provided skill for coding agents.
  --skills-dir selects an explicit destination.
  Without it, files go to ./.claude/skills; --user writes under
  $HOME/.claude/skills. TAFFISH mounts these host paths. Nothing is installed
  automatically.

Platform and resources:
  Native linux/amd64 only. Docker and Podman request linux/amd64 automatically;
  arm64 hosts require backend emulation. This is a CPU-oriented image.
  Memory, CPU time and disk use scale with assembly size and sample count.

Boundaries:
  This app does not assemble reads, map reads, sort/index BAM files, assess MAG
  quality or bundle a production GTDB database.
  Deprecated semi-supervised taxonomy paths require external MMseqs2 and GTDB;
  the optional FragGeneScan path is not bundled. Current self-supervised paths,
  built-in fast-naive ORF finding and packaged Prodigal are supported.
  download_GTDB is an explicit deprecated network operation;
  generate_cannot_links may also download GTDB when no reference is supplied.
  Neither is tested or started automatically. GPU use requires a custom
  CUDA/PyTorch image.

Command mode:
  Use "taf-semibin2 SemiBin2 SUBCOMMAND ...". A bare subcommand name is treated
  as a container executable. Use "-- --help" for option-leading arguments to
  the default SemiBin2 command.

Detailed documentation:
  https://semibin.readthedocs.io/en/latest/
  https://github.com/BigDataBiology/SemiBin

Wrapper options:
  taf-semibin2 --help       Show this TAFFISH help.
  taf-semibin2 --version    Show the TAFFISH wrapper version.
  taf-semibin2 --compile    Print generated shell code.
  taf-semibin2 -- --help    Pass option-leading arguments to SemiBin2.
