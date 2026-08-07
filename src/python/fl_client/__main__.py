from __future__ import annotations

import argparse

import flwr as fl
from torchvision import datasets, transforms

from .client import FlowerClient
from .config import ClientConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a secure CIFAR-100 Flower client")
    parser.add_argument("--server-address", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--partition-id", type=int, default=0)
    parser.add_argument("--num-partitions", type=int, default=1)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    config = ClientConfig(
        server_address=args.server_address,
        client_id=args.client_id,
        data_dir=args.data_dir,
        partition_id=args.partition_id,
        num_partitions=args.num_partitions,
        download=args.download,
        device=args.device,
    )
    config.validate()
    dataset = datasets.CIFAR100(
        root=config.data_dir, train=True, download=config.download,
        transform=transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.5071, 0.4867, 0.4408), (0.2675, 0.2565, 0.2761))]),
    )
    client = FlowerClient(config, dataset)
    fl.client.start_numpy_client(server_address=config.server_address, client=client)


if __name__ == "__main__":
    main()
