# fl_server

Flower 服务端（异步 FedAsync，Xie et al. 2019），独立包 `src/python/fl_server`。

- `fedasync.py`：纯 FedAsync 数学 + `AsyncConfig`，不依赖 Flower，可单独单测。
  `x_{t+1} = (1-α_t)·x_t + α_t·x_u`，`α_t = α·h(s,τ)`，staleness 函数 linear/poly/exp，可选 bound。
- `serverapp.py`：异步训练循环（Grid push/pull + TTL 驱逐）。in_flight 表并发派发 TRAIN（≤ `max_concurrency`），`staleness = global_step - dispatch_step`；每 `evaluate_every` 步分布式评估，最终精度写 `context.state.config_records["fedasync.final_accuracy"]`，最终权重 dump 到 `FL_OUTPUT_PATH`（默认 `artifacts/global_parameters.npz`，已 gitignore）。
- 模型复用 `fl_client.model.CIFAR100ResNet`；初始权重可用预训练 `.npz`（`FL_INIT_WEIGHTS`），路径缺失或形状不符回退随机初始化。
- 超参在 `pyproject.toml` `[tool.flwr.app.config]`，可 `flwr run -c key=value` 或 `FL_*` 环境变量覆盖；本地一键拉起 `bash scripts/run_local_fl.sh`。
