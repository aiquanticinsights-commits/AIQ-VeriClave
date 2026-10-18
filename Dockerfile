# AIQ-VeriClave Docker Image
# CPU-only, no GPU required. Reproducible deploy target for the P6 gate.
#
# Build:  docker build -t aiq-vericlave .
# Run:    docker run --rm aiq-vericlave        (runs the frozen contract suite)
#
# Design notes:
# - Multi-stage: build venv + install package, then a slim runtime that copies
#   both. Fixes a prior bug where the runtime stage copied /app from a stage
#   that never created it.
# - SymbiYosys (`sby`) is installed best-effort; absence is non-blocking and is
#   recorded as UNAVAILABLE by the harness, per project policy.

# =============================================================================
# Stage 1: build — venv, Python deps, package
# =============================================================================
FROM ubuntu:24.04 AS build

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-pip \
        python3-dev \
        build-essential \
        git \
        ca-certificates \
        pkg-config \
        verilator \
        yosys \
    && rm -rf /var/lib/apt/lists/*

# sby: best-effort (not present in every archive) -> non-blocking.
RUN (apt-get update && apt-get install -y --no-install-recommends sby \
        && rm -rf /var/lib/apt/lists/*) \
    || echo "sby not in this archive - non-blocking (recorded UNAVAILABLE)"

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app
WORKDIR /app
RUN pip install --no-cache-dir .

# =============================================================================
# Stage 2: runtime — slim image, non-root
# =============================================================================
FROM ubuntu:24.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        verilator \
        yosys \
    && rm -rf /var/lib/apt/lists/*

RUN (apt-get update && apt-get install -y --no-install-recommends sby && rm -rf /var/lib/apt/lists/*) \
    || echo "sby not available - non-blocking (recorded UNAVAILABLE)"

COPY --from=build /opt/venv /opt/venv
COPY --from=build /app /app

RUN groupadd -r vericlave \
    && useradd -r -g vericlave -m -d /home/vericlave -s /bin/bash vericlave \
    && chown -R vericlave:vericlave /app

USER vericlave
WORKDIR /app

# Default command runs the frozen contract suite (stdlib; ~fast, no models).
CMD ["python", "-m", "unittest", "test_router", "test_platform", "test_rewards", "test_datasets", "test_p4_bench", "test_p4_heldout"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Labels
LABEL org.opencontainers.image.title="AIQ-VeriClave"
LABEL org.opencontainers.image.description="AIQ-VeriClave: Evidence-first AI verification platform for silicon design"
LABEL org.opencontainers.image.version="0.9.1"
LABEL org.opencontainers.image.authors="Satish Sura <satish@aiqi.in>"
LABEL org.opencontainers.image.source="https://github.com/aiquanticinsights-commits/AIQ-VeriClave"
LABEL org.opencontainers.image.documentation="https://aiqi.in/docs"
LABEL org.opencontainers.image.licenses="Apache-2.0"
