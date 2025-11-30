from __future__ import annotations
import numpy as np


def l2_normalize(vec: list[float] | np.ndarray) -> np.ndarray:
    v = np.asarray(vec, dtype=np.float32)
    norm = np.linalg.norm(v)
    if norm == 0.0:
        return v
    return v / norm


def to_bytes(vec: list[float] | np.ndarray) -> bytes:
    v = np.asarray(vec, dtype=np.float32)
    return v.tobytes()


def from_bytes(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)