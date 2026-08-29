# fl_client

Flower 客户端，独立包 `src/python/fl_client`，由 `flower-supernode` 加载（见 `scripts/run_local_fl.sh`），不单独 `python -m` 启动。

- CIFAR-100 粗粒度 20 类：权威标签是数据集的 `coarse_label` 特征（fine 标签非连续分组，**不能用 `fine // 5`**）。数据为 HF arrow 格式，位于 `data/cifar100/`，由 `dataset.py` 加载。
- 模型 `CIFAR100ResNet`（32×32 适配，3 残差 stage）。训练配方与 `scripts/pretrain_model.py` 一致：SGD lr=0.1、momentum=0.9、weight_decay=5e-4；每步全局梯度 L2 范数裁剪，默认 `max_grad_norm=5.0`（0 关闭），AMP 下先 `scaler.unscale_` 再裁剪。
- 配置全部走 `ClientConfig.from_env`（`FL_*` 环境变量覆盖）；分片由 SuperNode `--node-config "partition-id=i num-partitions=N"` 决定；数据集按 data_dir 模块级缓存，避免重复加载。
- 设备 `auto`：CUDA > MPS（Apple）> CPU（`select_device`）。CUDA 下自动开 cudnn.benchmark、TF32 matmul、pin_memory 与 AMP(fp16)；CPU 路径均为 no-op。当前 venv 是 CPU 版 torch，要用 GPU 需另装 CUDA 版。
- 安全：本地调试 `--insecure`；生产必须 TLS，禁止禁用证书校验或将凭据写入源码。不支持 NPU，回退实现不得宣称支持。
