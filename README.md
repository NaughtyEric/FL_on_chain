# FL on chain

区块链上的联邦学习原型：Flower + PyTorch 做异步联邦学习（CIFAR-100，20 粗粒度类），以太坊 L1/L2 合约做链上账本，外加本地链与内容寻址存储的一键脚本。

| 目录 | 内容 |
| --- | --- |
| `src/python/fl_client` | Flower 客户端：数据集、`CIFAR100ResNet`、训练（SGD + 梯度裁剪）、设备选择 |
| `src/python/fl_server` | Flower ServerApp：FedAsync 异步聚合循环 |
| `src/eth` | Hardhat 工程：`L1FL`（提交 → 挑战 → 确定）、`L2FL`（参与方申请、参数 id 登记） |
| `scripts/` | 本地多节点仿真、本地链（Docker + Anvil）、本地存储、预训练与演示脚本 |

## 环境要求

- Python ≥ 3.10（本仓库在 3.13 上开发）
- Node.js ≥ 20（合约部分，开发用 22）
- Docker（可选，仅本地链 `scripts/chain/` 需要）
- 磁盘约 1.5 GB：CPU 版 torch + 140 MB CIFAR-100

## 快速开始（Python 侧）

```bash
git clone https://github.com/NaughtyEric/FL_on_chain.git
cd FL_on_chain
python -m venv .venv
source .venv/bin/activate          # Windows Git Bash: source .venv/Scripts/activate
python -m pip install -e ".[test]"

python scripts/fetch_data.py       # 下载 CIFAR-100 到 data/cifar100/（data/ 不入库）
python -m pytest                   # 34 个用例，CPU 上约 20 秒
bash scripts/run_local_fl.sh       # SuperLink + 2 个 SuperNode + FedAsync 20 步
```

`run_local_fl.sh` 的常用覆盖项：`FL_NUM_CLIENTS`、`FL_NUM_STEPS`、`FL_INIT_WEIGHTS`（预训练 `.npz`）。
更多超参见 `pyproject.toml` 的 `[tool.flwr.app.config]`，可用 `flwr run -c key=value` 或 `FL_*` 环境变量覆盖。

默认装的是 CPU 版 torch。要用 NVIDIA GPU，装完依赖后按 [pytorch.org](https://pytorch.org/get-started/locally/) 的指引重装 CUDA 版 torch 即可，代码会自动启用 AMP / cudnn.benchmark。

可选：

```bash
python scripts/pretrain_model.py --epochs 20            # 生成 artifacts/pretrained_cifar100.npz
FL_INIT_WEIGHTS=artifacts/pretrained_cifar100.npz bash scripts/run_local_fl.sh
python scripts/make_demo_page.py                         # 生成 artifacts/demo.html 可视化预测
```

## 快速开始（合约侧）

```bash
cd src/eth
npm ci                      # 按 package-lock 精确安装
npx hardhat test            # 23 个用例
```

部署到本地链（需要 Docker）：

```bash
bash scripts/chain/start_chain.sh                               # Anvil，127.0.0.1:8545，chainId 31337，状态持久化
cd src/eth && L1_CHALLENGE_PERIOD=60 npx hardhat run scripts/deploy.js --network localhost
bash scripts/storage/storage.sh start                           # 内容寻址存储，127.0.0.1:9000
```

详见 `scripts/chain/README.md` 与 `scripts/storage/README.md`。

## 当前状态

- Python 侧端到端可跑：数据分片、ResNet 训练、FedAsync 聚合、周期评估、最终权重落盘。
- `L1FL` 的乐观落账生命周期（`registerParticipant` / `commitRound` / `challenge` / `resolveChallenge` / `finalizeRound` / `withdraw`）已实现并有测试；`payReward` 为占位。
- `L2FL` 的 `applyToJoin` / `uploadParameters` / `getByParamId` 已实现；`distributeParameters` / `analyzeAndAggregate` / `commitToL1` 为 `revert NotImplemented()` 占位。
- Python 与合约之间尚未接线（服务端只把权重写到本地 `.npz`）。

各子目录的 `CLAUDE.md` 记录了更细的约定与设计意图。
