#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AM-AM / AM-PM scatter + LUT overlay. Port of amamplot.m."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import numpy as np

PathLike = Union[str, Path]


def amamplot(
    ref_data: np.ndarray,
    rx_data: np.ndarray,
    table_x: np.ndarray,
    table_y: np.ndarray,
    names1: str = "PA-Rx",
    *,
    save_dir: Optional[PathLike] = None,
    show: bool = False,
) -> None:
    """
    Plot AM-AM (|x| vs |y|) and AM-PM (atan(imag(y*conj(x))/real(...))).
    Prepends (0,0) to LUT curves like MATLAB.
    """
    import matplotlib

    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = np.asarray(ref_data, dtype=np.complex128).reshape(-1)
    y = np.asarray(rx_data, dtype=np.complex128).reshape(-1)
    table_x = np.asarray(table_x, dtype=float).reshape(-1)
    table_y = np.asarray(table_y, dtype=np.complex128)
    if table_y.ndim == 1:
        table_y = table_y.reshape(-1, 1)
    num_lut = table_y.shape[1]

    tx = np.concatenate([[0.0], table_x])
    ty = np.vstack([np.zeros((1, num_lut), dtype=np.complex128), table_y])

    # --- AM-AM ---
    fig1, ax1 = plt.subplots()
    h = []
    legend_names = []
    (ln,) = ax1.plot(np.abs(x), np.abs(y), marker="o", linestyle="none")
    h.append(ln)
    legend_names.append("PA")
    for n in range(num_lut):
        (ln,) = ax1.plot(np.abs(tx), np.abs(ty[:, n]), linewidth=4)
        h.append(ln)
        legend_names.append(f"LUT index{n + 1}")
    ax1.set_title(f"{names1}, AM-AM curve")
    ax1.set_aspect("equal", adjustable="box")
    ax1.grid(True, which="both")
    ax1.minorticks_on()
    ax1.set_xlim(0, 1500)
    ax1.set_ylim(0, 1500)
    ax1.set_xlabel("AM")
    ax1.set_ylabel("AM")
    ax1.legend(h, legend_names)

    # --- AM-PM ---
    fig2, ax2 = plt.subplots()
    phase1 = y * np.conj(x)
    with np.errstate(divide="ignore", invalid="ignore"):
        # Match MATLAB atan(imag/real); arctan2 is safer but changes branch cuts.
        pm = np.arctan(np.imag(phase1) / np.real(phase1))
    h2 = []
    legend2 = []
    (ln,) = ax2.plot(np.abs(x), pm, marker="o", linestyle="none")
    h2.append(ln)
    legend2.append("PA")
    # polyfit degree 2 on AM-PM cloud (skip if TX/PM empty — e.g. all-zero ref)
    amp = np.abs(x)
    mask = np.isfinite(pm) & np.isfinite(amp) & (amp > 0)
    if np.count_nonzero(mask) >= 3:
        phase_coef = np.polyfit(amp[mask], pm[mask], 2)
        xx = np.arange(1, 1024, dtype=float)
        yy = phase_coef[2] + phase_coef[1] * xx + phase_coef[0] * xx**2
        (ln,) = ax2.plot(xx, yy, linestyle="-", color="green", linewidth=2)
        h2.append(ln)
        legend2.append("PA fit")
    else:
        print("[amamplot] skip AM-PM polyfit: no finite |TX|>0 samples")

    ty_plot = ty.copy()
    # MATLAB: tableY(2,:) = real(tableY(2,:));
    if ty_plot.shape[0] > 1:
        ty_plot[1, :] = np.real(ty_plot[1, :])

    for n in range(num_lut):
        with np.errstate(divide="ignore", invalid="ignore"):
            pm_lut = np.arctan(np.imag(ty_plot[:, n]) / np.real(ty_plot[:, n]))
        (ln,) = ax2.plot(np.abs(tx), pm_lut, linewidth=4)
        h2.append(ln)
        legend2.append(f"LUT index{n + 1}")
    ax2.set_xlabel("AM")
    ax2.set_ylabel("PM")
    ax2.legend(h2, legend2)
    ax2.set_title(f"{names1}, AM-PM curve")
    ax2.grid(True)

    if save_dir is not None:
        out = Path(save_dir)
        out.mkdir(parents=True, exist_ok=True)
        fig1.savefig(out / f"{names1}_amam.pdf")
        fig2.savefig(out / f"{names1}_ampm.pdf")
        fig1.savefig(out / f"{names1}_amam.png", dpi=120)
        fig2.savefig(out / f"{names1}_ampm.png", dpi=120)

    if show:
        plt.show()
    else:
        plt.close(fig1)
        plt.close(fig2)
