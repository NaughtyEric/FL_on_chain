from __future__ import annotations

import flwr as fl
from torch.utils.data import DataLoader, Subset

from .config import ClientConfig
from .dataset import CIFAR100CoarseDataset
from .device import select_device
from .model import CIFAR100ResNet, COARSE_CLASSES
from .parameters import get_parameters, set_parameters
from .training import evaluate, partition_indices, train


class FlowerClient(fl.client.NumPyClient):
    def __init__(self, config: ClientConfig, dataset: CIFAR100CoarseDataset) -> None:
        """``dataset`` is a map-style dataset already yielding ``(inputs, coarse_label)``."""
        config.validate()
        self.config = config
        self.device = select_device(config.device)
        self.model = CIFAR100ResNet(num_classes=COARSE_CLASSES).to(self.device)
        indices = partition_indices(
            len(dataset), config.partition_id, config.num_partitions, config.seed
        )
        self.loader = DataLoader(
            Subset(dataset, indices),
            batch_size=config.batch_size,
            shuffle=True,
            num_workers=config.num_workers,
            pin_memory=self.device.type == "cuda",
        )
        self.sample_count = len(indices)

    def get_parameters(self, config: dict) -> list:
        return get_parameters(self.model)

    def fit(self, parameters: list, config: dict) -> tuple[list, int, dict]:
        set_parameters(self.model, parameters)
        loss = train(
            self.model,
            self.loader,
            self.device,
            self.config.local_epochs,
            self.config.learning_rate,
            weight_decay=self.config.weight_decay,
            momentum=self.config.momentum,
            max_grad_norm=self.config.max_grad_norm,
        )
        return get_parameters(self.model), self.sample_count, {"loss": float(loss)}

    def evaluate(self, parameters: list, config: dict) -> tuple[float, int, dict]:
        set_parameters(self.model, parameters)
        loss, accuracy = evaluate(self.model, self.loader, self.device)
        return float(loss), self.sample_count, {"accuracy": float(accuracy)}
