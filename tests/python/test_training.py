import math

import torch
from torch.utils.data import DataLoader, TensorDataset

from fl_client.model import CIFAR100ResNet, COARSE_CLASSES
from fl_client.training import evaluate, train


def _tiny_loader(n: int = 16) -> DataLoader:
    inputs = torch.randn(n, 3, 32, 32)
    targets = torch.randint(0, COARSE_CLASSES, (n,))
    return DataLoader(TensorDataset(inputs, targets), batch_size=8)


def test_train_and_evaluate_on_cpu():
    """Smoke test for the CPU (AMP-disabled) path of train/evaluate."""
    device = torch.device("cpu")
    model = CIFAR100ResNet(num_classes=COARSE_CLASSES).to(device)
    loss = train(model, _tiny_loader(), device, epochs=1, learning_rate=0.1)
    assert math.isfinite(loss)
    eval_loss, accuracy = evaluate(model, _tiny_loader(), device)
    assert math.isfinite(eval_loss)
    assert 0.0 <= accuracy <= 1.0
    # Training on random data still lowers the (finite) loss a bit.
    assert loss < 5.0
