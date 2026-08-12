from __future__ import annotations

import argparse

from .config import ServerConfig
from .server import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Flower server for federated CIFAR-100 training")
    parser.add_argument("--server-address", default="[::]:8080")
    parser.add_argument("--num-rounds", type=int, default=3)
    parser.add_argument("--fraction-fit", type=float, default=1.0)
    parser.add_argument("--fraction-evaluate", type=float, default=1.0)
    parser.add_argument("--min-available-clients", type=int, default=2)
    parser.add_argument("--min-fit-clients", type=int, default=2)
    parser.add_argument("--min-evaluate-clients", type=int, default=2)
    args = parser.parse_args()
    config = ServerConfig(
        server_address=args.server_address,
        num_rounds=args.num_rounds,
        fraction_fit=args.fraction_fit,
        fraction_evaluate=args.fraction_evaluate,
        min_available_clients=args.min_available_clients,
        min_fit_clients=args.min_fit_clients,
        min_evaluate_clients=args.min_evaluate_clients,
    )
    config.validate()
    run_server(config)


if __name__ == "__main__":
    main()
