# 本地存储小平台（内容寻址，sha256）

用于本地调试模拟的极简对象存储：上传任意文件，得到 sha256 作为 id，凭 id 取回。
单进程、零依赖（Python 标准库）、不需要 Docker、不组分布式，数据落盘在仓库
`data/storage/`（已被 .gitignore 忽略）。对应链上 `metadataUri` 所指的链下存储角色。

## 启动

```text
bash scripts/storage/storage.sh start      # 启动，监听 127.0.0.1:9000
bash scripts/storage/storage.sh status     # 查看状态 / 已存文件数
bash scripts/storage/storage.sh logs       # 跟踪日志（Ctrl-C 退出）
bash scripts/storage/storage.sh stop       # 停止（数据保留）
bash scripts/storage/storage.sh restart    # 重启
```

覆盖项：`STORAGE_PORT`（默认 9000）、`STORAGE_DIR`（默认 `data/storage`）、`STORAGE_HOST`。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/files` | 上传原始字节，返回 `{"id": sha256, "size": n, "url": "/files/<id>"}` |
| GET | `/files` | 列出全部已存 id |
| GET | `/files/<id>` | 取回文件（`application/octet-stream`），不存在返回 404 |
| GET | `/health` | 健康检查 |

## 示例

```text
# 上传（内容寻址：相同内容返回相同 id，自动去重）
curl -X POST --data-binary @artifacts/global_parameters.npz http://127.0.0.1:9000/files

# 取回
curl -o out.npz http://127.0.0.1:9000/files/<64位hex>

# 列表
curl http://127.0.0.1:9000/files
```

## 数据

- 目录：`data/storage/`；每个文件以 sha256 命名。
- 清空：`rm -rf data/storage`（数据不可恢复，慎用）。

## 对接链上 metadataUri

本机调试时 `metadataUri` 可直接填 `http://127.0.0.1:9000/files/<id>`。
