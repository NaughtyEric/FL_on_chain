#!/usr/bin/env bash
# 启动本地开发链（Docker + Foundry Anvil），状态持久化到 Docker 卷，随时可重启恢复。
#
# 设计要点：
#   - 链状态保存在 Docker 命名卷 ${CHAIN_VOLUME:-fl-chain-data} 的 /data/anvil-state.json；
#     Anvil 启动时自动加载该文件，运行中定期写盘，停止时写回 => 重启/断电后状态不丢。
#   - 容器 --restart unless-stopped：Docker 守护进程/机器重启后自动拉起。
#   - 链 ID 31337、RPC 127.0.0.1:8545，与 src/eth/hardhat.config.js 的 localhost 网络一致，
#     后续 Hardhat 部署命令无需改动。
#   - 账号由固定助记词派生（默认 Anvil 内置 mnemonic），重启后地址/私钥不变。
#
# 覆盖项（环境变量）：
#   CHAIN_IMAGE      镜像（默认 ghcr.io/foundry-rs/foundry:stable）
#   CHAIN_NAME       容器名（默认 fl-chain）
#   CHAIN_VOLUME     数据卷名（默认 fl-chain-data）
#   CHAIN_PORT       宿主机 RPC 端口（默认 8545，仅绑定 127.0.0.1）
#   CHAIN_MNEMONIC   助记词（默认 Anvil 内置 "test ... junk"，可覆盖）
#   CHAIN_BLOCK_TIME 出块间隔秒数（默认即时出块；设如 3 则每 3 秒一个块）

set -eu

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

IMAGE="${CHAIN_IMAGE:-ghcr.io/foundry-rs/foundry:stable}"
NAME="${CHAIN_NAME:-fl-chain}"
VOLUME="${CHAIN_VOLUME:-fl-chain-data}"
PORT="${CHAIN_PORT:-8545}"
MNEMONIC="${CHAIN_MNEMONIC:-}"
BLOCK_TIME="${CHAIN_BLOCK_TIME:-}"

STATE_FILE="/data/anvil-state.json"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker 不可用：请先安装并启动 Docker Desktop" >&2
  exit 1
fi

echo "==> 检查镜像 ${IMAGE}"
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "    镜像不存在，拉取中（首次需要网络）..."
  docker pull "$IMAGE"
fi

echo "==> 检查数据卷 ${VOLUME}"
if ! docker volume inspect "$VOLUME" >/dev/null 2>&1; then
  docker volume create "$VOLUME"
fi

# 镜像默认 entrypoint 是 /bin/sh -c，直接传多个参数会被当成位置参数丢弃，
# 因此用 --entrypoint anvil 显式指定二进制，flags 原样传入。
ANVIL_ARGS=(--host 0.0.0.0 --port 8545 --chain-id 31337 --state "$STATE_FILE")
if [ -n "$MNEMONIC" ]; then
  ANVIL_ARGS+=(--mnemonic "$MNEMONIC")
fi
if [ -n "$BLOCK_TIME" ]; then
  ANVIL_ARGS+=(--block-time "$BLOCK_TIME")
fi

if docker container inspect "$NAME" >/dev/null 2>&1; then
  case "$(docker inspect -f '{{.State.Status}}' "$NAME")" in
    running)
      echo "==> 容器 ${NAME} 已在运行，无需重复启动"
      ;;
    *)
      echo "==> 容器 ${NAME} 存在但未运行，直接拉起（状态自动从卷恢复）"
      docker start "$NAME"
      ;;
  esac
else
  echo "==> 创建并启动容器 ${NAME}（链 ID 31337，RPC 127.0.0.1:${PORT}）"
  docker run -d \
    --name "$NAME" \
    --restart unless-stopped \
    --entrypoint anvil \
    -v "$VOLUME":/data \
    -p "127.0.0.1:${PORT}:8545" \
    "$IMAGE" "${ANVIL_ARGS[@]}"
fi

# 等待 RPC 就绪并校验链 ID
echo "==> 等待 RPC 就绪 ..."
RESP=""
for _ in $(seq 1 30); do
  if RESP="$(curl -sf -X POST -H 'Content-Type: application/json' \
      --data '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' \
      "http://127.0.0.1:${PORT}" 2>/dev/null)"; then
    break
  fi
  sleep 1
done
if [ -z "$RESP" ]; then
  echo "RPC 30 秒内未就绪，请查看日志: docker logs ${NAME}" >&2
  exit 1
fi

EXPECTED_HEX="$(printf '0x%x' 31337)"
if ! printf '%s' "$RESP" | grep -q "\"$EXPECTED_HEX\""; then
  echo "警告：RPC 已就绪但链 ID 非 ${EXPECTED_HEX}，返回：${RESP}" >&2
fi

echo "==> 完成：链 ${NAME} 运行中（RPC 127.0.0.1:${PORT}，状态卷 ${VOLUME}）"
echo "    部署合约：cd src/eth && npx hardhat run scripts/deploy.js --network localhost"
