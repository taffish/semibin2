# Source drift: the digest pins image identity, not permanent registry retention. If pulling fails,
# check official image availability and revalidate in a new release; never silently switch digests.
FROM mambaorg/micromamba:1.5.10-bookworm-slim@sha256:e3797091302382ea841498bc93a7b0a50f7c1448333d5e946d2d1608d0c5f43d AS builder
USER root
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV PATH=/opt/conda/bin:${PATH} PYTHONDONTWRITEBYTECODE=1
# Source drift: explicit URLs/builds plus SHA256 pin the current dependency bytes, but Conda repositories may
# remove packages. For 404s, check the lock and upstream retention; do not hide failures by dropping checks or using unpinned installs.
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
      /opt/conda/share/cmake /opt/conda/share/aclocal \
      /opt/conda/etc/conda/test-files; \
    find /opt/conda -maxdepth 1 -type d -name '*-conda-linux-gnu' -exec rm -rf '{}' +; \
    find /opt/conda -type f \( -name '*.a' -o -name '*.pyc' \) -delete; \
    find /opt/conda/lib/python3.11/site-packages -type d \( -name __pycache__ -o -name tests -o -name test \) -prune -exec rm -rf '{}' +

FROM mambaorg/micromamba:1.5.10-bookworm-slim@sha256:e3797091302382ea841498bc93a7b0a50f7c1448333d5e946d2d1608d0c5f43d
USER root
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive PATH=/opt/conda/bin:${PATH} \
    PYTHONDONTWRITEBYTECODE=1 TAFFISH_ENV=TAFFISH TAFFISH_NAME=semibin2 \
    TAFFISH_VERSION=2.6.0 TAFFISH_RELEASE=2 OMP_NUM_THREADS=1
# Source drift: bookworm APT indexes/dependencies change with the repository; resolution occurs at install time, not against a historical snapshot.
# On failure, check the suite, indexes and package status before validating a fix in an immutable successor; long-term rebuildability is not guaranteed.
RUN set -eux; apt-get -o Acquire::Retries=3 update; \
    apt-get -o Acquire::Retries=3 install -y --no-install-recommends curl libx11-6; \
    rm -rf /var/lib/apt/lists/*; mkdir -p /work
COPY --from=builder /opt/conda /opt/conda
COPY --from=builder /opt/semibin2 /opt/semibin2
COPY --chmod=0644 docker/conda-licenses.py docker/test-conda-licenses.py docker/semibin-smoke.py docker/semibin-resource-smoke.py docker/test-resource-runtime.py /opt/semibin2/share/testdata/
COPY --chmod=0755 docker/semibin-db.py /usr/local/bin/semibin-db
COPY --chmod=0644 docker/semibin_runtime.py /usr/local/bin/semibin_runtime.py
# Storage-only compatibility adaptation: no implicit legacy database download.
COPY --chmod=0644 docker/gtdb-local.py /opt/conda/lib/python3.11/site-packages/SemiBin/gtdb.py
# COPY --chmod also applies to a newly created destination directory in current BuildKit.
# Keep Python files non-executable, but make their parent traversable for ordinary SIF users.
RUN set -eux; chmod 755 /usr/local/bin/semibin-db /opt/semibin2/share/testdata; \
    test "$(stat -c '%a' /opt/semibin2/share/testdata)" = 755; \
    python /opt/semibin2/share/testdata/conda-licenses.py verify; \
    python /opt/semibin2/share/testdata/test-conda-licenses.py; \
    python /opt/semibin2/share/testdata/semibin-smoke.py core; \
    python /opt/semibin2/share/testdata/semibin-smoke.py models; \
    SemiBin2 check_install
WORKDIR /work
ENTRYPOINT []
