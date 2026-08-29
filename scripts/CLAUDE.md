# scripts

本地单机调试：SuperLink + N 个 SuperNode + `flwr run`（异步 FedAsync）。

```text
bash scripts/run_local_fl.sh                              # 2 节点 / 20 步
FL_NUM_CLIENTS=3 FL_NUM_STEPS=30 bash scripts/run_local_fl.sh
bash scripts/chain/start_chain.sh|stop_chain.sh|status_chain.sh   # 本地链：Docker+Anvil，状态持久化到卷（详见 chain/README.md）
bash scripts/storage/storage.sh start|status              # 内容寻址存储：sha256，127.0.0.1:9000（详见 storage/README.md）
cd src/eth && npx hardhat run scripts/deploy.js --network localhost   # 部署合约到本地链
```

- 节点按 `--node-config "partition-id=i num-partitions=N"` 确定性切分 CIFAR-100；
  数据集为 HF arrow 格式，已在 `data/cifar100/`，无需下载。
- 可选预训练起步：`scripts/pretrain_model.py` 生成 `.npz`，`FL_INIT_WEIGHTS=<path>` 传给 run_local_fl.sh。
- 产物与日志在 `FLWR_HOME`（默认 `.flwr/`）；脚本退出时 trap 自动清理 superlink/supernode。
