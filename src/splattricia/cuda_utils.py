from __future__ import annotations

import gc

import torch


def require_cuda() -> torch.device:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA ist nicht verfügbar.")
    return torch.device("cuda")



def release_cuda_cache() -> None:
    gc.collect()
    torch.cuda.empty_cache()
