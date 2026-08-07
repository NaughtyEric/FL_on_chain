from __future__ import annotations

from collections import OrderedDict
from typing import Iterable

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
