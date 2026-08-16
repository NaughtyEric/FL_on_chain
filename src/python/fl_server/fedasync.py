"""Pure FedAsync math (Xie et al. 2019) and async-run configuration.

FedAsync keeps a global model ``x`` and absorbs each client update ``x_u`` as it
arrives::

    x_{t+1} = (1 - alpha_t) * x_t + alpha_t * x_u
    alpha_t = alpha * h(s, tau)          # s = staleness, tau = exponential decay

where ``h`` is one of the paper's staleness functions (linear / polynomial /
exponential), optionally bounded by clamping ``s`` to ``staleness_bound``.

This module imports nothing from Flower so the math is trivially unit-testable.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Optional

import numpy as np

# TOML has no null, so an unbounded staleness bound is encoded as -1 and mapped
# back to None when parsed.
_STALENESS_BOUND_UNBOUNDED = -1


def _parse_optional_path(value: object) -> Optional[Path]:
    """Parse a path from env/run-config, mapping empty or null markers to None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"-1", "none", "None"}:
        return None
    return Path(text)


def staleness_linear(s: int) -> float:
    """h(s) = 1/(s+1): linear staleness decay from the FedAsync paper."""
    return 1.0 / (s + 1.0)


def staleness_poly(s: int) -> float:
    """h(s) = 1/(s+1)^2: polynomial staleness decay from the FedAsync paper."""
    return 1.0 / ((s + 1.0) ** 2)


def staleness_exp(s: int, tau: float) -> float:
    """h(s) = exp(-s/tau): exponential staleness decay from the FedAsync paper."""
    return math.exp(-s / tau)


StalenessFn = Callable[[int], float]


def make_staleness_fn(name: str, tau: float) -> StalenessFn:
    """Return the staleness function named ``linear``, ``poly`` or ``exp``."""
    if name == "linear":
        return staleness_linear
    if name == "poly":
        return staleness_poly
    if name == "exp":
        if tau <= 0:
            raise ValueError("tau must be positive when staleness_fn is 'exp'")
        return lambda s: staleness_exp(s, tau)
    raise ValueError(f"unknown staleness function: {name!r} (expected linear, poly, or exp)")


def async_update(x: list[np.ndarray], x_u: list[np.ndarray], alpha_t: float) -> list[np.ndarray]:
    """FedAsync single-update rule: ``(1 - alpha_t) * x + alpha_t * x_u``."""
    return [(1.0 - alpha_t) * xi + alpha_t * xu_i for xi, xu_i in zip(x, x_u)]


def _parse_staleness_bound(value: object) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null"}:
        return None
    parsed = int(text)
    return None if parsed == _STALENESS_BOUND_UNBOUNDED else parsed


@dataclass(frozen=True)
class AsyncConfig:
    """Server-side FedAsync hyperparameters, from env or the Flower run config."""

    num_steps: int = 20            # number of async global updates to perform
    alpha: float = 0.5             # base learning rate of the aggregation
    tau: float = 1.0               # decay for the exponential staleness function
    staleness_fn: str = "linear"   # linear | poly | exp
    staleness_bound: Optional[int] = None  # clamp s to this value; None = unbounded
    max_concurrency: int = 2       # max in-flight client updates at once
    min_clients: int = 2           # wait for at least this many nodes before training
    ttl: float = 600.0             # per-message TTL in seconds (slow-client cutoff)
    evaluate_every: int = 5        # run distributed evaluation every N steps (0 = off)
    output_path: Path = Path("artifacts/global_parameters.npz")  # final global model dump
    init_weights: Optional[Path] = None  # .npz checkpoint to seed the global model (None = random)

    @classmethod
    def from_env(cls) -> "AsyncConfig":
        return cls(
            num_steps=int(os.getenv("FL_NUM_STEPS", "20")),
            alpha=float(os.getenv("FL_ALPHA", "0.5")),
            tau=float(os.getenv("FL_TAU", "1.0")),
            staleness_fn=os.getenv("FL_STALENESS_FN", "linear"),
            staleness_bound=_parse_staleness_bound(os.getenv("FL_STALENESS_BOUND", "-1")),
            max_concurrency=int(os.getenv("FL_MAX_CONCURRENCY", "2")),
            min_clients=int(os.getenv("FL_MIN_CLIENTS", "2")),
            ttl=float(os.getenv("FL_TTL", "600.0")),
            evaluate_every=int(os.getenv("FL_EVALUATE_EVERY", "5")),
            output_path=Path(os.getenv("FL_OUTPUT_PATH", "artifacts/global_parameters.npz")),
            init_weights=_parse_optional_path(os.getenv("FL_INIT_WEIGHTS", "")),
        )

    @classmethod
    def from_run_config(cls, run_config: Optional[dict] = None) -> "AsyncConfig":
        """Start from env, then let the Flower run config override each field."""
        cfg = cls.from_env()
        if not run_config:
            return cfg
        return replace(
            cfg,
            num_steps=int(run_config.get("num_steps", cfg.num_steps)),
            alpha=float(run_config.get("alpha", cfg.alpha)),
            tau=float(run_config.get("tau", cfg.tau)),
            staleness_fn=str(run_config.get("staleness_fn", cfg.staleness_fn)),
            staleness_bound=_parse_staleness_bound(
                run_config.get("staleness_bound", _STALENESS_BOUND_UNBOUNDED)
            ),
            max_concurrency=int(run_config.get("max_concurrency", cfg.max_concurrency)),
            min_clients=int(run_config.get("min_clients", cfg.min_clients)),
            ttl=float(run_config.get("ttl", cfg.ttl)),
            evaluate_every=int(run_config.get("evaluate_every", cfg.evaluate_every)),
            output_path=Path(str(run_config.get("output_path", cfg.output_path))),
            init_weights=_parse_optional_path(run_config.get("init_weights", cfg.init_weights)),
        )

    def validate(self) -> None:
        if self.num_steps < 1:
            raise ValueError("num_steps must be at least 1")
        if not 0 < self.alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        if self.tau <= 0:
            raise ValueError("tau must be positive")
        if self.staleness_fn not in {"linear", "poly", "exp"}:
            raise ValueError("staleness_fn must be linear, poly, or exp")
        if self.staleness_bound is not None and self.staleness_bound < 0:
            raise ValueError("staleness_bound must be non-negative or None")
        if self.max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        if self.min_clients < 1:
            raise ValueError("min_clients must be at least 1")
        if self.ttl <= 0:
            raise ValueError("ttl must be positive")
        if self.evaluate_every < 0:
            raise ValueError("evaluate_every must be non-negative")
