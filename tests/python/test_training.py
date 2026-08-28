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


def test_grad_clipping_bounds_the_update():
    """With an extreme clip threshold the SGD update magnitude is bounded by
    lr * max_grad_norm per step (weight decay/momentum disabled to isolate it)."""
    torch.manual_seed(0)
    device = torch.device("cpu")
    model = CIFAR100ResNet(num_classes=COARSE_CLASSES).to(device)
    before = [p.detach().clone() for p in model.parameters()]
    max_grad_norm = 1e-3
    lr = 0.1
    loader = _tiny_loader(8)  # batch_size=8 -> exactly 1 step
    train(
        model, loader, device, epochs=1, learning_rate=lr,
        weight_decay=0.0, momentum=0.0, max_grad_norm=max_grad_norm,
    )
    total_update_sq = sum(
        (p.detach() - b).pow(2).sum().item()
        for p, b in zip(model.parameters(), before)
    )
    assert math.sqrt(total_update_sq) <= lr * max_grad_norm * 1.01


def test_grad_clipping_disabled_with_zero():
    """max_grad_norm=0 keeps the unclipped path working."""
    device = torch.device("cpu")
    model = CIFAR100ResNet(num_classes=COARSE_CLASSES).to(device)
    loss = train(model, _tiny_loader(), device, epochs=1, learning_rate=0.1, max_grad_norm=0.0)
    assert math.isfinite(loss)
