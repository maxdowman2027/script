#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove mean DC on a short window. Port of dc_compensation.m."""

from __future__ import annotations

from typing import Tuple

import numpy as np


def dc_compensation(
    tx_data: np.ndarray,
    rx_data: np.ndarray,
    *,
    start_point: int = 600,
    length: int = 256,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Subtract mean over [start_point : start_point+L) (MATLAB 1-based start_point).

    Notes
    -----
    In xian_static_DPD_main1.m, TX argument is raw sliced TX (not gain-compensated).
    """
    tx = np.asarray(tx_data, dtype=np.complex128).reshape(-1)
    rx = np.asarray(rx_data, dtype=np.complex128).reshape(-1)
    i0 = int(start_point) - 1
    i1 = i0 + int(length)
    if i1 > len(tx) or i1 > len(rx) or i0 < 0:
        raise ValueError(
            f"DC window [{start_point}:{start_point + length - 1}] out of range "
            f"(tx={len(tx)}, rx={len(rx)})"
        )

    tx_dc_est = np.mean(tx[i0:i1])
    rx_dc_est = np.mean(rx[i0:i1])
    return (tx - tx_dc_est).reshape(-1, 1), (rx - rx_dc_est).reshape(-1, 1)
