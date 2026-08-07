from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClientConfig:
    server_address: str
    client_id: str
    data_dir: Path = Path("data")
    partition_id: int = 0
    num_partitions: int = 1
    seed: int = 42
    batch_size: int = 64
    local_epochs: int = 1
    learning_rate: float = 0.01
    num_workers: int = 0
    device: str = "auto"
    download: bool = False
    ca_cert: Path | None = None
    client_cert: Path | None = None
    client_key: Path | None = None

    @classmethod
    def from_env(cls) -> "ClientConfig":
        def optional_path(name: str) -> Path | None:
            value = os.getenv(name)
            return Path(value) if value else None

        return cls(
            server_address=os.environ.get("FL_SERVER_ADDRESS", ""),
            client_id=os.environ.get("FL_CLIENT_ID", ""),
            data_dir=Path(os.getenv("FL_DATA_DIR", "data")),
            partition_id=int(os.getenv("FL_PARTITION_ID", "0")),
            num_partitions=int(os.getenv("FL_NUM_PARTITIONS", "1")),
            seed=int(os.getenv("FL_SEED", "42")),
            batch_size=int(os.getenv("FL_BATCH_SIZE", "64")),
            local_epochs=int(os.getenv("FL_LOCAL_EPOCHS", "1")),
            learning_rate=float(os.getenv("FL_LEARNING_RATE", "0.01")),
            num_workers=int(os.getenv("FL_NUM_WORKERS", "0")),
            device=os.getenv("FL_DEVICE", "auto"),
            download=os.getenv("FL_DOWNLOAD", "false").lower() == "true",
            ca_cert=optional_path("FL_CA_CERT"),
            client_cert=optional_path("FL_CLIENT_CERT"),
            client_key=optional_path("FL_CLIENT_KEY"),
        )

    def validate(self, require_server: bool = True) -> None:
        if require_server and not self.server_address:
            raise ValueError("FL_SERVER_ADDRESS must be configured")
        if not self.client_id:
            raise ValueError("FL_CLIENT_ID must be configured")
        if self.num_partitions < 1 or not 0 <= self.partition_id < self.num_partitions:
            raise ValueError("partition_id must be within num_partitions")
        if self.batch_size < 1 or self.local_epochs < 1 or self.num_workers < 0:
            raise ValueError("batch size, epochs, and workers have invalid values")
        if self.learning_rate <= 0:
            raise ValueError("learning rate must be positive")
        certs = (self.ca_cert, self.client_cert, self.client_key)
        if any(certs) and not all(certs):
            raise ValueError("CA, client certificate, and client key must be configured together")
        for path in certs:
            if path is not None:
                if not path.is_file():
                    raise ValueError(f"TLS file does not exist: {path}")
                if not os.access(path, os.R_OK):
                    raise ValueError(f"TLS file is not readable: {path}")
