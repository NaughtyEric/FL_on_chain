from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ServerConfig:
    server_address: str = "[::]:8080"
    num_rounds: int = 3
    fraction_fit: float = 1.0
    fraction_evaluate: float = 1.0
    min_available_clients: int = 2
    min_fit_clients: int = 2
    min_evaluate_clients: int = 2
    ca_cert: Path | None = None
    server_cert: Path | None = None
    server_key: Path | None = None

    @classmethod
    def from_env(cls) -> "ServerConfig":
        def optional_path(name: str) -> Path | None:
            value = os.getenv(name)
            return Path(value) if value else None

        return cls(
            server_address=os.environ.get("FL_SERVER_ADDRESS", "[::]:8080"),
            num_rounds=int(os.getenv("FL_NUM_ROUNDS", "3")),
            fraction_fit=float(os.getenv("FL_FRACTION_FIT", "1.0")),
            fraction_evaluate=float(os.getenv("FL_FRACTION_EVALUATE", "1.0")),
            min_available_clients=int(os.getenv("FL_MIN_AVAILABLE_CLIENTS", "2")),
            min_fit_clients=int(os.getenv("FL_MIN_FIT_CLIENTS", "2")),
            min_evaluate_clients=int(os.getenv("FL_MIN_EVALUATE_CLIENTS", "2")),
            ca_cert=optional_path("FL_CA_CERT"),
            server_cert=optional_path("FL_SERVER_CERT"),
            server_key=optional_path("FL_SERVER_KEY"),
        )

    def validate(self) -> None:
        if not self.server_address:
            raise ValueError("FL_SERVER_ADDRESS must be configured")
        if self.num_rounds < 1:
            raise ValueError("num_rounds must be at least 1")
        if not 0 < self.fraction_fit <= 1:
            raise ValueError("fraction_fit must be in (0, 1]")
        if not 0 <= self.fraction_evaluate <= 1:
            raise ValueError("fraction_evaluate must be in [0, 1]")
        if self.min_fit_clients < 1:
            raise ValueError("min_fit_clients must be at least 1")
        if self.min_evaluate_clients < 0:
            raise ValueError("min_evaluate_clients must be non-negative")
        if self.min_available_clients < max(self.min_fit_clients, self.min_evaluate_clients):
            raise ValueError("min_available_clients must cover min_fit_clients and min_evaluate_clients")
        if self.fraction_evaluate == 0.0 and self.min_evaluate_clients > 0:
            raise ValueError("min_evaluate_clients must be 0 when evaluation is disabled")
        certs = (self.ca_cert, self.server_cert, self.server_key)
        if any(certs) and not all(certs):
            raise ValueError("CA, server certificate, and server key must be configured together")
        for path in certs:
            if path is not None:
                if not path.is_file():
                    raise ValueError(f"TLS file does not exist: {path}")
                if not os.access(path, os.R_OK):
                    raise ValueError(f"TLS file is not readable: {path}")
