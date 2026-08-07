# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## Repository status

这是一个用于 在区块链上实现联邦学习的代码库。代码位于`src`中，且目前仍处于起步阶段。

## Commands

The project now uses CMake and CTest. Configure and build from the repository root with:

```text
cmake -S . -B build
cmake --build build --config Release
ctest --test-dir build --output-on-failure -C Release
```

The focused test executable is `tensor_tests`; run it directly from the generated build directory when needed. There is no lint configuration yet.

CPU Tensor support is implemented and tested. CUDA/GPU is only a backend-ready boundary at this stage; no CUDA kernels or toolkit dependency are present. NPU is reserved as an explicit backend value, but selecting it throws an unavailable-backend error; do not describe it as implemented.

## Python Flower client

The Python client is an independent package under `src/python/fl_client`; it does not use the C++ Tensor library because no Python bindings exist. It uses PyTorch/torchvision for local CIFAR-100 training and Flower for client callbacks. The package supports automatic CPU/CUDA/MPS selection, deterministic dataset partitioning, and model parameter validation. The Flower server and blockchain integration are not implemented yet.

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


- `src/cpp/utils`包括了C++的工具代码，且目前实现未完成
- `src/eth`包括以太坊智能合约代码，目前为空，未来需要写入

## Working conventions specific to this codebase

- Keep public declarations in `src/cpp/utils/tensor.hpp` synchronized with definitions in `src/cpp/utils/tensor.cpp`.
- Preserve the current row-major tensor-storage intent unless the design is explicitly changed.
- When adding functionality, add the corresponding executable/test/build configuration as part of the same change; there is currently no established harness for running a single test.