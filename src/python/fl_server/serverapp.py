"""Async FedAsync (Xie et al. 2019) Flower ServerApp.

The modern ServerApp + Grid message loop replaces the legacy synchronous
``start_server``/``FedAvg`` round loop. FedAsync is inherently asynchronous, so
the whole training loop lives in ``main``: clients train concurrently on
possibly-stale global versions and the server absorbs each returned update with
``alpha_t = alpha * h(s, tau)`` (staleness-weighted learning rate).

Deployment: this ``app`` is loaded from the FAB by ``flower-superlink``; hyper-
parameters come from ``context.run_config`` (``[tool.flwr.app.config]``) with
``FL_*`` env fallback.
"""

from __future__ import annotations

import time
from logging import INFO, WARNING
from pathlib import Path
from typing import Optional

import numpy as np

from flwr.app import ConfigRecord, Context, Message, MessageType
from flwr.common import (
    EvaluateIns,
    FitIns,
    Parameters,
    ndarrays_to_parameters,
    parameters_to_ndarrays,
)
from flwr.common.logger import log
from flwr.compat.common.recorddict_compat import (
    evaluateins_to_recorddict,
    fitins_to_recorddict,
    recorddict_to_evaluateres,
    recorddict_to_fitres,
)
from flwr.serverapp import Grid, ServerApp

from fl_client.model import CIFAR100ResNet, COARSE_CLASSES
from fl_client.parameters import get_parameters, load_parameters, save_parameters, set_parameters

from .fedasync import AsyncConfig, async_update, make_staleness_fn


def initial_parameters(init_path: Optional[Path] = None) -> Parameters:
    """Seed the global model, preferring a pre-trained .npz checkpoint.

    If ``init_path`` points at an existing checkpoint (see
    ``scripts/pretrain_model.py``), its arrays are validated against a fresh
    ``CIFAR100ResNet`` and used verbatim; otherwise a randomly-initialized
    model is returned.
    """
    if init_path is not None and Path(init_path).is_file():
        arrays = load_parameters(init_path)
        set_parameters(CIFAR100ResNet(num_classes=COARSE_CLASSES), arrays)  # shape/layout check
        log(INFO, "seeding global model from %s", init_path)
        return ndarrays_to_parameters(arrays)
    if init_path is not None:
        log(WARNING, "init weights %s not found; falling back to random init", init_path)
    return ndarrays_to_parameters(get_parameters(CIFAR100ResNet(num_classes=COARSE_CLASSES)))


def weighted_average(metrics: list[tuple[int, dict]]) -> dict:
    """Aggregate per-client "accuracy" weighted by the number of examples."""
    total = sum(num_examples for num_examples, _ in metrics)
    if total == 0:
        return {"accuracy": 0.0}
    values = [num_examples * float(entry["accuracy"]) for num_examples, entry in metrics]
    return {"accuracy": sum(values) / total}


def weighted_loss(metrics: list[tuple[int, dict]]) -> dict:
    """Aggregate per-client "loss" weighted by the number of examples."""
    total = sum(num_examples for num_examples, _ in metrics)
    if total == 0:
        return {"loss": 0.0}
    values = [num_examples * float(entry["loss"]) for num_examples, entry in metrics]
    return {"loss": sum(values) / total}


def _evaluate(grid: Grid, node_ids: list[int], global_arrays: list[np.ndarray], cfg: AsyncConfig) -> float:
    """Ask every node to evaluate the current global model; return weighted accuracy."""
    messages = []
    for node in node_ids:
        content = evaluateins_to_recorddict(
            EvaluateIns(parameters=ndarrays_to_parameters(global_arrays), config={}),
            keep_input=False,
        )
        messages.append(
            Message(content, dst_node_id=node, message_type=MessageType.EVALUATE, group_id="eval", ttl=cfg.ttl)
        )
    pending = list(grid.push_messages(messages))
    deadline = time.monotonic() + cfg.ttl
    results: list[tuple[int, dict]] = []
    while pending and time.monotonic() < deadline:
        for reply in grid.pull_messages(pending):
            mid = reply.metadata.reply_to_message_id
            if mid not in pending:
                continue
            pending.remove(mid)
            if reply.has_error():
                continue
            eval_res = recorddict_to_evaluateres(reply.content)
            results.append((eval_res.num_examples, eval_res.metrics))
        time.sleep(0.5)
    if pending:
        log(WARNING, "evaluation timed out with %d unanswered node(s)", len(pending))
    return float(weighted_average(results)["accuracy"])


app = ServerApp()


