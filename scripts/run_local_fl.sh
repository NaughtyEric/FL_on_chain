#!/usr/bin/env bash
# One-shot local federated debug run: a single server plus N clients on 127.0.0.1.
#
# Simulates multi-client interaction on one machine so the server and clients
# can be exercised end-to-end without a distributed setup. TLS is intentionally
# OFF here: only the production server enables it via FL_CA_CERT / FL_SERVER_CERT
# / FL_SERVER_KEY.
#
# Overrides (env vars):
#   FL_SERVER_ADDRESS  host:port the server listens on (default 127.0.0.1:8080)
#   FL_NUM_CLIENTS     number of clients to spawn (default 2)
#   FL_NUM_ROUNDS      federation rounds (default 1)
#   FL_DATA_DIR        CIFAR-100 cache directory (default data)
#   PYTHON             python interpreter (default .venv/Scripts/python)

set -u

PYTHON="${PYTHON:-.venv/Scripts/python}"
SERVER_ADDRESS="${FL_SERVER_ADDRESS:-127.0.0.1:8080}"
NUM_CLIENTS="${FL_NUM_CLIENTS:-2}"
NUM_ROUNDS="${FL_NUM_ROUNDS:-1}"
DATA_DIR="${FL_DATA_DIR:-data}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "python interpreter not found: $PYTHON (set PYTHON to override)" >&2
  exit 1
fi

echo "==> Starting server on ${SERVER_ADDRESS} (rounds=${NUM_ROUNDS}, clients=${NUM_CLIENTS})"
"$PYTHON" -m fl_server \
  --server-address "$SERVER_ADDRESS" \
  --num-rounds "$NUM_ROUNDS" \
  --min-available-clients "$NUM_CLIENTS" \
  --min-fit-clients "$NUM_CLIENTS" \
  --min-evaluate-clients "$NUM_CLIENTS" &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

# Give the gRPC server a moment to bind before clients connect.
sleep 3

for ((i = 0; i < NUM_CLIENTS; i++)); do
  echo "==> Starting client ${i}/${NUM_CLIENTS} (partition ${i} of ${NUM_CLIENTS})"
  "$PYTHON" -m fl_client \
    --server-address "$SERVER_ADDRESS" \
    --client-id "client-$i" \
    --data-dir "$DATA_DIR" \
    --partition-id "$i" \
    --num-partitions "$NUM_CLIENTS" \
    --download &
done

# The server exits after FL_NUM_ROUNDS; clients exit when the server stops.
wait
