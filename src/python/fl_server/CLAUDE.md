# fl_server

Flower 服务端，独立包，位于 `src/python/fl_server`，结构与客户端镜像（`config.py`/`server.py`/`__main__.py`）。

## 职责

- 用 `fl_client.model.CIFAR100Model` 与 `fl_client.parameters.get_parameters` 生成初始权重；粗类数共享 `COARSE_CLASSES`，不重复定义。
- 用 Flower `FedAvg` 聚合客户端更新，accuracy/loss 按样本数加权平均。

## 安全

- TLS 仅用于生产：`FL_CA_CERT`、`FL_SERVER_CERT`、`FL_SERVER_KEY` 三者齐全才启用，本地调试留空即关闭。
- 客户端当前未出示自身凭据，因此服务端 TLS 尚非完整 mTLS 往返。
- 禁止禁用证书校验或将凭据写入源码。