@app.main()
def main(grid: Grid, context: Context) -> None:
    """FedAsync training loop (paper Algorithm 1, multi-worker variant)."""
    cfg = AsyncConfig.from_run_config(context.run_config)
    cfg.validate()
    log(INFO, "FedAsync config: steps=%d alpha=%.2f tau=%.2f staleness_fn=%s bound=%s "
              "concurrency=%d min_clients=%d ttl=%.0fs evaluate_every=%d",
        cfg.num_steps, cfg.alpha, cfg.tau, cfg.staleness_fn, cfg.staleness_bound,
        cfg.max_concurrency, cfg.min_clients, cfg.ttl, cfg.evaluate_every)

    # Wait until enough SuperNodes have registered before dispatching anything.
    node_ids: list[int] = []
    while len(node_ids) < cfg.min_clients:
        node_ids = list(grid.get_node_ids())
        log(INFO, "waiting for %d node(s) (have %d)", cfg.min_clients, len(node_ids))
        time.sleep(1.0)
    log(INFO, "starting FedAsync with nodes %s", node_ids)

    staleness_fn = make_staleness_fn(cfg.staleness_fn, cfg.tau)
    global_arrays = parameters_to_ndarrays(initial_parameters(cfg.init_weights))
    global_step = 0
    in_flight: dict[str, dict] = {}  # message_id -> {"node", "step", "sent"}

    while global_step < cfg.num_steps:
        now = time.monotonic()

        # 1) Drop messages whose TTL expired (unresponsive / too-slow clients).
        for mid in [mid for mid, info in in_flight.items() if now - info["sent"] > cfg.ttl]:
            log(WARNING, "dropping timed-out message %s from node %d", mid, in_flight[mid]["node"])
            del in_flight[mid]

        # 2) Dispatch TRAIN to idle nodes while concurrency slots remain.
        node_ids = list(grid.get_node_ids())
        busy = {info["node"] for info in in_flight.values()}
        for node in node_ids:
            if len(in_flight) >= cfg.max_concurrency:
                break
            if node in busy:
                continue
            content = fitins_to_recorddict(
                FitIns(parameters=ndarrays_to_parameters(global_arrays), config={}),
                keep_input=False,  # fresh Parameters object, safe to consume
            )
            msg = Message(
                content, dst_node_id=node, message_type=MessageType.TRAIN,
                group_id=str(global_step), ttl=cfg.ttl,
            )
            sent = list(grid.push_messages([msg]))
            if not sent:
                log(WARNING, "push_messages returned no id for node %d", node)
                continue
            in_flight[sent[0]] = {"node": node, "step": global_step, "sent": now}
            log(INFO, "dispatched train to node %d at step %d (in_flight=%d)",
                node, global_step, len(in_flight))

        if not in_flight:
            time.sleep(0.5)
            continue

        # 3) Absorb ready replies in FedAsync fashion.
        for reply in grid.pull_messages(list(in_flight.keys())):
            mid = reply.metadata.reply_to_message_id
            if mid not in in_flight:
                continue
            info = in_flight.pop(mid)
            if reply.has_error():
                log(WARNING, "train error from node %d, discarding update", info["node"])
                continue
            s = global_step - info["step"]
            if cfg.staleness_bound is not None:
                s = min(s, cfg.staleness_bound)
            alpha_t = cfg.alpha * staleness_fn(s)
            fit_res = recorddict_to_fitres(reply.content, keep_input=True)
            loss = float(fit_res.metrics.get("loss", float("nan")))
            global_arrays = async_update(
                global_arrays, parameters_to_ndarrays(fit_res.parameters), alpha_t
            )
            global_step += 1
            log(INFO, "step=%d staleness=%d alpha=%.4f loss=%.4f in_flight=%d",
                global_step, s, alpha_t, loss, len(in_flight))

        # 4) Periodic distributed evaluation.
        if cfg.evaluate_every and global_step % cfg.evaluate_every == 0:
            accuracy = _evaluate(grid, node_ids, global_arrays, cfg)
            log(INFO, "evaluation at step %d: accuracy=%.4f", global_step, accuracy)

    accuracy = _evaluate(grid, node_ids, global_arrays, cfg)
    log(INFO, "final accuracy=%.4f after %d steps", accuracy, global_step)
    context.state.config_records["fedasync.final_accuracy"] = ConfigRecord({"accuracy": accuracy})

    # Persist the final global model locally (gitignored) for offline inference.
    saved = save_parameters(global_arrays, cfg.output_path)
    log(INFO, "saved final global parameters to %s", saved)
