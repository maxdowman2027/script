#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CFO estimate via correlation phase polyfit + compensate. Port of frequency_offset_estimation.m."""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np


def frequency_offset_estimation(
    tx_data_norm: np.ndarray,
    pa_data_norm: np.ndarray,
    *,
    corr_len: int = 3500,
    plot: bool = True,
    axes: Optional[Tuple] = None,
) -> np.ndarray:
    """
    Estimate residual CFO from angle(tx * conj(pa)) linear fit, then rotate PA.

    MATLAB uses ``phase()`` (unwrapped). Here: ``np.unwrap(np.angle(...))``.

    Returns
    -------
    pa_data_after_cfo_comp : complex (N, 1)
    """
    tx = np.asarray(tx_data_norm, dtype=np.complex128).reshape(-1)
    pa = np.asarray(pa_data_norm, dtype=np.complex128).reshape(-1)
    n = min(len(tx), len(pa))
    tx, pa = tx[:n], pa[:n]
    L = min(int(corr_len), n)

    corr = tx[:L] * np.conj(pa[:L])
    phase1 = np.unwrap(np.angle(corr))
    x = np.arange(1, L + 1, dtype=float)
    # polyfit degree 1 → [slope, intercept] (same as MATLAB polyfit)
    coef1 = np.polyfit(x, phase1, 1)
    x1 = np.arange(1, n + 1, dtype=float)
    fit_result = coef1[0] * x1 + coef1[1]

    pa_comp = pa * np.exp(1j * fit_result)

    if plot:
        import matplotlib.pyplot as plt

        if axes is None:
            fig1, ax1 = plt.subplots()
            fig2, ax2 = plt.subplots()
        else:
            ax1, ax2 = axes

        ax1.plot(phase1, label="corr phase")
        ax1.plot(x1, fit_result, linewidth=4, color="r", label="polyfit")
        ax1.set_title("Phase of Tx and PA data correlation results, before CFO compensation")
        ax1.grid(True)
        ax1.legend(loc="best")

        corr2 = tx * np.conj(pa_comp)
        phase2 = np.unwrap(np.angle(corr2))
        coef2 = np.polyfit(x1, phase2, 1)
        fit2 = coef2[0] * x1 + coef2[1]
        ax2.plot(phase2)
        ax2.plot(fit2, linewidth=4, color="r")
        ax2.set_title("Phase after CFO compensation")
        ax2.grid(True)

    return pa_comp.reshape(-1, 1)
