# CLAUDE.md

区块链上的联邦学习起步代码库。

- `src/python` — Flower 客户端/服务端，PyTorch 训练 CIFAR-100（20 粗粒度类），子目录各有 CLAUDE.md。
- `src/eth` — 以太坊 L1/L2 合约（部分实现），见 `src/eth/CLAUDE.md`。
- `scripts/` — 本地多客户端仿真 + 本地链/存储，见 `scripts/CLAUDE.md`。

## 约定

- 除非显式改设计，保持现有 row-major 张量存储意图。
- 新增功能时，同一次改动附带对应的可执行/测试/构建配置。
- `paper/` 与 `reference/` 为论文/笔记，如无指令无需阅读。
