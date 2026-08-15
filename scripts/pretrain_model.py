#!/usr/bin/env python
"""Pre-train CIFAR100ResNet on CIFAR-100 coarse labels and dump a .npz checkpoint.

The ServerApp seeds its global model from this checkpoint via ``FL_INIT_WEIGHTS``
(or the ``init_weights`` run config), so the async FL run starts from a sensible
model instead of random initialization. The .npz format matches
``fl_client.parameters.save_parameters`` (one array per layer), which is also
what the server writes at the end of a run.

Device selection follows ``fl_client.device.select_device``: CUDA GPU first,
CPU fallback (no CUDA). On CUDA the run enables ``cudnn.benchmark``, higher
precision float32 matmuls, ``pin_memory`` loaders, worker processes
(``--num-workers``), and mixed precision (AMP) via autocast + GradScaler.
Run from the repo root with the venv python:
    .venv/Scripts/python scripts/pretrain_model.py [--epochs 20] [--batch-size 128] \
        [--num-workers 4] [--lr 0.1] [--data-dir data/cifar100] \
        [--out artifacts/pretrained_cifar100.npz]

Then launch the FL run with the checkpoint:
    FL_INIT_WEIGHTS=artifacts/pretrained_cifar100.npz bash scripts/run_local_fl.sh
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader

from fl_client.dataset import load_cifar100
from fl_client.device import select_device
from fl_client.model import CIFAR100ResNet, COARSE_CLASSES
from fl_client.parameters import get_parameters, save_parameters
from fl_client.training import evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-train CIFAR100ResNet on CIFAR-100 coarse labels.")
    parser.add_argument("--epochs", type=int, default=20, help="training epochs (default 20)")
    parser.add_argument("--batch-size", type=int, default=128, help="batch size (default 128)")
    parser.add_argument("--num-workers", type=int, default=4,
                        help="DataLoader worker processes (default 4)")
    parser.add_argument("--lr", type=float, default=0.1, help="initial SGD learning rate (default 0.1)")
    parser.add_argument("--data-dir", default="data/cifar100",
                        help="HuggingFace CIFAR-100 arrow directory (default data/cifar100)")
    parser.add_argument("--out", default="artifacts/pretrained_cifar100.npz",
                        help="checkpoint path to write (default artifacts/pretrained_cifar100.npz)")
    args = parser.parse_args()

    # Select the device first so loaders can set pin_memory correctly.
    device = select_device("auto")
    print(f"using device {device}")
    pin_memory = device.type == "cuda"
    train_loader = DataLoader(
        load_cifar100(args.data_dir, split="train"),
        batch_size=args.batch_size, shuffle=True,
        num_workers=args.num_workers, pin_memory=pin_memory,
    )
    test_loader = DataLoader(
        load_cifar100(args.data_dir, split="test"),
        batch_size=256, shuffle=False,
        num_workers=args.num_workers, pin_memory=pin_memory,
    )

    model = CIFAR100ResNet(num_classes=COARSE_CLASSES).to(device)
    optimizer = torch.optim.SGD(model.parameters(), lr=args.lr, momentum=0.9, weight_decay=5e-4)
    criterion = nn.CrossEntropyLoss()
    use_amp = device.type == "cuda"  # mixed precision only pays off on NVIDIA GPUs
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    scheduler = torch.optim.lr_scheduler.MultiStepLR(
        optimizer, milestones=[max(1, args.epochs * 2 // 3)], gamma=0.1
    )

    final_acc = 0.0
    for epoch in range(1, args.epochs + 1):
        model.train()
        for inputs, targets in train_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                loss = criterion(model(inputs), targets)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        scheduler.step()
        _, train_acc = evaluate(model, train_loader, device)
        _, final_acc = evaluate(model, test_loader, device)
        print(f"epoch {epoch:>3}: train_acc={train_acc:.3f} test_acc={final_acc:.3f}", flush=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    save_parameters(get_parameters(model), out)
    print(f"saved checkpoint to {out} (test_acc={final_acc:.3f})")


if __name__ == "__main__":
    main()
