from __future__ import annotations

import torch
from torch import nn
from torch.utils.data import DataLoader


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
    max_grad_norm: float = 5.0,
) -> float:
    """Train with SGD + momentum + weight decay (ResNet-friendly recipe).

    Weight decay and momentum default to the same values used by
    ``scripts/pretrain_model.py`` so FL fine-tuning is consistent with the
    pre-training run.

    ``max_grad_norm`` clips the global gradient L2 norm each step
    (``min(||g||, tau) * g / ||g||``, cf. DCMF-BFL adaptive clipping with a
    fixed tau); pass 0 to disable. Under AMP the gradients are unscaled
    before clipping so the threshold applies to true gradient magnitudes.
    """
    model.train()
    optimizer = torch.optim.SGD(
        model.parameters(), lr=learning_rate, momentum=momentum, weight_decay=weight_decay
    )
    criterion = nn.CrossEntropyLoss()
    ## nvidia mixed precision training (AMP)
    use_amp = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    total_loss = 0.0
    count = 0
    for _ in range(epochs):
        for inputs, targets in loader:
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                loss = criterion(model(inputs), targets)
            scaler.scale(loss).backward()
            if max_grad_norm > 0:
                scaler.unscale_(optimizer)  # AMP: 还原真实梯度量级后再按范数裁剪
                nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
            scaler.step(optimizer)
            scaler.update()
            total_loss += loss.item() * inputs.size(0)
            count += inputs.size(0)
    return total_loss / max(count, 1)


def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> tuple[float, float]:
    model.eval()
    criterion = nn.CrossEntropyLoss()
    use_amp = device.type == "cuda"
    loss_total = correct = count = 0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs, targets = inputs.to(device), targets.to(device)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                outputs = model(inputs)
            loss_total += criterion(outputs, targets).item() * inputs.size(0)
            correct += (outputs.argmax(1) == targets).sum().item()
            count += inputs.size(0)
    return loss_total / max(count, 1), correct / max(count, 1)
