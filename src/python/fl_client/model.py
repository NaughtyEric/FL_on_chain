from __future__ import annotations

import torch
from torch import nn


# CIFAR-100 coarse (superclass) label count. The fine labels are ordered so
# each coarse class spans five consecutive fine labels, hence coarse = fine // 5.
COARSE_CLASSES = 20


class CIFAR100Model(nn.Module):
    """Small convolutional model for CIFAR-100 coarse-label classification.

    Defaults to the 20 superclass (coarse) labels; pass ``num_classes``
    explicitly for fine-grained (100-class) training.
    """

    def __init__(self, num_classes: int = COARSE_CLASSES) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d(1),
        )
        self.classifier = nn.Linear(128, num_classes)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(inputs).flatten(1))
