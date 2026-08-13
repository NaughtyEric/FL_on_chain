# CLAUDE.md

## 仓库概览

在区块链上实现联邦学习的起步代码库。

- `src/python` — Flower 客户端/服务端，PyTorch 本地训练 CIFAR-100（20 个粗粒度标签）。
  - 客户端详见 `src/python/fl_client/CLAUDE.md`
  - 服务端详见 `src/python/fl_server/CLAUDE.md`
- `src/eth` — 以太坊智能合约（L1/L2 框架，未实现），见 `src/eth/CLAUDE.md`。
- `scripts/` — 本地多客户端仿真，见 `scripts/CLAUDE.md`。

## 约定

- 除非显式改设计，保持现有 row-major 张量存储意图。
- 新增功能时，同一次改动附带对应的可执行/测试/构建配置。
