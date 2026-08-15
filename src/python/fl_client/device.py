from __future__ import annotations

import torch


def _cuda() -> torch.device:
    """Enable NVIDIA-GPU speedups and return the CUDA device."""
    if torch.backends.cudnn.enabled:
        torch.backends.cudnn.benchmark = True  # autotune conv kernels for fixed input sizes
    try:
        torch.set_float32_matmul_precision("high")  # use tensor cores where available
    except (AttributeError, RuntimeError):
        pass
    return torch.device("cuda")


def select_device(requested: str = "auto") -> torch.device:
    """Pick a torch device: ``auto`` prefers CUDA, then MPS, then CPU.

    When CUDA is selected, :func:`_cuda` enables ``cudnn.benchmark`` and
    higher-precision float32 matmuls, which meaningfully speed up
    ResNet-style training on NVIDIA GPUs.
    """
    requested = requested.lower()
    if requested == "auto":
        if torch.cuda.is_available():
            return _cuda()
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    if requested == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS was requested but is not available")
    if requested not in {"cpu", "cuda", "mps"}:
        raise ValueError("device must be auto, cpu, cuda, or mps")
    if requested == "cuda":
        return _cuda()
    return torch.device(requested)
