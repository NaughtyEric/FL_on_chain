from __future__ import annotations

import flwr as fl

from fl_client.model import CIFAR100Model, COARSE_CLASSES
from fl_client.parameters import get_parameters

from .config import ServerConfig


def initial_parameters() -> fl.common.Parameters:
    """Fresh CIFAR-100 coarse-label model weights to seed the first round.

    Must match the model shape the clients train on, so the coarse class
    count is shared with ``fl_client`` rather than duplicated.
    """
    return fl.common.ndarrays_to_parameters(get_parameters(CIFAR100Model(num_classes=COARSE_CLASSES)))


def weighted_average(metrics: list[tuple[int, dict]]) -> dict:
    """Aggregate per-client "accuracy" weighted by the number of examples."""
    total = sum(num_examples for num_examples, _ in metrics)
    if total == 0:
        return {"accuracy": 0.0}
    values = [num_examples * float(entry["accuracy"]) for num_examples, entry in metrics]
    return {"accuracy": sum(values) / total}


def weighted_loss(metrics: list[tuple[int, dict]]) -> dict:
    """Aggregate per-client "loss" weighted by the number of examples."""
    total = sum(num_examples for num_examples, _ in metrics)
    if total == 0:
        return {"loss": 0.0}
    values = [num_examples * float(entry["loss"]) for num_examples, entry in metrics]
    return {"loss": sum(values) / total}


def build_strategy(config: ServerConfig) -> fl.server.strategy.Strategy:
    return fl.server.strategy.FedAvg(
        fraction_fit=config.fraction_fit,
        fraction_evaluate=config.fraction_evaluate,
        min_available_clients=config.min_available_clients,
        min_fit_clients=config.min_fit_clients,
        min_evaluate_clients=config.min_evaluate_clients,
        initial_parameters=initial_parameters(),
        fit_metrics_aggregation_fn=weighted_loss,
        evaluate_metrics_aggregation_fn=weighted_average,
    )


def tls_credentials(config: ServerConfig) -> tuple[bytes, bytes, bytes] | None:
    """Read the (CA, server cert, server key) triple for Flower TLS.

    Only active in production: pass all three cert paths via the environment
    (``FL_CA_CERT`` / ``FL_SERVER_CERT`` / ``FL_SERVER_KEY``). Local debugging
    leaves them unset, so ``certificates=None`` disables TLS entirely.
    """
    if config.ca_cert is None:
        return None
    assert config.server_cert is not None and config.server_key is not None
    return (
        config.ca_cert.read_bytes(),
        config.server_cert.read_bytes(),
        config.server_key.read_bytes(),
    )


def run_server(config: ServerConfig) -> fl.server.history.History:
    config.validate()
    return fl.server.start_server(
        server_address=config.server_address,
        config=fl.server.ServerConfig(num_rounds=config.num_rounds),
        strategy=build_strategy(config),
        certificates=tls_credentials(config),
    )
