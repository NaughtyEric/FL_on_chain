# 本地链（Docker + Anvil）

用 Docker 启动一条**可持久化、随时可恢复**的本地 EVM 链，供合约部署/测试与后续链上联邦学习流程使用。

## 为什么用 Anvil

- `--state` 原生支持状态落盘/加载：启动时自动从文件恢复，运行中定期写盘，停止时写回，重启不丢状态。
- 默认链 ID 31337、RPC `127.0.0.1:8545`，与 `src/eth/hardhat.config.js` 的 localhost 网络一致，Hardhat 部署零改动。
- 账号由固定助记词派生（Anvil 默认 `test test ... junk`），重启后地址/私钥不变。
- 容器 `--restart unless-stopped`：Docker 守护进程/机器重启后自动拉起。

## 常用命令

| 命令 | 作用 |
| --- | --- |
| `bash scripts/chain/start_chain.sh` | 启动（幂等：已运行则跳过，已停止则拉起并恢复状态） |
| `bash scripts/chain/stop_chain.sh` | 优雅停止（状态自动写回卷） |
| `bash scripts/chain/restart_chain.sh` | 重启（先落盘再恢复） |
| `bash scripts/chain/status_chain.sh` | 查看容器 / RPC / 区块高度 / 状态文件 |
| `bash scripts/chain/logs_chain.sh` | 跟踪日志（Ctrl-C 退出） |
| `bash scripts/chain/snapshot_chain.sh` | 把状态快照复制到 `.chain-backups/` |

环境变量覆盖：`CHAIN_IMAGE`、`CHAIN_NAME`、`CHAIN_VOLUME`、`CHAIN_PORT`、`CHAIN_MNEMONIC`、`CHAIN_BLOCK_TIME`（见 [start_chain.sh](start_chain.sh) 头部注释）。

## 状态与恢复

- 状态保存在 Docker 命名卷 `fl-chain-data` 的 `/data/anvil-state.json`。
- 正常恢复：`stop_chain.sh` 之后、或机器重启之后，直接 `start_chain.sh` 即可，无需手工操作。
- 快照 / 回滚：

  ```text
  # 备份
  bash scripts/chain/snapshot_chain.sh

  # 恢复指定快照
  docker cp .chain-backups/anvil-state-<时间戳>.json fl-chain:/data/anvil-state.json
  bash scripts/chain/restart_chain.sh
  ```

- 彻底删除链（状态不可恢复，慎用）：`docker rm -f fl-chain && docker volume rm fl-chain-data`

## 部署合约

```text
cd src/eth
npm install    # 首次
npx hardhat run scripts/deploy.js --network localhost
```

## 账号

使用 Anvil 默认助记词（`test test test test test test test test test test test junk`），
`account[0]` 固定为 `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`，所有账号初始持有大量 ETH。

## 常见问题

- **端口占用**：`CHAIN_PORT=8546 bash scripts/chain/start_chain.sh`，并同步修改 `src/eth/hardhat.config.js` 的 localhost URL。
- **首次拉镜像需要网络**：`docker pull ghcr.io/foundry-rs/foundry:stable`。
- **机器重启后自动恢复**：依赖 Docker Desktop 开机自启（在 Docker Desktop 设置中开启）。
