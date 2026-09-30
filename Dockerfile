# AIQ-VeriClave P0 CPU image — mirrors WSL Ubuntu truth layer (locked 2026-09-28).
# WSL reference: Ubuntu 26.04, Verilator 5.032, Yosys 0.52, SBY 0.68,
# Python 3.14 + cocotb 2.1.0 + pytest 9.1.1 in venv (PEP 668).
# Docker uses Ubuntu 24.04 LTS (nearest stable image with apt verilator/yosys);
# version drift is caught by CI `*- --version` checks, not assumed equal.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip \
    verilator yosys sby g++ \
    git make curl ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
  || (apt-get update && apt-get install -y --no-install-recommends \
     python3 python3-venv python3-pip \
     verilator yosys g++ \
     git make curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*)
# (sby is absent from some Ubuntu apt pools — CI treats it as non-blocking P0;
# WSL host carries SBY 0.68 as the reference formal runner. g++ enables
# --cc simulation builds inside the image for the E2 benchmark.)
WORKDIR /work
COPY requirements.txt /work/requirements.txt
RUN python3 -m venv /opt/vericlave-venv \
 && /opt/vericlave-venv/bin/pip install --no-cache-dir -r /work/requirements.txt

COPY . /work/AIQ-VeriClave
WORKDIR /work/AIQ-VeriClave

# P0 contract: entire executable gate (ARCHITECTURE.md acceptance mapping)
CMD ["/opt/vericlave-venv/bin/python", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"]
