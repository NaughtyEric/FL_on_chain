#!/usr/bin/env bash
# 重启本地链：先优雅停止（状态落盘），再拉起（从卷恢复）。

set -eu

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

"$REPO_ROOT/scripts/chain/stop_chain.sh"
"$REPO_ROOT/scripts/chain/start_chain.sh"
