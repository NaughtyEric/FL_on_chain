#!/usr/bin/env bash
# 停止本地链。Anvil 关停前会把最新状态写回数据卷，下次 start_chain.sh 可完整恢复。

set -eu

NAME="${CHAIN_NAME:-fl-chain}"

if docker container inspect "$NAME" >/dev/null 2>&1; then
  docker stop "$NAME"
  echo "已停止 ${NAME}；状态已写回数据卷，随时可用 scripts/chain/start_chain.sh 恢复"
else
  echo "容器 ${NAME} 不存在，无需停止"
fi
