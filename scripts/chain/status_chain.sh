#!/usr/bin/env bash
# 查看本地链状态：容器运行情况、RPC 链 ID、最新区块高度、数据卷与状态文件。

set -eu

NAME="${CHAIN_NAME:-fl-chain}"
VOLUME="${CHAIN_VOLUME:-fl-chain-data}"
PORT="${CHAIN_PORT:-8545}"

if ! docker container inspect "$NAME" >/dev/null 2>&1; then
  echo "容器 ${NAME} 不存在（尚未启动或已被删除）"
  exit 0
fi

echo "==> 容器"
docker ps -a --filter "name=^/${NAME}$" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo "==> RPC (127.0.0.1:${PORT})"
CHAIN_ID="$(curl -sf -X POST -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' \
  "http://127.0.0.1:${PORT}" 2>/dev/null || echo unreachable)"
BLOCK="$(curl -sf -X POST -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  "http://127.0.0.1:${PORT}" 2>/dev/null || echo unreachable)"
echo "链 ID: ${CHAIN_ID}"
echo "最新区块: ${BLOCK}"

echo "==> 数据卷与状态文件"
docker volume inspect "$VOLUME" --format '卷名: {{.Name}}  挂载点: {{.Mountpoint}}'
if [ "$(docker inspect -f '{{.State.Running}}' "$NAME")" = "true" ]; then
  docker exec "$NAME" ls -la /data
else
  echo "容器未运行，跳过状态文件列表"
fi
