from pathlib import Path

import flwr as fl
import pytest

from fl_client.model import CIFAR100ResNet, COARSE_CLASSES
from fl_client.parameters import get_parameters, save_parameters
from fl_server.fedasync import AsyncConfig, _parse_optional_path
from fl_server.serverapp import initial_parameters, weighted_average, weighted_loss


def test_async_config_validation():
    AsyncConfig().validate()
    with pytest.raises(ValueError):
        AsyncConfig(num_steps=0).validate()
    with pytest.raises(ValueError):
        AsyncConfig(staleness_fn="quadratic").validate()


def test_parse_optional_path():
    assert _parse_optional_path(None) is None
    assert _parse_optional_path("") is None
    assert _parse_optional_path("-1") is None
    assert _parse_optional_path("none") is None
    assert _parse_optional_path("artifacts/pretrained.npz") == Path("artifacts/pretrained.npz")


def test_initial_parameters_match_model():
    parameters = initial_parameters()
    arrays = fl.common.parameters_to_ndarrays(parameters)
    state = CIFAR100ResNet(num_classes=COARSE_CLASSES).state_dict()
    assert len(arrays) == len(state)
    assert all(tuple(array.shape) == tuple(value.shape) for array, value in zip(arrays, state.values()))


def test_initial_parameters_loads_checkpoint(tmp_path):
    checkpoint = tmp_path / "init.npz"
    save_parameters(get_parameters(CIFAR100ResNet(num_classes=COARSE_CLASSES)), checkpoint)
    parameters = initial_parameters(checkpoint)
    arrays = fl.common.parameters_to_ndarrays(parameters)
    state = CIFAR100ResNet(num_classes=COARSE_CLASSES).state_dict()
    assert len(arrays) == len(state)
    assert all(tuple(array.shape) == tuple(value.shape) for array, value in zip(arrays, state.values()))


def test_initial_parameters_ignores_missing_checkpoint(tmp_path):
    # Missing path falls back to random init without raising.
    parameters = initial_parameters(tmp_path / "does-not-exist.npz")
    assert len(fl.common.parameters_to_ndarrays(parameters)) == len(
        CIFAR100ResNet(num_classes=COARSE_CLASSES).state_dict()
    )


def test_weighted_average():
    assert weighted_average([(10, {"accuracy": 0.5}), (30, {"accuracy": 0.9})]) == {"accuracy": 0.8}
    assert weighted_average([]) == {"accuracy": 0.0}


def test_weighted_loss():
    assert weighted_loss([(10, {"loss": 1.0}), (30, {"loss": 2.0})]) == {"loss": 1.75}
    assert weighted_loss([]) == {"loss": 0.0}
