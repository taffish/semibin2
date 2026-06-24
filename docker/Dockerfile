FROM mambaorg/micromamba:1.5.10-bookworm-slim

ARG SEMIBIN_VERSION=2.3.0
ARG SEMIBIN_SDIST_SHA256=d12fb62dd40d6443df04c4b2cf91cb7935b945ad68152b6e6ef06dda55976d48
ARG SEMIBIN_SDIST_URL=https://files.pythonhosted.org/packages/source/s/semibin/semibin-2.3.0.tar.gz

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

RUN micromamba install -y -n base \
      -c conda-forge \
      -c bioconda \
      pip \
      "python=3.11" \
      "semibin=${SEMIBIN_VERSION}" \
      samtools \
      bedtools \
      hmmer \
      prodigal \
      ucx \
      rdma-core \
 && micromamba clean -a -y

ENV PATH=/opt/conda/bin:${PATH}

USER root

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN set -eux; \
    mkdir -p \
      /opt/semibin2/share/doc/semibin2 \
      /opt/semibin2/share/licenses/semibin2 \
      /opt/semibin2/share/testdata; \
    curl --http1.1 --retry 5 --retry-delay 5 --retry-all-errors -fsSL "${SEMIBIN_SDIST_URL}" -o /tmp/semibin.tar.gz; \
    echo "${SEMIBIN_SDIST_SHA256}  /tmp/semibin.tar.gz" | sha256sum -c -; \
    mkdir -p /tmp/semibin-src; \
    tar -xzf /tmp/semibin.tar.gz -C /tmp/semibin-src --strip-components=1; \
    cp /tmp/semibin-src/COPYING.MIT /opt/semibin2/share/licenses/semibin2/COPYING.MIT; \
    micromamba list -n base > /opt/semibin2/share/doc/semibin2/conda-packages.txt; \
    python -m pip freeze > /opt/semibin2/share/doc/semibin2/pip-freeze.txt; \
    { \
      printf "upstream_repo=https://github.com/BigDataBiology/SemiBin\n"; \
      printf "upstream_tag=v%s\n" "${SEMIBIN_VERSION}"; \
      printf "runtime_source=bioconda::semibin=%s\n" "${SEMIBIN_VERSION}"; \
      printf "source_archive=pypi::SemiBin==%s\n" "${SEMIBIN_VERSION}"; \
      printf "source_sdist_sha256=%s\n" "${SEMIBIN_SDIST_SHA256}"; \
      printf "platform_note=This TAFFISH build is validated as linux/amd64 only.\n"; \
      printf "gpu_note=This image is a CPU runtime; CUDA/GPU SemiBin2 requires a custom GPU-capable PyTorch image.\n"; \
      printf "database_note=SemiBin2 built-in pretrained models are supplied by the packaged semibin distribution; external contigs and abundance/BAM inputs are user data.\n"; \
    } > /opt/semibin2/share/doc/semibin2/source.txt; \
    rm -rf /opt/conda/pkgs; \
    rm -rf /tmp/semibin.tar.gz /tmp/semibin-src

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
    chmod 0755 /opt/semibin2/share/testdata/semibin2-smoke-concat.sh; \
    python -c 'import importlib.metadata as md; import SemiBin, torch, numpy, pandas, sklearn, igraph, requests, safetensors, tqdm, numexpr; assert md.version("SemiBin") == "2.3.0"; print(md.version("SemiBin"))' | grep -Fx "${SEMIBIN_VERSION}" >/dev/null; \
    SemiBin2 --version 2>&1 | grep -F "${SEMIBIN_VERSION}" >/dev/null; \
    SemiBin2 --help 2>&1 | grep -F "single_easy_bin" >/dev/null; \
    SemiBin2 --help 2>&1 | grep -F "multi_easy_bin" >/dev/null; \
    SemiBin2 --help 2>&1 | grep -F "concatenate_fasta" >/dev/null; \
    SemiBin2 single_easy_bin --help 2>&1 | grep -F -- "--environment" >/dev/null; \
    SemiBin2 multi_easy_bin --help 2>&1 | grep -F -- "--input-fasta" >/dev/null; \
    SemiBin2 concatenate_fasta --help 2>&1 | grep -F -- "--input-fasta" >/dev/null; \
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
