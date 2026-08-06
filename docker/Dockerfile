FROM mambaorg/micromamba:1.5.10-bookworm-slim

ARG SEMIBIN_VERSION=2.4.1
ARG SEMIBIN_COMMIT=932d98b13761c3f64a928e1b74e41649d3c8bf14
ARG SEMIBIN_CONDA_BUILD=pyhdfd78af_0
ARG SEMIBIN_CONDA_SHA256=e6d95475806bd06ab05a129595e61b032c72e68446c378564ffe0373d39dd222
ARG SEMIBIN_RELEASE_WHEEL_SHA256=f0f0cb6b3f1302d63b0e9b073fb69a4649c8bb37f8aa2e3d31cad6c06196c070
ARG SEMIBIN_RELEASE_WHEEL_URL=https://github.com/BigDataBiology/SemiBin/releases/download/v2.4.1/semibin-2.4.1-py3-none-any.whl

USER root

ENV DEBIAN_FRONTEND=noninteractive

RUN set -eux; \
    for attempt in 1 2 3 4 5; do \
      if apt-get -o Acquire::Retries=3 update \
       && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
            bash \
            bzip2 \
            ca-certificates \
            coreutils \
            curl \
            findutils \
            grep \
            gzip \
            libx11-6 \
            sed \
            tar \
            xz-utils; then \
        break; \
      fi; \
      if [ "${attempt}" = "5" ]; then exit 1; fi; \
      apt-get clean; \
      rm -rf /var/lib/apt/lists/*; \
      sleep 5; \
    done; \
    rm -rf /var/lib/apt/lists/*

USER mambauser

RUN set -eux; \
    micromamba install -y -n base \
      -c conda-forge \
      -c bioconda \
      pip \
      "python=3.11" \
      "semibin=${SEMIBIN_VERSION}=${SEMIBIN_CONDA_BUILD}" \
      samtools \
      bedtools \
      hmmer \
      prodigal \
      ucx \
      rdma-core; \
    package_archive="$(find /opt/conda/pkgs -maxdepth 1 -type f -name "semibin-${SEMIBIN_VERSION}-${SEMIBIN_CONDA_BUILD}.conda" -print -quit)"; \
    test -n "${package_archive}"; \
    echo "${SEMIBIN_CONDA_SHA256}  ${package_archive}" | sha256sum -c -; \
    micromamba clean -a -y; \
    rm -rf \
      /opt/conda/include \
      /opt/conda/share/aclocal \
      /opt/conda/share/cmake \
      /opt/conda/share/doc \
      /opt/conda/share/info \
      /opt/conda/share/man; \
    find /opt/conda -type f \( -name '*.a' -o -name '*.pyc' \) -delete; \
    find /opt/conda/lib/python3.11/site-packages -type d \
      \( -name '__pycache__' -o -name 'test' -o -name 'tests' \) \
      -prune -exec rm -rf '{}' '+'

ENV PATH=/opt/conda/bin:${PATH}
ENV PYTHONDONTWRITEBYTECODE=1

USER root

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN set -eux; \
    mkdir -p \
      /opt/semibin2/share/doc/semibin2 \
      /opt/semibin2/share/licenses/semibin2 \
      /opt/semibin2/share/testdata; \
    curl --http1.1 --retry 5 --retry-delay 5 --retry-all-errors -fsSL "${SEMIBIN_RELEASE_WHEEL_URL}" -o /tmp/semibin.whl; \
    echo "${SEMIBIN_RELEASE_WHEEL_SHA256}  /tmp/semibin.whl" | sha256sum -c -; \
    mkdir -p /tmp/semibin-wheel; \
    python -m zipfile -e /tmp/semibin.whl /tmp/semibin-wheel; \
    cp "/tmp/semibin-wheel/semibin-${SEMIBIN_VERSION}.dist-info/licenses/COPYING.MIT" /opt/semibin2/share/licenses/semibin2/COPYING.MIT; \
    micromamba list -n base > /opt/semibin2/share/doc/semibin2/conda-packages.txt; \
    python -m pip freeze > /opt/semibin2/share/doc/semibin2/pip-freeze.txt; \
    { \
      printf "upstream_repo=https://github.com/BigDataBiology/SemiBin\n"; \
      printf "upstream_tag=v%s\n" "${SEMIBIN_VERSION}"; \
      printf "upstream_commit=%s\n" "${SEMIBIN_COMMIT}"; \
      printf "runtime_source=bioconda::semibin=%s=%s\n" "${SEMIBIN_VERSION}" "${SEMIBIN_CONDA_BUILD}"; \
      printf "runtime_package_sha256=%s\n" "${SEMIBIN_CONDA_SHA256}"; \
      printf "release_artifact=github-release::semibin-%s-py3-none-any.whl\n" "${SEMIBIN_VERSION}"; \
      printf "release_artifact_sha256=%s\n" "${SEMIBIN_RELEASE_WHEEL_SHA256}"; \
      printf "platform_note=This TAFFISH build is validated as linux/amd64 only.\n"; \
      printf "gpu_note=This image is a CPU runtime; CUDA/GPU SemiBin2 requires a custom GPU-capable PyTorch image.\n"; \
      printf "database_note=SemiBin2 built-in pretrained models are supplied by the packaged semibin distribution; external contigs and abundance/BAM inputs are user data.\n"; \
    } > /opt/semibin2/share/doc/semibin2/source.txt; \
    rm -rf /opt/conda/pkgs; \
    rm -rf /tmp/semibin.whl /tmp/semibin-wheel

RUN cat > /opt/semibin2/share/testdata/semibin2-smoke-concat.sh <<'EOF'
#!/bin/sh
set -eu

tmp="${1:-/tmp/taf-semibin2-concat-$$}"
rm -rf "$tmp"
mkdir -p "$tmp/input" "$tmp/output"
cd "$tmp"

seq_a="$(printf 'ACGT%.0s' $(seq 1 400))"
seq_b="$(printf 'TGCA%.0s' $(seq 1 400))"
seq_c="$(printf 'GATTACA%.0s' $(seq 1 230))"

cat > input/S1.fa <<FASTA
>contig_a
${seq_a}
>contig_b
${seq_b}
FASTA

cat > input/S2.fa <<FASTA
>contig_c
${seq_c}
FASTA

SemiBin2 concatenate_fasta \
  --input-fasta input/S1.fa input/S2.fa \
  --output output

test -s output/concatenated.fa.gz
gzip -cd output/concatenated.fa.gz > concatenated.fa
grep -F '>S1:contig_a' concatenated.fa >/dev/null
grep -F '>S1:contig_b' concatenated.fa >/dev/null
grep -F '>S2:contig_c' concatenated.fa >/dev/null
grep -c '^>' concatenated.fa | grep -Fx '3' >/dev/null

rm -rf "$tmp"
EOF

RUN cat > /opt/semibin2/share/testdata/semibin2-smoke-install-skills.sh <<'EOF'
#!/bin/sh
set -eu

tmp="${1:-/tmp/taf-semibin2-skills-$$}"
rm -rf "$tmp"
mkdir -p "$tmp"
cd "$tmp"

SemiBin2 install-skills --skills-dir "$tmp/installed" > run.log 2>&1

test -s installed/semibin/SKILL.md
test -s installed/semibin/references/developer-guide.md
test -s installed/semibin/references/subcommands.md
grep -F 'name: semibin' installed/semibin/SKILL.md >/dev/null
grep -F 'version: 1.0.0' installed/semibin/SKILL.md >/dev/null
grep -F 'Installed 1 skill(s)' run.log >/dev/null
test ! -e .claude

rm -rf "$tmp"
EOF

RUN cat > /opt/semibin2/share/testdata/semibin2-smoke-short-contigs.sh <<'EOF'
#!/bin/sh
set -eu

tmp="${1:-/tmp/taf-semibin2-short-contigs-$$}"
rm -rf "$tmp"
mkdir -p "$tmp/output"
cd "$tmp"

short_contig="$(printf 'ACGT%.0s' $(seq 1 375))"
cat > short-contigs.fa <<FASTA
>contig_1
${short_contig}
>contig_2
${short_contig}
>contig_3
${short_contig}
>contig_4
${short_contig}
FASTA

if SemiBin2 generate_sequence_features_single \
    --input-fasta short-contigs.fa \
    --output output \
    --min-len 1000 \
    --ml-threshold 4000 > run.log 2>&1; then
  echo "expected short-contig validation to fail" >&2
  exit 1
fi

grep -F 'none contain at least 4000 basepairs' run.log >/dev/null
grep -F 'the longest is 1500' run.log >/dev/null
test ! -e output/data.csv

rm -rf "$tmp"
EOF

RUN set -eux; \
    ln -sf /opt/conda/bin/SemiBin2 /usr/local/bin/SemiBin2; \
    ln -sf /opt/conda/bin/python /usr/local/bin/python; \
    ln -sf /opt/conda/bin/python3 /usr/local/bin/python3; \
    ln -sf /opt/conda/bin/samtools /usr/local/bin/samtools; \
    ln -sf /opt/conda/bin/bedtools /usr/local/bin/bedtools; \
    ln -sf /opt/conda/bin/hmmsearch /usr/local/bin/hmmsearch; \
    ln -sf /opt/conda/bin/hmmscan /usr/local/bin/hmmscan; \
    ln -sf /opt/conda/bin/hmmpress /usr/local/bin/hmmpress; \
    ln -sf /opt/conda/bin/prodigal /usr/local/bin/prodigal; \
    chmod 0755 /opt/semibin2/share/testdata/semibin2-smoke-concat.sh /opt/semibin2/share/testdata/semibin2-smoke-install-skills.sh /opt/semibin2/share/testdata/semibin2-smoke-short-contigs.sh; \
    python -c "import importlib.metadata as md; import SemiBin, torch, numpy, pandas, sklearn, igraph, requests, safetensors, tqdm, numexpr; assert md.version('SemiBin') == '${SEMIBIN_VERSION}'; print(md.version('SemiBin'))" | grep -Fx "${SEMIBIN_VERSION}" >/dev/null; \
    python -c "from pathlib import Path; import SemiBin; expected = {'built_environment_model.pt', 'cat_gut_model.pt', 'chicken_caecum_model.pt', 'dog_gut_model.pt', 'global_model.pt', 'human_gut_model.pt', 'human_oral_model.pt', 'mouse_gut_model.pt', 'ocean_model.pt', 'pig_gut_model.pt', 'soil_model.pt', 'wastewater_model.pt'}; found = {path.name for path in (Path(next(iter(SemiBin.__path__))) / 'models').glob('*.pt')}; assert found == expected; print(len(found))" | grep -Fx "12" >/dev/null; \
    SemiBin2 --version 2>&1 | grep -Fx "${SEMIBIN_VERSION}" >/dev/null; \
    SemiBin2 --help 2>&1 | grep -F "single_easy_bin" >/dev/null; \
    SemiBin2 --help 2>&1 | grep -F "multi_easy_bin" >/dev/null; \
    SemiBin2 --help 2>&1 | grep -F "concatenate_fasta" >/dev/null; \
    SemiBin2 --help 2>&1 | grep -F "install-skills" >/dev/null; \
    SemiBin2 single_easy_bin --help 2>&1 | grep -F -- "--environment" >/dev/null; \
    SemiBin2 multi_easy_bin --help 2>&1 | grep -F -- "--input-fasta" >/dev/null; \
    SemiBin2 concatenate_fasta --help 2>&1 | grep -F -- "--input-fasta" >/dev/null; \
    SemiBin2 install-skills --help 2>&1 | grep -F -- "--skills-dir" >/dev/null; \
    SemiBin2 check_install --help 2>&1 | grep -F "check" >/dev/null; \
    SemiBin2 check_install 2>&1 | grep -F "SemiBin2" >/dev/null; \
    samtools --version 2>&1 | grep -F "samtools" >/dev/null; \
    bedtools --version 2>&1 | grep -F "bedtools" >/dev/null; \
    hmmsearch -h 2>&1 | grep -F "HMMER" >/dev/null; \
    hmmscan -h 2>&1 | grep -F "HMMER" >/dev/null; \
    prodigal -v 2>&1 | grep -F "Prodigal" >/dev/null; \
    /opt/semibin2/share/testdata/semibin2-smoke-concat.sh /tmp/semibin2-build-concat; \
    { LD_LIBRARY_PATH=/opt/conda/lib:${LD_LIBRARY_PATH:-} find /opt/conda/lib -type f -name '*.so*' -print0 | xargs -0 -r ldd > /tmp/semibin2-ldd.txt; } || true; \
    if grep -F "not found" /tmp/semibin2-ldd.txt | grep -Ev 'libcuda\.so|libnvidia-ml\.so|libcudart\.so'; then exit 1; fi

WORKDIR /root

ENV TAFFISH_ENV=TAFFISH
ENV TAFFISH_NAME=semibin2
