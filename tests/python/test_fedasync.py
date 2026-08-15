"""Unit tests for the pure FedAsync math and async-run configuration."""

import math
from pathlib import Path

import numpy as np
import pytest

from fl_server.fedasync import (
    AsyncConfig,
    async_update,
    make_staleness_fn,
    staleness_exp,
    staleness_linear,
    staleness_poly,
)


@pytest.mark.parametrize(
    "fn, expected",
    [
        (staleness_linear(0), 1.0),
        (staleness_linear(1), 0.5),
        (staleness_linear(3), 0.25),
        (staleness_poly(0), 1.0),
        (staleness_poly(1), 0.25),
        (staleness_exp(0, 1.0), 1.0),
        (staleness_exp(1, 2.0), math.exp(-0.5)),
    ],
)
def test_staleness_functions(fn, expected):
    assert fn == pytest.approx(expected)


def test_make_staleness_fn_dispatch():
    assert make_staleness_fn("linear", 1.0)(2) == pytest.approx(staleness_linear(2))
    assert make_staleness_fn("poly", 1.0)(2) == pytest.approx(staleness_poly(2))
    assert make_staleness_fn("exp", 2.0)(1) == pytest.approx(staleness_exp(1, 2.0))
    with pytest.raises(ValueError):
        make_staleness_fn("bogus", 1.0)
    with pytest.raises(ValueError):
        make_staleness_fn("exp", 0.0)  # tau must be positive


def test_async_update_interpolates():
    x = [np.zeros(2, dtype=np.float64)]
    x_u = [np.ones(2, dtype=np.float64)]
    for alpha in (0.0, 0.25, 1.0):
        out = async_update(x, x_u, alpha)
        assert out[0] == pytest.approx(np.full(2, alpha))


def test_async_update_is_staleness_weighted():
    # Alpha = alpha_base * h(s): stale updates move the global model less.
    x = [np.zeros(4, dtype=np.float64)]
    x_u = [np.ones(4, dtype=np.float64)]
    fresh = async_update(x, x_u, 0.5 * staleness_linear(0))
    stale = async_update(x, x_u, 0.5 * staleness_linear(5))
    assert np.sum(fresh[0]) > np.sum(stale[0])


def test_async_config_validation():
    AsyncConfig().validate()  # defaults are valid
    with pytest.raises(ValueError):
        AsyncConfig(num_steps=0).validate()
    with pytest.raises(ValueError):
        AsyncConfig(alpha=0.0).validate()
    with pytest.raises(ValueError):
        AsyncConfig(tau=-1.0).validate()
    with pytest.raises(ValueError):
        AsyncConfig(staleness_fn="quadratic").validate()
    with pytest.raises(ValueError):
        AsyncConfig(staleness_bound=-2).validate()
    with pytest.raises(ValueError):
        AsyncConfig(max_concurrency=0).validate()
    with pytest.raises(ValueError):
        AsyncConfig(min_clients=0).validate()
    with pytest.raises(ValueError):
        AsyncConfig(ttl=0.0).validate()


def test_async_config_staleness_bound_sentinel():
    # TOML has no null: -1 decodes to unbounded (None), real values pass through.
    cfg = AsyncConfig.from_run_config({"staleness_bound": -1})
    assert cfg.staleness_bound is None
    cfg = AsyncConfig.from_run_config({"staleness_bound": 3})
    assert cfg.staleness_bound == 3


def test_async_config_from_run_config_overrides():
    cfg = AsyncConfig.from_run_config(
        {"num_steps": 7, "alpha": 0.9, "staleness_fn": "poly", "ttl": 30.0}
    )
    assert cfg.num_steps == 7
    assert cfg.alpha == 0.9
    assert cfg.staleness_fn == "poly"
    assert cfg.ttl == 30.0
    # Unspecified fields keep their defaults.
    assert cfg.tau == 1.0
    assert cfg.evaluate_every == 5


def test_async_config_from_run_config_none():
    assert AsyncConfig.from_run_config(None) == AsyncConfig.from_run_config({})


def test_async_config_output_path_default_and_overrides():
    assert AsyncConfig().output_path == Path("artifacts/global_parameters.npz")
    assert AsyncConfig.from_run_config({}).output_path == Path("artifacts/global_parameters.npz")
    custom = AsyncConfig.from_run_config({"output_path": "out/model.npz"})
    assert custom.output_path == Path("out/model.npz")
