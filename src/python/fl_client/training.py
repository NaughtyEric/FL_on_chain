from __future__ import annotations

from typing import Any, Protocol

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset


class IndexableDataset(Protocol):
    """A map-style dataset: sized and indexable by integer position."""

    def __len__(self) -> int: ...

    def __getitem__(self, index: int) -> Any: ...


class CoarseLabelDataset(Dataset):
    """Wrap a CIFAR-100 dataset to expose coarse (superclass) labels.
    """

    def __init__(self, dataset: IndexableDataset) -> None:
        self.dataset = dataset

    def __len__(self) -> int:
        return len(self.dataset)

    def __getitem__(self, index: int) -> tuple[object, int]:
        inputs, fine_label = self.dataset[index]
        return inputs, int(fine_label) // 5


def partition_indices(length: int, partition_id: int, num_partitions: int, seed: int) -> list[int]:
    if length < 1 or num_partitions < 1 or not 0 <= partition_id < num_partitions:
        raise ValueError("invalid partition arguments")
    generator = torch.Generator().manual_seed(seed)
    indices = torch.randperm(length, generator=generator).tolist()
    return indices[partition_id::num_partitions]


def train(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    epochs: int,
    learning_rate: float,
    weight_decay: float = 5e-4,
    momentum: float = 0.9,
) -> float:
    """Train with SGD + momentum + weight decay (ResNet-friendly recipe).

    Weight decay and momentum default to the same values used by
    ``scripts/pretrain_model.py`` so FL fine-tuning is consistent with the
    pre-training run.
    """
    model.train()
    optimizer = torch.optim.SGD(
        model.parameters(), lr=learning_rate, momentum=momentum, weight_decay=weight_decay
    )
    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0
    count = 0
    for _ in range(epochs):
        for inputs, targets in loader:
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(inputs), targets)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * inputs.size(0)
            count += inputs.size(0)
    return total_loss / max(count, 1)


def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> tuple[float, float]:
    model.eval()
    criterion = nn.CrossEntropyLoss()
    loss_total = correct = count = 0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            loss_total += criterion(outputs, targets).item() * inputs.size(0)
            correct += (outputs.argmax(1) == targets).sum().item()
            count += inputs.size(0)
    return loss_total / max(count, 1), correct / max(count, 1)
