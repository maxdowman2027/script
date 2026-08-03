#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory / memoryless polynomial inverse LUT. Port of static_DPD_memory.m.

Basis on RX (y):  y * |y|^(m-1)  for m=1..order, and optional memory taps.
LUT on amplitude grid x: sum_m c_m * x^m  (same as MATLAB table build).
"""

from __future__ import annotations

from typing import Tuple

import numpy as np


def static_dpd_memory(
    max_table_value: float,
    x: np.ndarray,
    y: np.ndarray,
    num_lut: int = 1,
    est_delay: int = 0,
    order: int = 3,
    *,
    table_size: int = 32,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Parameters
    ----------
    max_table_value :
        Peak of LUT amplitude axis (MATLAB maxTableValue, e.g. 1023).
    x, y :
        Aligned complex TX (desired) and RX (PA) column vectors.
    num_lut, est_delay, order :
        Memory depth, TX delay, polynomial order (defaults match main).

    Returns
    -------
    table_x : (table_size,) real amplitude abscissa
    table_y : (table_size, num_lut) complex LUT values
    """
    x = np.asarray(x, dtype=np.complex128).reshape(-1)
    y = np.asarray(y, dtype=np.complex128).reshape(-1)
    if x.size != y.size:
        raise ValueError(f"x/y length mismatch: {x.size} vs {y.size}")

    delta = float(max_table_value) / float(table_size)
    table_x = np.arange(delta, max_table_value + delta * 0.5, delta)
    table_x = table_x[:table_size]

    L = y.size
    Y = np.zeros((L, order * num_lut), dtype=np.complex128)

    # X = [zeros(estDelay); x(1:end-estDelay)]
    if est_delay > 0:
        X = np.concatenate([np.zeros(est_delay, dtype=np.complex128), x[:-est_delay]])
    else:
        X = x.copy()

    for k in range(1, num_lut + 1):
        if k == 1:
            y_delay = y
        else:
            y_delay = np.concatenate(
                [np.zeros(k - 1, dtype=np.complex128), y[: -(k - 1)]]
            )
        for m in range(1, order + 1):
            col = (k - 1) * order + (m - 1)
            Y[:, col] = y_delay * (np.abs(y_delay) ** (m - 1))

    # coefEst = (Y' Y)^{-1} Y' X  — use least squares for stability
    coef_est, *_ = np.linalg.lstsq(Y, X, rcond=None)

    table_y = np.zeros((table_size, num_lut), dtype=np.complex128)
    for k in range(1, num_lut + 1):
        for m in range(1, order + 1):
            c = coef_est[(k - 1) * order + (m - 1)]
            table_y[:, k - 1] = table_y[:, k - 1] + c * (table_x ** m)

    return table_x, table_y
