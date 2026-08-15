from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClientConfig:
    data_dir: Path = Path("data/cifar100")
    partition_id: int = 0
    num_partitions: int = 1
    seed: int = 42
    batch_size: int = 64
    local_epochs: int = 1
    learning_rate: float = 0.01
    num_workers: int = 0
    device: str = "auto"

    @classmethod
    def from_env(cls) -> "ClientConfig":
        return cls(
            data_dir=Path(os.getenv("FL_DATA_DIR", "data/cifar100")),
            partition_id=int(os.getenv("FL_PARTITION_ID", "0")),
            num_partitions=int(os.getenv("FL_NUM_PARTITIONS", "1")),
            seed=int(os.getenv("FL_SEED", "42")),
            batch_size=int(os.getenv("FL_BATCH_SIZE", "64")),
            local_epochs=int(os.getenv("FL_LOCAL_EPOCHS", "1")),
            learning_rate=float(os.getenv("FL_LEARNING_RATE", "0.01")),
            num_workers=int(os.getenv("FL_NUM_WORKERS", "0")),
            device=os.getenv("FL_DEVICE", "auto"),
        )

    def validate(self) -> None:
        if self.num_partitions < 1:
            raise ValueError("num_partitions must be at least 1")
        if not 0 <= self.partition_id < self.num_partitions:
            raise ValueError("partition_id must be within num_partitions")
        if self.batch_size < 1 or self.local_epochs < 1 or self.num_workers < 0:
            raise ValueError("batch size, epochs, and workers have invalid values")
        if self.learning_rate <= 0:
            raise ValueError("learning rate must be positive")
