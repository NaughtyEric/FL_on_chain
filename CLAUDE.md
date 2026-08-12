# CLAUDE.md

## Repository status

这是一个用于在区块链上实现联邦学习的代码库。代码位于`src`中，且目前仍处于起步阶段。

- `src/python`包括客户端和服务端，使用FLower框架。目前测试用CIFAR100。
- `src/eth`包括以太坊智能合约代码，目前为空，未来需要写入

## Python Flower client

The Python client is an independent package under `src/python/fl_client`.

It uses PyTorch/torchvision for local CIFAR-100 training and Flower for client callbacks.

Training targets the 20 coarse (superclass) labels by default. 

The Flower server is implemented as the sibling package `src/python/fl_server`

Blockchain integration is not implemented yet.

Set up and test the client from the repository root:

```text
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install -e ".[test]"
python -m pytest
```

Launch a client only when a compatible Flower server and dataset are available:

```text
python -m fl_client --server-address HOST:PORT --client-id CLIENT_ID --data-dir data --partition-id 0 --num-partitions N
```

For deployment, configure `FL_CA_CERT`, `FL_CLIENT_CERT`, and `FL_CLIENT_KEY` together and validate them before wiring the matching Flower TLS/mTLS connection. Do not disable certificate verification or place credentials in source. NPU support is not implemented; no Python client fallback should claim it is.

## Python Flower server

The server is the sibling package under `src/python/fl_server`, mirroring the client's structure (`config.py` / `server.py` / `__main__.py`). It reuses `fl_client.model.CIFAR100Model` and `fl_client.parameters.get_parameters` for the initial model weights, and aggregates client updates with Flower's `FedAvg` (weighted-average accuracy/loss metrics). It does not use the C++ Tensor library, matching the client.

Set up and test it together with the client from the repository root (same venv and pytest run):

```text
python -m pytest
```

Launch a server when clients are expected to connect:

```text
python -m fl_server --server-address HOST:PORT --num-rounds N --min-available-clients K
```

Config may also come from the environment (`FL_SERVER_ADDRESS`, `FL_NUM_ROUNDS`, `FL_FRACTION_FIT`, `FL_FRACTION_EVALUATE`, `FL_MIN_AVAILABLE_CLIENTS`, `FL_MIN_FIT_CLIENTS`, `FL_MIN_EVALUATE_CLIENTS`). For TLS, configure `FL_CA_CERT`, `FL_SERVER_CERT`, and `FL_SERVER_KEY` together and validate them; they are passed to `start_server` as `certificates=(ca, cert, key)`. TLS is production-only: while any of the three certs is unset the server runs insecure, which is the default for local debugging. Do not disable certificate verification or place credentials in source. Note: the client currently does not present its own credentials, so server-side TLS is not a full mTLS round-trip until that is wired.

## Local multi-client simulation

To debug server+client interaction on a single machine, spawn one server and several clients with `scripts/run_local_fl.sh` (Git Bash on Windows):

```text
bash scripts/run_local_fl.sh   # server + 2 clients, 1 round, TLS off
FL_NUM_CLIENTS=3 FL_NUM_ROUNDS=2 bash scripts/run_local_fl.sh
```

Clients partition CIFAR-100 deterministically via `--partition-id`/`--num-partitions`, so each process trains on a distinct slice of the dataset. The first run downloads CIFAR-100 (~180 MB) into `data/`. See the script header for all environment overrides.


## Working conventions specific to this codebase

- Keep public declarations in `src/cpp/utils/tensor.hpp` synchronized with definitions in `src/cpp/utils/tensor.cpp`.
- Preserve the current row-major tensor-storage intent unless the design is explicitly changed.
- When adding functionality, add the corresponding executable/test/build configuration as part of the same change; there is currently no established harness for running a single test.