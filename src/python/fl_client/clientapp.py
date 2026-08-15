"""Flower ClientApp wrapper around :class:`FlowerClient`.

``client_fn`` is invoked once per message by the ClientApp runtime, so the
CIFAR-100 dataset (HuggingFace arrow format under ``data/cifar100``) is memoized
per ``data_dir`` to avoid re-loading the arrow files on every message.
Partitioning comes from the SuperNode's ``--node-config "partition-id=... num-partitions=..."``,
read off ``context.node_config``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Optional

import flwr as fl
from flwr.app import Context, UserConfigValue
from flwr.clientapp import ClientApp

from .client import FlowerClient
from .config import ClientConfig
from .dataset import CIFAR100CoarseDataset, load_cifar100

_datasets: dict[str, CIFAR100CoarseDataset] = {}


def _load_dataset(data_dir: str) -> CIFAR100CoarseDataset:
    key = str(data_dir)
    if key not in _datasets:
        _datasets[key] = load_cifar100(data_dir)
    return _datasets[key]


def partition_from_node_config(
    node_config: Mapping[str, UserConfigValue], base: Optional[ClientConfig] = None
) -> ClientConfig:
    """Merge the SuperNode ``--node-config`` partition fields into a base config."""
    return replace(
        base or ClientConfig.from_env(),
        partition_id=int(node_config.get("partition-id", 0)),
        num_partitions=int(node_config.get("num-partitions", 1)),
    )


def client_fn(context: Context) -> fl.client.Client:
    """Build a typed Flower client for the node the SuperLink assigned this message."""
    config = partition_from_node_config(context.node_config)
    config.validate()
    dataset = _load_dataset(str(config.data_dir))
    return FlowerClient(config, dataset).to_client()


app = ClientApp(client_fn=client_fn)
