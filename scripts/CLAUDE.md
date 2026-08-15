# scripts

本地单机调试（Windows Git Bash）：SuperLink + N 个 SuperNode + `flwr run`（异步 FedAsync）。

```text
bash scripts/run_local_fl.sh                          # 2 个节点 / 20 步
FL_NUM_CLIENTS=3 FL_NUM_STEPS=30 bash scripts/run_local_fl.sh
```

- 拓扑：`flower-superlink`（Control :9093 / Fleet :9092 / AppIo :9091）+ 每分区一个
  `flower-supernode`（ClientAppIo :9104+i），`flwr run . --stream` 前台跑 ServerApp。
- 节点按 `--node-config "partition-id=i num-partitions=N"` 确定性地切分 CIFAR-100。
- CIFAR-100 以 HuggingFace arrow 格式放在 `data/cifar100/`（train/test `.arrow` + `dataset_info.json`），无需下载。
- 可选：先用 `scripts/pretrain_model.py` 预训练 `CIFAR100ResNet` 存成 `.npz`，再 `FL_INIT_WEIGHTS=<path> bash scripts/run_local_fl.sh` 让服务端从该 checkpoint 起步。
- 产物与日志在 `FLWR_HOME`（默认 `.flwr/`）；全部环境变量覆盖项见脚本头部注释。
- 结束时 `trap` 自动清理 superlink/supernode。
