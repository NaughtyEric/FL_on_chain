import PIL.Image
import torch

from fl_client.dataset import CIFAR100CoarseDataset, CIFAR_TRANSFORM


class _FakeHF:
    """Minimal stand-in for a HuggingFace split row: ``img`` + ``coarse_label``."""

    def __init__(self, size: int, labels: list[int]) -> None:
        self._size = size
        self._labels = labels

    def __len__(self) -> int:
        return self._size

    def __getitem__(self, index: int) -> dict:
        return {
            "img": PIL.Image.new("RGB", (32, 32), color=(index % 256, 0, 0)),
            "coarse_label": self._labels[index],
        }


def test_len_and_coarse_labels_verbatim():
    labels = [4, 4, 19, 0]
    ds = CIFAR100CoarseDataset(_FakeHF(len(labels), labels))
    assert len(ds) == 4
    assert [ds[i][1] for i in range(4)] == labels  # coarse taken as-is, not fine // 5


def test_transform_applied():
    ds = CIFAR100CoarseDataset(_FakeHF(2, [3, 7]), CIFAR_TRANSFORM)
    image, coarse = ds[1]
    assert isinstance(image, torch.Tensor)
    assert image.shape == (3, 32, 32)
    assert image.dtype == torch.float32
    assert coarse == 7


def test_no_transform_returns_pil():
    ds = CIFAR100CoarseDataset(_FakeHF(1, [0]))
    image, coarse = ds[0]
    assert isinstance(image, PIL.Image.Image)
    assert coarse == 0
