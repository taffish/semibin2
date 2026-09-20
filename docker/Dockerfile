FROM mambaorg/micromamba:1.5.10-bookworm-slim@sha256:e3797091302382ea841498bc93a7b0a50f7c1448333d5e946d2d1608d0c5f43d AS builder
USER root
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV PATH=/opt/conda/bin:${PATH} PYTHONDONTWRITEBYTECODE=1
COPY docker/conda-linux-64.lock /tmp/environment.lock
COPY docker/conda-sha256.txt /tmp/conda-sha256.txt
COPY docker/conda-licenses.py /tmp/conda-licenses.py
COPY docker/upstream-notices/ /tmp/upstream-notices/
RUN set -eux; \
    micromamba install -y -n base --file /tmp/environment.lock; \
    sha256sum -c /tmp/conda-sha256.txt; \
    python /tmp/conda-licenses.py collect; \
    mkdir -p /opt/semibin2/share/doc/semibin2; \
    cp /tmp/environment.lock /opt/semibin2/share/doc/semibin2/conda-linux-64.lock; \
    cp /tmp/conda-sha256.txt /opt/semibin2/share/doc/semibin2/conda-sha256.txt; \
    micromamba list -n base > /opt/semibin2/share/doc/semibin2/conda-installed.txt; \
    micromamba clean -a -y; \
    rm -rf /opt/conda/pkgs /opt/conda/include /opt/conda/compiler_compat \
      /opt/conda/share/doc /opt/conda/share/man /opt/conda/share/info \
      /opt/conda/share/cmake /opt/conda/share/aclocal; \
    find /opt/conda -maxdepth 1 -type d -name '*-conda-linux-gnu' -exec rm -rf '{}' +; \
    find /opt/conda -type f \( -name '*.a' -o -name '*.pyc' \) -delete; \
    find /opt/conda/lib/python3.11/site-packages -type d \( -name __pycache__ -o -name tests -o -name test \) -prune -exec rm -rf '{}' +

FROM mambaorg/micromamba:1.5.10-bookworm-slim@sha256:e3797091302382ea841498bc93a7b0a50f7c1448333d5e946d2d1608d0c5f43d
USER root
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive PATH=/opt/conda/bin:${PATH} \
    PYTHONDONTWRITEBYTECODE=1 TAFFISH_ENV=TAFFISH TAFFISH_NAME=semibin2 \
    TAFFISH_VERSION=2.5.0 TAFFISH_RELEASE=1 OMP_NUM_THREADS=1
RUN set -eux; apt-get -o Acquire::Retries=3 update; \
    apt-get -o Acquire::Retries=3 install -y --no-install-recommends curl libx11-6; \
    rm -rf /var/lib/apt/lists/*; mkdir -p /work
COPY --from=builder /opt/conda /opt/conda
COPY --from=builder /opt/semibin2 /opt/semibin2
COPY docker/conda-licenses.py docker/test-conda-licenses.py docker/semibin-smoke.py docker/semibin-resource-smoke.py /opt/semibin2/share/testdata/
COPY docker/semibin-db.py /usr/local/bin/semibin-db
# Storage-only compatibility adaptation: no implicit legacy database download.
COPY docker/gtdb-local.py /opt/conda/lib/python3.11/site-packages/SemiBin/gtdb.py
RUN set -eux; chmod 755 /usr/local/bin/semibin-db; \
    python /opt/semibin2/share/testdata/conda-licenses.py verify; \
    python /opt/semibin2/share/testdata/test-conda-licenses.py; \
    python /opt/semibin2/share/testdata/semibin-smoke.py core; \
    python /opt/semibin2/share/testdata/semibin-smoke.py models; \
    SemiBin2 check_install
WORKDIR /work
ENTRYPOINT []
