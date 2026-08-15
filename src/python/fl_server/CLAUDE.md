# fl_server

Flower 服务端（异步 FedAsync，SuperLink ServerApp），独立包，位于 `src/python/fl_server`。

## 职责

- `fedasync.py`：纯 FedAsync 数学（Xie et al. 2019，不依赖 Flower，可单独单测）+ 运行配置 `AsyncConfig`。
  - `x_{t+1} = (1-α_t)·x_t + α_t·x_u`，`α_t = α·h(s,τ)`；staleness 函数 linear/poly/exp，可选 bound。
- `serverapp.py`：`ServerApp` + `@app.main()` 的异步训练循环（Grid push/pull + TTL 驱逐）：
  - 维护 `in_flight` 消息表，空闲节点并发派发 TRAIN（≤ `max_concurrency`）；
  - 收到回复时 `staleness = global_step - dispatch_step`（≥0），按 `α_t = α·h(s)` 吸收更新；
  - 每 `evaluate_every` 步做分布式评估，最终准确率写入 `context.state.config_records["fedasync.final_accuracy"]`；
  - 训练结束时把最终全局参数 dump 到 `output_path`（默认 `artifacts/global_parameters.npz`，已 gitignore，可用 `FL_OUTPUT_PATH` 覆盖），供离线推理。
- 初始权重与 accuracy/loss 样本数加权聚合复用 `fl_client.model.CIFAR100ResNet`/`COARSE_CLASSES`。
- 初始全局模型可用预训练 `.npz` 种子：`AsyncConfig.init_weights`（`FL_INIT_WEIGHTS` / run config `init_weights`），
  checkpoint 由 `scripts/pretrain_model.py` 生成；路径缺失或形状不符会回退到随机初始化。

## 运行

本地拓扑（SuperLink + N 个 SuperNode）由 `scripts/run_local_fl.sh` 一键拉起：

```text
bash scripts/run_local_fl.sh
FL_NUM_CLIENTS=3 FL_NUM_STEPS=30 bash scripts/run_local_fl.sh
```

超参数来自 `pyproject.toml` 的 `[tool.flwr.app.config]`，可用 `flwr run -c key=value` 覆盖，
或 `FL_*` 环境变量（见 `AsyncConfig.from_env`）。
