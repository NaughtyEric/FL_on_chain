#!/usr/bin/env bash
# 把链状态快照复制到仓库 .chain-backups/（不干扰运行中的链）。
# 恢复方法见 scripts/chain/README.md。

set -eu

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NAME="${CHAIN_NAME:-fl-chain}"
BACKUP_DIR="${CHAIN_BACKUP_DIR:-$REPO_ROOT/.chain-backups}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
docker cp "$NAME:/data/anvil-state.json" "$BACKUP_DIR/anvil-state-${STAMP}.json"

echo "快照已保存：$BACKUP_DIR/anvil-state-${STAMP}.json"
echo "恢复：docker cp $BACKUP_DIR/anvil-state-${STAMP}.json ${NAME}:/data/anvil-state.json && bash scripts/chain/restart_chain.sh"
