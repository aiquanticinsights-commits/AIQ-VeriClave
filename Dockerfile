# AIQ-VeriClave Docker Image
# Multi-stage build for minimal production image

# =============================================================================
# Stage 1: Base build environment with EDA tools
# =============================================================================
FROM ubuntu:24.04 AS builder

# Build arguments
ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG TARGETOS
ARG TARGETARCH

# Environment
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    python3-venv \
    verilator \
    yosys \
    sby \
    g++ \
    git \
    make \
    curl \
    ca-certificates \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# =============================================================================
# Stage 2: Python dependencies
# =============================================================================
FROM builder AS python-deps

# Copy requirements first for better caching
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Install the package in development mode
COPY . /app
WORKDIR /app
RUN pip install --no-cache-dir -e .

# =============================================================================
# Stage 3: Final runtime image
# =============================================================================
FROM ubuntu:24.04 AS runtime

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    verilator \
    yosys \
    sby \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=python-deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=builder /app /app
WORKDIR /app

# Create non-root user
RUN groupadd -r vericlave && useradd -r -g vericlave -m -d /home/vericlave -s /bin/bash vericlave
USER vericlave

# Set working directory
WORKDIR /home/vericlave

# Default command runs the test suite
CMD ["python", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py", "-v"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Labels
LABEL org.opencontainers.image.title="AIQ-VeriClave"
LABEL org.opencontainers.image.description="AIQ-VeriClave: Evidence-first AI verification platform for silicon design"
LABEL org.opencontainers.image.version="0.9.0"
LABEL org.opencontainers.image.authors="Satish Sura <satish@aiqi.in>"
LABEL org.opencontainers.image.source="https://github.com/aiquanticinsights-commits/AIQ-VeriClave"
LABEL org.opencontainers.image.documentation="https://aiqi.in/docs"
LABEL org.opencontainers.image.licenses="Apache-2.0"