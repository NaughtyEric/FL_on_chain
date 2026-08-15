# fl_client

Flower 客户端，独立包，位于 `src/python/fl_client`。

## 职责

- 用 PyTorch 在本地训练 CIFAR-100，粗粒度（superclass）标签直接取数据的 `coarse_label` 特征（20 类）。
- 模型为 32×32 适配的残差网络 `CIFAR100ResNet`（`model.py`，3 个残差 stage），默认 20 类输出；服务端可用预训练 `.npz` 当初始权重（`FL_INIT_WEIGHTS`，见 `scripts/pretrain_model.py`）。
- 数据集为 HuggingFace arrow 格式，位于 `data/cifar100/`，由 `dataset.py` 的 `load_cifar100`/`CIFAR100CoarseDataset` 加载（`coarse_label` 是权威标签，因 fine 标签非连续分组，不能用 `fine // 5`）。
- `clientapp.py` 的 `ClientApp(client_fn=...)` 由 SuperNode 按消息调用：
  - 从 `context.node_config` 读 `partition-id`/`num-partitions`（SuperNode `--node-config` 设置）确定分片；
  - 数据集按 `data_dir` 模块级缓存，避免每个消息重复加载 arrow 文件；
  - 返回 `FlowerClient(config, dataset).to_client()`。
- 区块链集成尚未实现。

## 启动

由 `flower-supernode` 加载（见 `scripts/run_local_fl.sh`），不单独用 `python -m` 启动。
配置见 `config.py`（`ClientConfig.from_env`/`validate`），可用 `FL_*` 环境变量覆盖。

## 设备

- `device="auto"`（默认）经 `select_device` 解析：有 CUDA 用 GPU，否则回退 CPU（Apple 上优先 MPS）。
- 客户端与 `scripts/pretrain_model.py`、`scripts/predict_samples.py` 都走这条路径；可用 `FL_DEVICE=cpu|cuda` 强制指定。
- 注意：当前 venv 是 CPU 版 torch（`2.13.0+cpu`），`torch.cuda.is_available()` 为 False，`auto` 实际落在 CPU；要真正用 GPU 需安装 CUDA 版 torch。

## 安全

- 本地调试 `--insecure`；生产需 SuperLink/SuperNode 的 TLS，禁止禁用证书校验或将凭据写入源码。
- 不支持 NPU；任何客户端回退实现不得宣称支持。
