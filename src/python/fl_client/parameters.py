from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Iterable, Union

import numpy as np
import torch
from torch import nn


def get_parameters(model: nn.Module) -> list[np.ndarray]:
    return [value.detach().cpu().numpy().copy() for _, value in model.state_dict().items()]


def set_parameters(model: nn.Module, parameters: Iterable[np.ndarray]) -> None:
    state = model.state_dict()
    values = list(parameters)
    if len(values) != len(state):
        raise ValueError("parameter count does not match model state")
    converted = OrderedDict()
    for (name, expected), received in zip(state.items(), values):
        array = np.asarray(received)
        if tuple(array.shape) != tuple(expected.shape):
            raise ValueError(f"parameter shape mismatch for {name}")
        tensor = torch.as_tensor(array, dtype=expected.dtype)
        converted[name] = tensor
    try:
        model.load_state_dict(converted, strict=True)
    except RuntimeError as exc:
        raise ValueError("received parameters are incompatible with model") from exc


def save_parameters(arrays: Iterable[np.ndarray], path: Union[str, Path]) -> Path:
    """Persist a list of parameter arrays to a local .npz file (one array per layer).

    Array order is preserved so :func:`load_parameters` can round-trip them back
    into a list. ``path`` may sit in a gitignored directory (see ``.gitignore``).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, *list(arrays))
    return path


def load_parameters(path: Union[str, Path]) -> list[np.ndarray]:
    """Load parameter arrays previously written by :func:`save_parameters`."""
    with np.load(Path(path)) as archive:
        return [archive[key] for key in archive.files]
