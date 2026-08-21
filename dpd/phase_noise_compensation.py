#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compensate slow common phase noise on RX using TX as phase reference.

After CFO (linear phase) removal, residual ``angle(tx * conj(rx))`` still
contains instrument/LO phase wander plus PA AM-PM. AM-PM is fit vs |TX| and
subtracted; the leftover is low-pass filtered as PN and removed from RX so
LUT fitting is not biased by iQxel LO wander.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np

PathLike = Union[str, Path]

# Default smooth window (samples @ ~80 MHz ≈ 3.2 µs); must be odd for centered MA.
DEFAULT_SMOOTH_WIN = 257
# Use |TX| >= ratio * peak for AM-PM / PN anchors (reject noisy low-amp phase).
DEFAULT_AMP_RATIO = 0.25
# AM-PM polynomial degree vs |TX| before PN residual smoothing.
DEFAULT_AMPM_DEGREE = 2


def _moving_average(x: np.ndarray, win: int) -> np.ndarray:
    w = int(win)
    if w < 3:
        return np.asarray(x, dtype=float).copy()
    if w % 2 == 0:
        w += 1
    k = np.ones(w, dtype=float) / float(w)
    pad = w // 2
    xp = np.pad(np.asarray(x, dtype=float), (pad, pad), mode="edge")
    return np.convolve(xp, k, mode="valid")


def phase_noise_compensation(
    tx_data: np.ndarray,
    rx_data: np.ndarray,
    *,
    smooth_win: int = DEFAULT_SMOOTH_WIN,
    amp_ratio: float = DEFAULT_AMP_RATIO,
    ampm_degree: int = DEFAULT_AMPM_DEGREE,
    plot: bool = True,
    save_dir: Optional[PathLike] = None,
    tag: str = "pn",
    show: bool = False,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Remove slow common phase from RX (TX reference).

    Parameters
    ----------
    tx_data, rx_data :
        Aligned complex column/row vectors (same length preferred).
    smooth_win :
        Moving-average length for PN estimate (samples).
    amp_ratio :
        High-|TX| mask threshold as fraction of peak (fit anchors).
    ampm_degree :
        Polynomial degree for AM-PM vs |TX| stripped before PN smooth.

    Returns
    -------
    rx_comp : (N, 1) complex
        RX after multiplying by ``exp(j * pn_est)``.
    pn_est : (N,) float
        Estimated common phase (rad) removed from RX.
    """
    tx = np.asarray(tx_data, dtype=np.complex128).reshape(-1)
    rx = np.asarray(rx_data, dtype=np.complex128).reshape(-1)
    n = min(tx.size, rx.size)
    if n < 8:
        return rx.reshape(-1, 1), np.zeros(max(rx.size, 0), dtype=float)

    tx, rx = tx[:n], rx[:n]
    phi = np.unwrap(np.angle(tx * np.conj(rx)))

    amp = np.abs(tx)
    peak = float(amp.max()) if amp.size else 0.0
    thr = float(amp_ratio) * peak
    mask = amp >= thr if peak > 0 else np.ones(n, dtype=bool)
    idx = np.flatnonzero(mask)

    deg = int(ampm_degree)
    if deg < 0:
        deg = 0
    if idx.size >= max(deg + 2, 16):
        coef = np.polyfit(amp[idx], phi[idx], deg)
        ampm = np.polyval(coef, amp)
    else:
        ampm = np.full(n, float(np.mean(phi)), dtype=float)

    resid = phi - ampm
    # Interpolate residual on full grid from high-SNR anchors, then low-pass → PN
    if idx.size >= max(16, int(smooth_win) // 4):
        resid_anchor = np.interp(
            np.arange(n, dtype=float), idx.astype(float), resid[idx]
        )
    else:
        resid_anchor = resid

    pn_est = _moving_average(resid_anchor, int(smooth_win))
    pn_est = pn_est - float(np.mean(pn_est))

    rx_comp = rx * np.exp(1j * pn_est)

    do_plot = bool(plot or save_dir is not None or show)
    if do_plot:
        import matplotlib

        if not show and save_dir is not None:
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        x = np.arange(1, n + 1)
        fig, axes = plt.subplots(3, 1, figsize=(10, 8.5), sharex=True)
        ax0, ax1, ax2 = axes
        ax0.plot(x, phi, lw=0.7, alpha=0.65, label="corr phase")
        ax0.plot(x, ampm, lw=1.2, color="C1", label=f"AM-PM poly deg={deg}")
        ax0.set_ylabel("Phase (rad)")
        ax0.set_title("Residual phase before PN (TX·conj(RX))")
        ax0.grid(True, alpha=0.35)
        ax0.legend(loc="best")

        ax1.plot(x, resid, lw=0.7, alpha=0.65, label="phase − AM-PM")
        ax1.plot(x, pn_est, lw=1.6, color="r", label="PN estimate")
        ax1.set_ylabel("Phase (rad)")
        ax1.set_title("PN residual (AM-PM removed)")
        ax1.grid(True, alpha=0.35)
        ax1.legend(loc="best")

        phi2 = np.unwrap(np.angle(tx * np.conj(rx_comp)))
        ax2.plot(x, phi2, lw=0.8, label="corr phase after PN")
        ax2.set_xlabel("Sample")
        ax2.set_ylabel("Phase (rad)")
        ax2.set_title("Residual phase after PN compensation")
        ax2.grid(True, alpha=0.35)
        ax2.legend(loc="best")
        fig.tight_layout()

        if save_dir is not None:
            out = Path(save_dir)
            out.mkdir(parents=True, exist_ok=True)
            stem = f"{tag}_phase"
            fig.savefig(out / f"{stem}.pdf")
            fig.savefig(out / f"{stem}.png", dpi=120)
            print(f"[PLOT] PN → {out / (stem + '.png')}")

        if show:
            plt.show()
        else:
            plt.close(fig)

    phi_after = np.unwrap(np.angle(tx * np.conj(rx_comp)))
    print(
        f"[PN] smooth_win={int(smooth_win)}  amp_ratio={float(amp_ratio):.3g}  "
        f"ampm_deg={deg}  anchors={int(idx.size)}/{n}  "
        f"pn_rms={float(np.std(pn_est)):.4g} rad  "
        f"phase_std {float(np.std(phi)):.4g}→{float(np.std(phi_after)):.4g} rad"
    )

    return rx_comp.reshape(-1, 1), pn_est
