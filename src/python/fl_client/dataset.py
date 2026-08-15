"""HuggingFace CIFAR-100 loading for the Flower clients.

The CIFAR-100 dataset is stored in HuggingFace arrow format under
``data/cifar100/`` (train/test ``.arrow`` files plus ``dataset_info.json``).
The ``coarse_label`` feature is the authoritative 20-class superclass label;
the ``img`` feature decodes to a PIL image of shape 32x32 RGB.
"""

from __future__ import annotations

from typing import Any, Optional

from datasets import load_dataset as hf_load_dataset
from torch.utils.data import Dataset
from torchvision import transforms

CIFAR_TRANSFORM = transforms.Compose(
    [
        transforms.ToTensor(),
        transforms.Normalize((0.5071, 0.4867, 0.4408), (0.2675, 0.2565, 0.2761)),
    ]
)


class CIFAR100CoarseDataset(Dataset):
    """Map-style view over a HuggingFace CIFAR-100 split yielding ``(tensor, coarse_label)``.

    The ``img`` feature decodes to a PIL image and is pushed through
    ``transform``; the coarse (superclass) label comes straight from the
    dataset's ``coarse_label`` feature. The fine labels are not ordered in
    consecutive per-superclass runs, so the ``fine // 5`` shortcut does not
    apply to this dataset.
    """

    def __init__(self, hf_dataset: Any, transform: Optional[transforms.Compose] = None) -> None:
        self._hf = hf_dataset
        self._transform = transform

    def __len__(self) -> int:
        return len(self._hf)

    def __getitem__(self, index: int) -> tuple[Any, int]:
        row = self._hf[index]
        image = row["img"]
        if self._transform is not None:
            image = self._transform(image)
        return image, int(row["coarse_label"])


def load_cifar100(data_dir: str, split: str = "train") -> CIFAR100CoarseDataset:
    """Load one CIFAR-100 split from a HuggingFace arrow directory."""
    hf_dataset = hf_load_dataset("arrow", data_dir=str(data_dir))
    return CIFAR100CoarseDataset(hf_dataset[split], CIFAR_TRANSFORM)
