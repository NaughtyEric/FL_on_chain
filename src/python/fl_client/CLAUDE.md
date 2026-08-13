# fl_client

Flower 客户端，独立包，位于 `src/python/fl_client`。

## 职责

- 用 PyTorch/torchvision 在本地训练 CIFAR-100，默认映射到 20 个粗粒度（superclass）标签。
- 通过 Flower 回调与服务器交互；区块链集成尚未实现。

## 启动

```text
python -m fl_client --server-address HOST:PORT --client-id CLIENT_ID --data-dir data --partition-id 0 --num-partitions N [--download]
```

仅当存在兼容的 Flower 服务器与数据集时启动。`--partition-id`/`--num-partitions` 决定 CIFAR-100 分片，各进程训练不重叠的切片。参数与 `FL_*` 环境变量见 `config.py`（`ClientConfig.from_env`/`validate`）。

## 安全

- 生产环境 TLS：`FL_CA_CERT`、`FL_CLIENT_CERT`、`FL_CLIENT_KEY` 三者同时配置并校验后才接入 TLS/mTLS。
- 禁止禁用证书校验或将凭据写入源码。
- 不支持 NPU；任何客户端回退实现不得宣称支持。
