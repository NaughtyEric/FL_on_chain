import numpy as np
import pytest
import torch

from fl_client.clientapp import partition_from_node_config
from fl_client.config import ClientConfig
from fl_client.device import select_device
from fl_client.model import CIFAR100ResNet, COARSE_CLASSES
from fl_client.parameters import load_parameters, save_parameters
from fl_client.training import CoarseLabelDataset, partition_indices


class _FakeDataset:
    """Map-style dataset whose fine labels are 10 apart, i.e. coarse = 2 * index."""

    def __init__(self, size: int) -> None:
        self._size = size

    def __len__(self) -> int:
        return self._size

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        return torch.zeros(3, 32, 32), index * 10


def test_partition_is_deterministic_and_disjoint():
    parts = [set(partition_indices(20, i, 4, 7)) for i in range(4)]
    assert parts == [set(partition_indices(20, i, 4, 7)) for i in range(4)]
    assert not (parts[0] & parts[1])
    assert set.union(*parts) == set(range(20))


def test_device_cpu():
    assert select_device("cpu").type == "cpu"


def test_config_requires_valid_partition():
    with pytest.raises(ValueError):
        ClientConfig(num_partitions=0).validate()
    with pytest.raises(ValueError):
        ClientConfig(partition_id=2, num_partitions=2).validate()
    with pytest.raises(ValueError):
        ClientConfig(learning_rate=0.0).validate()
    with pytest.raises(ValueError):
        ClientConfig(weight_decay=-0.1).validate()
    with pytest.raises(ValueError):
        ClientConfig(momentum=1.0).validate()
    with pytest.raises(ValueError):
        ClientConfig(batch_size=0).validate()
    ClientConfig(partition_id=1, num_partitions=2).validate()  # valid boundary


def test_partition_from_node_config():
    cfg = partition_from_node_config({"partition-id": "2", "num-partitions": "4"})
    assert cfg.partition_id == 2
    assert cfg.num_partitions == 4
    cfg.validate()
    # Missing keys fall back to env defaults (partition 0 of 1).
    assert partition_from_node_config({}).partition_id == 0
    assert partition_from_node_config({}).num_partitions == 1
    # Out-of-range node config is rejected at validate() time by client_fn.
    with pytest.raises(ValueError):
        partition_from_node_config({"partition-id": "5", "num-partitions": "4"}).validate()


def test_coarse_label_dataset_maps_fine_to_coarse():
    wrapped = CoarseLabelDataset(_FakeDataset(10))
    assert len(wrapped) == 10
    assert [wrapped[i][1] for i in range(10)] == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]


def test_model_defaults_to_coarse_classes():
    model = CIFAR100ResNet()
    assert model.fc.out_features == COARSE_CLASSES
    assert model(torch.zeros(1, 3, 32, 32)).shape == (1, COARSE_CLASSES)


def test_save_and_load_parameters_roundtrip(tmp_path):
    arrays = [
        np.arange(12, dtype=np.float32).reshape(3, 4),
        np.array([0.5, 1.5], dtype=np.float64),
    ]
    path = save_parameters(arrays, tmp_path / "params.npz")
    assert path.is_file()
    loaded = load_parameters(path)
    assert len(loaded) == len(arrays)
    assert [a.shape for a in loaded] == [a.shape for a in arrays]
    assert [a.dtype for a in loaded] == [a.dtype for a in arrays]
    np.testing.assert_array_equal(loaded[0], arrays[0])
    np.testing.assert_array_equal(loaded[1], arrays[1])
