#!/usr/bin/env bash
# 跟踪本地链日志（Ctrl-C 退出）。可传尾部行数，如：bash scripts/chain/logs_chain.sh 50

set -eu

NAME="${CHAIN_NAME:-fl-chain}"
LINES="${1:-100}"

docker logs -f --tail "$LINES" "$NAME"
