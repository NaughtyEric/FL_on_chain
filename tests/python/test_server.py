import flwr as fl
import pytest

from fl_client.model import CIFAR100Model, COARSE_CLASSES
from fl_server.config import ServerConfig
from fl_server.server import (
    build_strategy,
    initial_parameters,
    weighted_average,
    weighted_loss,
)


def test_server_config_requires_address_and_rounds():
    with pytest.raises(ValueError):
        ServerConfig(server_address="", num_rounds=3).validate()
    with pytest.raises(ValueError):
        ServerConfig(server_address="localhost:8080", num_rounds=0).validate()


def test_server_config_fraction_bounds():
    with pytest.raises(ValueError):
        ServerConfig(server_address="a", num_rounds=1, fraction_fit=0.0).validate()
    with pytest.raises(ValueError):
        ServerConfig(server_address="a", num_rounds=1, fraction_fit=1.5).validate()
    with pytest.raises(ValueError):
        ServerConfig(server_address="a", num_rounds=1, fraction_evaluate=-0.1).validate()


def test_server_config_min_clients_consistency():
    with pytest.raises(ValueError):
        ServerConfig(server_address="a", num_rounds=1, min_available_clients=1, min_fit_clients=2).validate()
    with pytest.raises(ValueError):
        ServerConfig(server_address="a", num_rounds=1, min_available_clients=1, min_evaluate_clients=2).validate()
    with pytest.raises(ValueError):
        ServerConfig(server_address="a", num_rounds=1, fraction_evaluate=0.0, min_evaluate_clients=1).validate()


def test_tls_files_must_be_complete(tmp_path):
    ca = tmp_path / "ca.pem"
    ca.write_text("test")
    with pytest.raises(ValueError):
        ServerConfig("localhost:8080", 1, ca_cert=ca).validate()


def test_initial_parameters_match_model():
    parameters = initial_parameters()
    arrays = fl.common.parameters_to_ndarrays(parameters)
    state = CIFAR100Model(num_classes=COARSE_CLASSES).state_dict()
    assert len(arrays) == len(state)
    assert all(tuple(array.shape) == tuple(value.shape) for array, value in zip(arrays, state.values()))


def test_build_strategy_wires_config():
    strategy = build_strategy(ServerConfig(min_available_clients=3, min_fit_clients=2, min_evaluate_clients=2))
    assert isinstance(strategy, fl.server.strategy.FedAvg)
    assert strategy.min_available_clients == 3
    assert strategy.min_fit_clients == 2
    assert strategy.min_evaluate_clients == 2
    assert strategy.initial_parameters is not None
    assert strategy.evaluate_metrics_aggregation_fn is weighted_average
    assert strategy.fit_metrics_aggregation_fn is weighted_loss


def test_weighted_average():
    assert weighted_average([(10, {"accuracy": 0.5}), (30, {"accuracy": 0.9})]) == {"accuracy": 0.8}
    assert weighted_average([]) == {"accuracy": 0.0}


def test_weighted_loss():
    assert weighted_loss([(10, {"loss": 1.0}), (30, {"loss": 2.0})]) == {"loss": 1.75}
    assert weighted_loss([]) == {"loss": 0.0}
