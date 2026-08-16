#!/usr/bin/env bash
# 本地最小存储服务（内容寻址，sha256）：单进程、零依赖（Python 标准库），用于本地调试模拟。
#
# 用法：bash scripts/storage/storage.sh <start|stop|restart|status|logs>
#
# 覆盖项（环境变量）：
#   STORAGE_PORT  监听端口（默认 9000）
#   STORAGE_DIR   数据目录（默认 <repo>/data/storage，已被 .gitignore 忽略）
#   STORAGE_HOST  绑定地址（默认 127.0.0.1）

set -eu

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVER="$REPO_ROOT/scripts/storage/storage_server.py"
PORT="${STORAGE_PORT:-9000}"
DATA_DIR="${STORAGE_DIR:-$REPO_ROOT/data/storage}"
PID_FILE="$DATA_DIR/server.pid"
LOG_FILE="$DATA_DIR/server.log"

case "${1:-}" in
  start)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "已在运行 (pid $(cat "$PID_FILE"))，端口 ${PORT}"
      exit 0
    fi
    mkdir -p "$DATA_DIR"
    # 服务自身 daemonize（setsid + 双 fork），脱离启动它的 shell 会话；
    # 不依赖 nohup/后台 &，进程在终端关闭后依然存活。
    STORAGE_PORT="$PORT" STORAGE_DIR="$DATA_DIR" STORAGE_PID_FILE="$PID_FILE" \
      python3 "$SERVER" >> "$LOG_FILE" 2>&1 || {
        echo "启动失败，请查看日志: ${LOG_FILE}" >&2
        exit 1
      }
    for _ in $(seq 1 20); do
      if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
        echo "已启动 (pid $(cat "$PID_FILE"))：http://127.0.0.1:${PORT}，数据目录 ${DATA_DIR}"
        echo "  上传: curl -X POST --data-binary @<文件> http://127.0.0.1:${PORT}/files"
        exit 0
      fi
      sleep 0.5
    done
    echo "启动失败，请查看日志: ${LOG_FILE}" >&2
    exit 1
    ;;
  stop)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      kill "$(cat "$PID_FILE")"
      rm -f "$PID_FILE"
      echo "已停止；数据保留在 ${DATA_DIR}"
    else
      echo "未在运行"
    fi
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "运行中 (pid $(cat "$PID_FILE"))，端口 ${PORT}"
      curl -sf "http://127.0.0.1:${PORT}/health" || echo "(health 检查失败)"
      COUNT="$(curl -sf "http://127.0.0.1:${PORT}/files" 2>/dev/null \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["count"])' 2>/dev/null || echo "?")"
      echo "已存文件数: ${COUNT}"
    else
      echo "未在运行（端口 ${PORT}，数据目录 ${DATA_DIR}）"
    fi
    ;;
  logs)
    tail -f "$LOG_FILE"
    ;;
  *)
    echo "用法: $0 {start|stop|restart|status|logs}" >&2
    exit 1
    ;;
esac
