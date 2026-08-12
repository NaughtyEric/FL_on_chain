import pytest
import torch

from fl_client.config import ClientConfig
from fl_client.device import select_device
from fl_client.model import CIFAR100Model, COARSE_CLASSES
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


def test_config_requires_identity_and_server():
    with pytest.raises(ValueError):
        ClientConfig(server_address="", client_id="").validate()
    with pytest.raises(ValueError):
        ClientConfig(server_address="localhost:8080", client_id="").validate()


def test_tls_files_must_be_complete(tmp_path):
    ca = tmp_path / "ca.pem"
    ca.write_text("test")
    with pytest.raises(ValueError):
        ClientConfig("server", "client", ca_cert=ca).validate()


def test_coarse_label_dataset_maps_fine_to_coarse():
    wrapped = CoarseLabelDataset(_FakeDataset(10))
    assert len(wrapped) == 10
    assert [wrapped[i][1] for i in range(10)] == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]


def test_model_defaults_to_coarse_classes():
    model = CIFAR100Model()
    assert model.classifier.out_features == COARSE_CLASSES
    assert model(torch.zeros(1, 3, 32, 32)).shape == (1, COARSE_CLASSES)
