import pytest

from fl_client.config import ClientConfig
from fl_client.device import select_device
from fl_client.training import partition_indices


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
