#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CFO estimate via correlation phase polyfit + compensate. Port of frequency_offset_estimation.m."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np

PathLike = Union[str, Path]


def frequency_offset_estimation(
    tx_data_norm: np.ndarray,
    pa_data_norm: np.ndarray,
    *,
    corr_len: int = 5000,
    plot: bool = True,
    axes: Optional[Tuple] = None,
    save_dir: Optional[PathLike] = None,
    tag: str = "cfo",
    show: bool = False,
) -> np.ndarray:
    """
    Estimate residual CFO from angle(tx * conj(pa)) linear fit, then rotate PA.

    MATLAB uses ``phase()`` (unwrapped). Here: ``np.unwrap(np.angle(...))``.

    If ``save_dir`` is set, writes:
      ``{tag}_before.pdf/.png`` — corr phase + polyfit (before compensate)
      ``{tag}_after.pdf/.png``  — phase after compensate

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

    do_plot = bool(plot or save_dir is not None or show)
    if do_plot:
        import matplotlib

        if not show and save_dir is not None:
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if axes is None:
            fig1, ax1 = plt.subplots(figsize=(10, 4.5))
            fig2, ax2 = plt.subplots(figsize=(10, 4.5))
        else:
            ax1, ax2 = axes
            fig1 = ax1.figure
            fig2 = ax2.figure

        # Before: corr phase (length L) + fitted line over full N (MATLAB style)
        ax1.plot(np.arange(1, L + 1), phase1, label="corr phase")
        ax1.plot(x1, fit_result, linewidth=4, color="r", label="polyfit")
        ax1.set_title(
            "Phase of Tx and PA data correlation results, before CFO compensation"
        )
        ax1.set_xlabel("Sample")
        ax1.set_ylabel("Phase (rad)")
        ax1.grid(True)
        ax1.legend(loc="best")
        fig1.tight_layout()

        corr2 = tx * np.conj(pa_comp)
        phase2 = np.unwrap(np.angle(corr2))
        coef2 = np.polyfit(x1, phase2, 1)
        fit2 = coef2[0] * x1 + coef2[1]
        ax2.plot(x1, phase2, label="corr phase")
        ax2.plot(x1, fit2, linewidth=4, color="r", label="polyfit")
        ax2.set_title("Phase after CFO compensation")
        ax2.set_xlabel("Sample")
        ax2.set_ylabel("Phase (rad)")
        ax2.grid(True)
        ax2.legend(loc="best")
        fig2.tight_layout()

        if save_dir is not None:
            out = Path(save_dir)
            out.mkdir(parents=True, exist_ok=True)
            for fig, name in ((fig1, "before"), (fig2, "after")):
                stem = f"{tag}_{name}"
                fig.savefig(out / f"{stem}.pdf")
                fig.savefig(out / f"{stem}.png", dpi=120)
            print(f"[PLOT] CFO → {out / (tag + '_before.png')}, {out / (tag + '_after.png')}")

        if show:
            plt.show()
        elif axes is None:
            plt.close(fig1)
            plt.close(fig2)

    return pa_comp.reshape(-1, 1)
