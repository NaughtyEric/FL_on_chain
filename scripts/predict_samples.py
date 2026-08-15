#!/usr/bin/env python
"""Classify random CIFAR-100 test images with the FedAsync-trained global model.

Loads the parameters dumped by the ServerApp (default ``artifacts/global_parameters.npz``,
see ``fl_server``) into ``CIFAR100Model``, then runs inference on ``--num`` randomly
sampled test images and prints predicted vs. true coarse (superclass) labels.

Run from the repo root with the venv python:
    .venv/Scripts/python scripts/predict_samples.py [--num 8] [--seed 0] [--weights PATH]
"""

from __future__ import annotations

import argparse
import random

import torch

from fl_client.dataset import load_cifar100
from fl_client.device import select_device
from fl_client.model import CIFAR100ResNet, COARSE_CLASSES
from fl_client.parameters import load_parameters, set_parameters

# CIFAR-100 coarse (superclass) labels in coarse-id order (0..19).
COARSE_LABELS = [
    "aquatic_mammals",
    "fish",
    "flowers",
    "food_containers",
    "fruit_and_vegetables",
    "household_electrical_devices",
    "household_furniture",
    "insects",
    "large_carnivores",
    "large_man-made_outdoor_things",
    "large_natural_outdoor_scenes",
    "large_omnivores_and_herbivores",
    "medium_mammals",
    "non-insect_invertebrates",
    "people",
    "reptiles",
    "small_mammals",
    "trees",
    "vehicles_1",
    "vehicles_2",
]

def main() -> None:
    parser = argparse.ArgumentParser(description="Test random CIFAR-100 images with the trained model.")
    parser.add_argument("--weights", default="artifacts/global_parameters.npz",
                        help="path to the .npz dump from the ServerApp")
    parser.add_argument("--num", type=int, default=8, help="number of images to sample (default 8)")
    parser.add_argument("--seed", type=int, default=0, help="RNG seed for reproducible sampling (default 0)")
    parser.add_argument("--data-dir", default="data/cifar100",
                        help="HuggingFace CIFAR-100 arrow directory (default data/cifar100)")
    args = parser.parse_args()

    device = select_device("auto")
    model = CIFAR100ResNet(num_classes=COARSE_CLASSES).to(device)
    set_parameters(model, load_parameters(args.weights))
    model.eval()

    # Uses the same transform as training (fl_client.dataset.CIFAR_TRANSFORM).
    test_set = load_cifar100(args.data_dir, split="test")
    rng = random.Random(args.seed)
    indices = rng.sample(range(len(test_set)), args.num)

    print(f"testing {args.num} random images from CIFAR-100 test set (seed={args.seed}) on {device}")
    print(f"{'index':>6}  {'true':<32} {'pred':<32} {'conf':>6}")
    correct = 0
    for index in indices:
        image, true_coarse = test_set[index]
        with torch.no_grad():
            logits = model(image.unsqueeze(0).to(device))
        probs = torch.softmax(logits, dim=1)[0]
        pred = int(probs.argmax())
        conf = float(probs[pred])
        ok = pred == true_coarse
        correct += int(ok)
        print(f"{index:>6}  {COARSE_LABELS[true_coarse]:<32} {COARSE_LABELS[pred]:<32} {conf:>6.1%} {'OK' if ok else 'X'}")

    print(f"\n{correct}/{args.num} correct on the sampled images")


if __name__ == "__main__":
    main()
