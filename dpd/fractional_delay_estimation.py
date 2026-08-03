#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fractional delay via parabolic peak on |conv| + spline resample. Port of fractional_delay_estimation.m."""

from __future__ import annotations

from typing import Optional

import numpy as np
from scipy.interpolate import interp1d


def fractional_delay_estimation(
    tx_data_norm: np.ndarray,
    pa_data_after_cfo_comp: np.ndarray,
    *,
    stf_len: int = 630,
    plot: bool = True,
) -> np.ndarray:
    """
    Estimate sub-sample delay from |conv(tx_stf, rx_stf)| peak, parabolic refine,
    then spline-interpolate the full PA sequence by that delay.

    Returns
    -------
    pa_after_frac_delay : complex (N, 1)
    """
    tx = np.asarray(tx_data_norm, dtype=np.complex128).reshape(-1)
    pa = np.asarray(pa_data_after_cfo_comp, dtype=np.complex128).reshape(-1)
    L = min(int(stf_len), len(tx), len(pa))
    tx_stf = tx[:L]
    rx_stf = pa[:L]

    # MATLAB conv is full convolution
    conv_results = np.abs(np.convolve(tx_stf, rx_stf, mode="full"))
    max_index = int(np.argmax(conv_results))  # 0-based
    max_value = float(conv_results[max_index])

    if max_index <= 0 or max_index >= len(conv_results) - 1:
        frac_delay = 0.0
    else:
        y0 = float(conv_results[max_index - 1])
        y1 = float(conv_results[max_index])
        y2 = float(conv_results[max_index + 1])
        a = (y2 + y0 - 2.0 * y1) / 2.0
        b = (y2 - y0) / 2.0
        if abs(a) < 1e-30:
            frac_delay = 0.0
        else:
            # Peak offset relative to discrete max_index (MATLAB 1-based index
            # cancels in -b/(2a) for the same parabola in sample units).
            frac_delay = -b / (2.0 * a)

    # MATLAB: output_x = input_x + frac_delay; interp1(..., 'spline')
    n = len(pa)
    input_x = np.arange(1, n + 1, dtype=float)
    output_x = input_x + frac_delay
    # spline on real/imag separately (complex interp1 in MATLAB)
    fr = interp1d(input_x, pa.real, kind="cubic", fill_value="extrapolate")
    fi = interp1d(input_x, pa.imag, kind="cubic", fill_value="extrapolate")
    pa_out = fr(output_x) + 1j * fi(output_x)

    if plot:
        import matplotlib.pyplot as plt

        xx1 = np.arange(1, len(conv_results) + 1, dtype=float)
        fig, ax = plt.subplots()
        ax.plot(xx1, conv_results)
        ax.set_xlim(626, 634)
        ax.set_ylim(max_value * 0.9, max_value * 1.1)
        if max_index > 0 and max_index < len(conv_results) - 1:
            y0 = float(conv_results[max_index - 1])
            y1 = float(conv_results[max_index])
            y2 = float(conv_results[max_index + 1])
            a = (y2 + y0 - 2.0 * y1) / 2.0
            b = (y2 - y0) / 2.0
            c = y1
            mid = max_index + 1  # MATLAB 1-based peak index
            xx = np.arange(1, len(conv_results) + 0.01, 0.01)
            yy = a * (xx - mid) ** 2 + b * (xx - mid) + c
            ax.plot(xx, yy, color="r")
        ax.set_title(f"Fractional delay peak (frac={frac_delay:.4f})")
        ax.grid(True)

        # After compensation STF check
        out0 = np.arange(1, L + 1, dtype=float) + frac_delay
        fr0 = interp1d(np.arange(1, L + 1, dtype=float), rx_stf.real, kind="cubic", fill_value="extrapolate")
        fi0 = interp1d(np.arange(1, L + 1, dtype=float), rx_stf.imag, kind="cubic", fill_value="extrapolate")
        rx_stf_c = fr0(out0) + 1j * fi0(out0)
        stf_conv = np.abs(np.convolve(tx_stf, rx_stf_c, mode="full"))
        fig2, ax2 = plt.subplots()
        ax2.plot(stf_conv)
        ax2.set_xlim(626, 634)
        ax2.set_title("After fractional delay compensation")
        ax2.grid(True)

    return pa_out.reshape(-1, 1)
