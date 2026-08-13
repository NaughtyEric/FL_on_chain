# scripts

本地单机调试（Windows Git Bash）：一个 server + 多个 client。

```text
bash scripts/run_local_fl.sh                     # server + 2 clients, 1 round, TLS off
FL_NUM_CLIENTS=3 FL_NUM_ROUNDS=2 bash scripts/run_local_fl.sh
```

- 客户端按 `--partition-id`/`--num-partitions` 确定性地切分 CIFAR-100。
- 首次运行下载 CIFAR-100（约 180MB）到 `data/`。
- 全部环境变量覆盖项见脚本头部注释。
