#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gain match RX to TX RMS on low-amplitude TX samples. Port of gain_compensation.m."""

from __future__ import annotations

from typing import Tuple

import numpy as np


def gain_compensation(
    tx_data: np.ndarray,
    rx_data: np.ndarray,
    *,
    amp_thresh: float = 1000.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Scale RX so its RMS matches TX RMS on samples with |TX| < amp_thresh.

    MATLAB:
        location = find(abs(tx) < 1000)
        rx_gain = rx * tx_rms / rx_rms
    """
    tx = np.asarray(tx_data, dtype=np.complex128).reshape(-1)
    rx = np.asarray(rx_data, dtype=np.complex128).reshape(-1)
    if tx.shape != rx.shape:
        raise ValueError(f"tx/rx length mismatch: {tx.shape} vs {rx.shape}")

    location = np.flatnonzero(np.abs(tx) < amp_thresh)
    if location.size == 0:
        raise ValueError(f"no samples with |tx| < {amp_thresh} for gain match")

    tx_rms = float(np.sqrt(np.mean(np.abs(tx[location]) ** 2)))
    rx_rms = float(np.sqrt(np.mean(np.abs(rx[location]) ** 2)))
    if rx_rms <= 0:
        raise ValueError("rx_rms is zero; cannot gain-compensate")

    scale = tx_rms / rx_rms
    tx_out = tx.reshape(-1, 1)
    rx_out = (rx * scale).reshape(-1, 1)
    return tx_out, rx_out
