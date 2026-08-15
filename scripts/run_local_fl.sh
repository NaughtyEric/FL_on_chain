#!/usr/bin/env bash
# One-shot local async FedAsync debug run on the modern SuperLink topology.
#
# Topology (all on 127.0.0.1):
#   flower-superlink          the link (Control :9093 / Fleet :9092 / AppIo :9091)
#   N x flower-supernode      one per data partition (unique ClientAppIo ports)
#   flwr run . --stream       builds the FAB and runs the ServerApp (FedAsync)
#
# Overrides (env vars):
#   FL_NUM_CLIENTS   number of supernodes / data partitions (default 2)
#   FL_NUM_STEPS     async global updates to run (default 20)
#   FL_DATA_DIR      HuggingFace CIFAR-100 arrow directory (default data/cifar100)
#   FL_INIT_WEIGHTS  pre-trained .npz to seed the global model (default none; see scripts/pretrain_model.py)
#   FL_LEARNING_RATE client SGD learning rate (default 0.1; matches pretrain_model.py)
#   FL_WEIGHT_DECAY  client SGD weight decay (default 5e-4; matches pretrain_model.py)
#   FL_MOMENTUM      client SGD momentum (default 0.9; matches pretrain_model.py)
#   FLWR_HOME        Flower home (default $PWD/.flwr)
#   PYTHON           python interpreter (default .venv/Scripts/python)

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-.venv/Scripts/python}"
NUM_CLIENTS="${FL_NUM_CLIENTS:-2}"
NUM_STEPS="${FL_NUM_STEPS:-20}"
DATA_DIR="${FL_DATA_DIR:-data/cifar100}"
INIT_WEIGHTS="${FL_INIT_WEIGHTS:-}"
FLWR_HOME="${FLWR_HOME:-$REPO_ROOT/.flwr}"

export FLWR_HOME FL_DATA_DIR FL_INIT_WEIGHTS="$INIT_WEIGHTS"
# superlink/supernode spawn `flower-superexec` by bare name; keep venv Scripts on PATH.
export PATH="$REPO_ROOT/.venv/Scripts:$PATH"

SUPERLINK_PORT=9093
FLEET_PORT=9092
APPIO_PORT=9091
NODE_BASE_PORT=9104

if ! command -v flower-superlink >/dev/null 2>&1; then
  echo "flower-superlink not found on PATH (is .venv/Scripts on PATH?)" >&2
  exit 1
fi
mkdir -p "$FLWR_HOME"

echo "==> Starting SuperLink (control :${SUPERLINK_PORT} fleet :${FLEET_PORT} appio :${APPIO_PORT})"
flower-superlink --insecure --disable-runtime-dependency-installation \
  --control-api-address "127.0.0.1:${SUPERLINK_PORT}" \
  --fleet-api-address "127.0.0.1:${FLEET_PORT}" \
  --serverappio-api-address "127.0.0.1:${APPIO_PORT}" \
  --log-file "$FLWR_HOME/superlink.log" &
SUPERLINK_PID=$!

SUPERNODE_PIDS=()
trap 'kill "$SUPERLINK_PID" 2>/dev/null || true; for p in "${SUPERNODE_PIDS[@]}"; do kill "$p" 2>/dev/null || true; done' EXIT

echo "==> Waiting for SuperLink Control API on :${SUPERLINK_PORT}..."
"$PYTHON" - "$SUPERLINK_PORT" <<'EOF'
import socket
import sys
import time

port = int(sys.argv[1])
deadline = time.monotonic() + 30
while time.monotonic() < deadline:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            sys.exit(0)
    except OSError:
        time.sleep(1)
sys.exit(1)
EOF
if [ $? -ne 0 ]; then
  echo "SuperLink did not come up within 30s; tail $FLWR_HOME/superlink.log" >&2
  exit 1
fi

# Point `flwr run` at our user-managed SuperLink (the default `:local:` spins up a
# simulation SuperLink with no Fleet API, so real SuperNodes could not attach).
cat > "$FLWR_HOME/config.toml" <<EOF
[superlink]
default = "local"

[superlink.local]
address = "127.0.0.1:${SUPERLINK_PORT}"
insecure = true
EOF

# One SuperNode per partition; each needs a unique --clientappio-api-address.
for ((i = 0; i < NUM_CLIENTS; i++)); do
  port=$((NODE_BASE_PORT + i))
  echo "==> Starting SuperNode ${i}/${NUM_CLIENTS} (partition ${i}/${NUM_CLIENTS}, appio :${port})"
  flower-supernode --superlink "127.0.0.1:${FLEET_PORT}" --insecure \
    --clientappio-api-address "127.0.0.1:${port}" \
    --node-config "partition-id=${i} num-partitions=${NUM_CLIENTS}" &
  SUPERNODE_PIDS+=("$!")
done

echo "==> Running ServerApp (num_steps=${NUM_STEPS})"
flwr run . --stream -c "num_steps=${NUM_STEPS}"
RUN_RC=$?

echo "==> Done (flwr run exited ${RUN_RC}); shutting down topology"
exit "$RUN_RC"
