"""External corpora registry — verified datasets adopted into §4 (annex §4.1).

Each entry records provenance, license posture, intended consumer stage, and
verification status. Rule: status 'verified-paper' means the *paper/repo*
checks out; it does NOT mean the data is clean for training — the `caveats`
field states the required curation before any sample enters T0–T3.
"""
from __future__ import annotations

from dataclasses import dataclass, field


ALLOWED_USES = {"ppa-congestion", "understanding-cot", "synthesis-profiles",
                "real-bugs", "benchmarks", "flywheel-internal"}
ALLOWED_LICENSES = {"Apache-2.0", "MIT", "BSD-3-Clause", "Solderpad-0.51",
                    "research-verify", "internal"}


@dataclass(frozen=True)
class DatasetEntry:
    key: str
    name: str
    url: str
    license: str            # must be in ALLOWED_LICENSES; research-verify = read LICENSE on download
    uses: tuple[str, ...]   # subset of ALLOWED_USES
    status: str             # "verified-paper" | "verified-repo" | "internal" | "unverified"
    scale: str
    consumer: str           # which workstream/stage consumes it
    caveats: str = ""


REGISTRY: dict[str, DatasetEntry] = {
    "circuitnet-2.0": DatasetEntry(
        key="circuitnet-2.0",
        name="CircuitNet 2.0 (ICLR'24)",
        url="https://circuitnet.github.io/",
        license="research-verify",
        uses=("ppa-congestion",),
        status="verified-paper",
        scale="10,000+ samples; CPU/GPU/AI-chip; 14nm FinFET commercial flows",
        consumer="PHASE 5 auxiliary PPA/congestion head; WS4 protection trade-offs",
        caveats="Back-end physical-design data (congestion/DRV/IR-drop/delay), "
                "NOT RISC-V-microarchitecture-specific. Consume as congestion/PPA "
                "features only; never as RTL-correctness labels. v1=28nm, v3=45nm exist.",
    ),
    "deepcircuitx": DatasetEntry(
        key="deepcircuitx",
        name="DeepCircuitX (ICLAD'25; HF zeju-0727, 1.04GB annotations)",
        url="https://github.com/cure-lab/LCM-Datasetm",
        license="research-verify",
        uses=("understanding-cot", "benchmarks"),
        status="verified-paper",
        scale="4,000+ repos; repo/file/module/block; 57K+ CoT annotations; "
               "2,078 RISC-V repos; synthesized netlists + PPA",
        consumer="PHASE 4 SFT reasoning traces; BluesFL-style block context training",
        caveats="CoT annotations are GPT-4/Claude-generated (silver standard, "
                "human-eval claimed). Filter via FRM-equivalence before training; "
                "never treat annotations as ground truth.",
    ),
    "hlsdataset": DatasetEntry(
        key="hlsdataset",
        name="HLSDataset (ASAP'23, UT-LCA ML4Accel)",
        url="https://github.com/UT-LCA/ML4Accel-Dataset",
        license="research-verify",
        uses=("synthesis-profiles",),
        status="verified-paper",
        scale="~9,000 Verilog/FPGA type; Polybench/Machsuite/CHStone/Rosetta; "
               "Vivado/Vitis HLS+impl reports; ~50GB; 1,500+ machine-hours",
        consumer="Synthesis-aware features; Arty-profile regeneration via their scripts",
        caveats="Targets are ZU9EG/XC7V585T @100MHz — NOT Artix-7 35T/100T. Use "
                "methodology + CSV schema + generation scripts; re-run flows for "
                "Arty targets before any Arty claim. 'Kaggle HLS' is not the artifact; "
                "HLSDataset is.",
    ),
    "koios-2.0": DatasetEntry(
        key="koios-2.0",
        name="Koios 2.0 (UT Austin DL FPGA benchmarks)",
        url="https://github.com/UT-LCA/koios",
        license="research-verify",
        uses=("synthesis-profiles", "benchmarks"),
        status="verified-paper",
        scale="40 DL Verilog benchmarks, 12K–1.6M primitives, VTR/open-flow clean",
        consumer="Open-flow sanity + heterogeneity coverage alongside HLSDataset",
        caveats="Benchmarks (not profiles): pairs with HLSDataset, does not replace it.",
    ),
    "opentitan-bugs": DatasetEntry(
        key="opentitan-bugs",
        name="OpenTitan RTL bug histories (arXiv 2402.00684 methodology)",
        url="https://github.com/lowRISC/opentitan/issues",
        license="research-verify",
        uses=("real-bugs", "benchmarks"),
        status="verified-paper",
        scale="4,148 issues → 516 bugs → 235 RTL → 170 curated; 52.9% security; "
               "55.3% single-file, 61% ≤30 lines, ~half assignment fixes",
        consumer="WS5 closure eval + WS6 repair benchmark (human-bug realism check "
                 "against BugGen synthetics)",
        caveats="28% noise (65/235 discarded: no fix found / not design bugs). "
                "Raw issue scraping is FORBIDDEN — replicate the curation pipeline "
                "(closed-issue filter + fix linkage + AST footprint check) first. "
                "DV envs are UVM/Xcelium: gold reference for G1/G2 interop.",
    ),
    "own-flywheel": DatasetEntry(
        key="own-flywheel",
        name="Own T0/T2 flywheel (verif/, VCDs, traceability, BugGen mutants)",
        url="",
        license="internal",
        uses=("flywheel-internal", "real-bugs", "understanding-cot"),
        status="internal",
        scale="compounding with every IP run (see §4 T0/T2)",
        consumer="all stages; sole contamination-free core",
        caveats="External corpora augment this core; none replace it.",
    ),
}

# Corrections to the proposal, recorded so they are not re-introduced:
# - CircuitNet is NOT RISC-V-microarchitecture-mapped; it is backend-stage data.
# - There is no single "Kaggle HLS" artifact; the concrete assets are HLSDataset
#   (+ generation scripts) and Koios 2.0 benchmarks.
# - HLSDataset targets do NOT include Arty; Arty claims require re-running flows.
# - OpenTitan issues are NOT directly usable; ~28% need manual-equivalent filtering.
