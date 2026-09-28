"""Compute adapter — one interface, three backends (CPU-first).

The same benchmark runs unmodified on local CPU, a free/open remote endpoint,
or an optional accelerated environment. Backend selection is configuration,
never architecture: `vericlave run benchmark.json` does not care where
inference executes. Cloud/GPU is an optional accelerator, not a dependency —
the system must keep functioning with zero GPU.
"""
from __future__ import annotations

import json

BACKENDS = ("local-cpu", "free-cloud", "accelerated-external")


def load_config(path: str) -> dict:
    """Load a benchmark config (JSON; YAML only if pyyaml is installed).

    Schema: {"backend": str, "endpoint": str, "suite": str, "timeout_s": int}
    """
    text = open(path, encoding="utf-8").read()
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError("YAML configs need pyyaml; use JSON instead") from exc
        cfg = yaml.safe_load(text)
    else:
        cfg = json.loads(text)
    backend = cfg.get("backend", "local-cpu")
    if backend not in BACKENDS:
        raise ValueError(f"unknown backend '{backend}'; choose from {BACKENDS}")
    if backend != "local-cpu" and not cfg.get("endpoint"):
        raise ValueError(f"backend '{backend}' requires an 'endpoint' URL")
    cfg.setdefault("timeout_s", 3600)
    return cfg


def describe(cfg: dict) -> str:
    """One-line execution plan for a benchmark config (no side effects)."""
    b = cfg["backend"]
    if b == "local-cpu":
        return "local-cpu: evaluate() in-process on local CPU (no network, no GPU)"
    if b == "free-cloud":
        return f"free-cloud: route generate() calls via {cfg['endpoint']} (policy: redacted prompts only)"
    return (f"accelerated-external: route generate() calls via {cfg['endpoint']} "
            f"(optional optimization; results must match local-cpu within tolerance)")


def split_suite(task_ids: list[str], shards: int) -> list[list[str]]:
    """Deterministic sharding for parallel runners (stable order, no data loss)."""
    if shards < 1:
        raise ValueError("shards must be >= 1")
    return [task_ids[i::shards] for i in range(shards)]
