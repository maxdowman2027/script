#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xian static DPD training pipeline — Python port of xian_static_DPD_main1.m.

Aligned with ``dpd/20260804_3_data/xian_static_DPD_main1.m``:

  read_data(CSV) → TX (ref / dac / adc) → RX (iqxel / feedback)
  → auto envelope align → gain → CFO → (iQxel) PN → DC → frac delay → LUT

  iQxel dump: residual phase noise is low-pass removed (TX-referenced) before
  LUT estimation so instrument LO wander does not bias AM-PM / LUT coeffs.

DAC vs iQxel (OFDM or CW tone; tone auto-detected)::

  python dpd/xian_static_dpd_main1.py --csv dac_iladata.csv --txt iqxel.txt --tx-source dac --rx txt

  python dpd/xian_static_dpd_main1.py --csv tone/dac_iladata.csv --txt tone/iqxel_2412_tone.txt --tx-source dac --rx txt --signal-mode tone

ref (CSV-A) vs dac (CSV-B)::

  python dpd/xian_static_dpd_main1.py --csv feedback_ref_iladata.csv --tx-source ref --dac-csv dac_iladata.csv --rx dac

ref_iladata (dac_* cols as TX) vs dac_iladata (RX)::

  python dpd/xian_static_dpd_main1.py --csv ref_iladata.csv --tx-source dac --dac-csv dac_iladata.csv --rx dac

ref (4x ILA) vs pkt_out dac (label 2x; same ILA clock → keep default OSR, global align)::

  python dpd/xian_static_dpd_main1.py --csv feedback_ref_iladata.csv --tx-source ref --dac-csv pkt_out_iladata.csv --rx dac

True half-rate dump vs 4x (resample to work OSR)::

  python dpd/xian_static_dpd_main1.py --csv feedback_ref.csv --csv-osr 4 --dac-csv pkt_out.csv --dac-csv-osr 2 --work-osr 2 --tx-source ref --rx dac

ILA on-chip (ref vs feedback)::

  python dpd/xian_static_dpd_main1.py --csv ... --rx feedback --tx-source ref

iQxel + ref::

  python dpd/xian_static_dpd_main1.py --csv ... --txt ... --rx txt --tx-source ref

All helper modules live in the same directory (dpd/).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Union

import numpy as np

# Allow `python dpd/xian_static_dpd_main1.py` and `python -m` from repo root
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from amamplot import amamplot  # noqa: E402
from dc_compensation import dc_compensation  # noqa: E402
from fractional_delay_estimation import fractional_delay_estimation  # noqa: E402
from frequency_offset_estimation import frequency_offset_estimation  # noqa: E402
from gain_compensation import gain_compensation  # noqa: E402
from phase_noise_compensation import (  # noqa: E402
    DEFAULT_AMP_RATIO as PN_AMP_RATIO_DEFAULT,
    DEFAULT_SMOOTH_WIN as PN_SMOOTH_WIN_DEFAULT,
    phase_noise_compensation,
)
from read_data import load_iqxel_txt, read_data, resample_iq_to_osr  # noqa: E402
from static_dpd_memory import static_dpd_memory  # noqa: E402

PathLike = Union[str, Path]

# =============================================================================
# Config (mirrors 20260804_3_data/xian_static_DPD_main1.m)
# =============================================================================
DATA_DIR = _THIS_DIR / "20260804_3_data"
INPUT_CSV = DATA_DIR / "feedback_ref_gain1_168_gain2_127_iladata2.csv"
# MATLAB: load(..._short.mat).rx_data
RX_MAT = DATA_DIR / "iqxel_2412_gain1_168_gain2_127_short.mat"
RX_TXT = DATA_DIR / "iqxel_2412_gain1_168_gain2_127.txt"
# 0 = auto (160 Msps LitePoint → stride 2); else keep every N-th sample
RX_TXT_STRIDE = 0

# MATLAB: tx_data(313:313+7000,:), rx_data(1596:1596+7000,:), then both (1:5500,:)
TX_SLICE_START = 313  # 1-based
RX_SLICE_START = 1596  # 1-based
SLICE_LEN = 7001  # inclusive end = start + 7000 → length 7001
ALIGN_LEN = 7000

# Zoom window for align_time_domain plot (0-based, end exclusive → shows [5000, 7000))
ALIGN_PLOT_START = 5000
ALIGN_PLOT_END = 7000

# Integer-sample envelope align (abs cross-corr) before gain/CFO
COARSE_ALIGN = True
COARSE_MAX_LAG = 512  # local refine / feedback-mode ±search
# Global search length into iQxel capture (0-based samples after txt stride).
# Large enough to find packet start when default rx_slice_start is wrong.
COARSE_SEARCH_LEN = 500_000

# Sample rate of post-decimate ILA / post-stride iQxel streams (Hz)
FS_HZ = 80e6
# CW / single-tone: |x| crest variation below this → tone mode
TONE_CV_MAX = 0.05

DPD_TRIM_START = 1000  # MATLAB (1000:end) 1-based → Python 999:
AMP_THRESH = 800.0
CFO_CORR_LEN = 5000

# Phase-noise compensation (iQxel TX-referenced residual phase low-pass)
# "auto" → enable only when RX is iQxel (txt/mat); True/False force on/off.
PN_COMP = "auto"
PN_SMOOTH_WIN = PN_SMOOTH_WIN_DEFAULT
PN_AMP_RATIO = PN_AMP_RATIO_DEFAULT

MAX_TABLE_VALUE = 1023
NUM_LUT = 1
EST_DELAY = 0
ORDER = 3
NITER = 1

OUTPUT_DIR = _THIS_DIR / "output" / "xian_static_dpd"


def _as_col(z: np.ndarray) -> np.ndarray:
    return np.asarray(z, dtype=np.complex128).reshape(-1, 1)


def estimate_envelope_delay(
    tx: np.ndarray,
    rx: np.ndarray,
    *,
    max_lag: int = COARSE_MAX_LAG,
) -> int:
    """
    Integer lag of |RX| vs |TX| via abs cross-correlation.

    Positive lag ⇒ RX is late relative to TX ⇒ drop ``rx[:lag]``.
    Negative lag ⇒ RX is early ⇒ drop ``tx[:-lag]``.
    """
    from scipy.signal import correlate

    a = np.abs(np.asarray(tx, dtype=np.complex128).reshape(-1)).astype(float)
    b = np.abs(np.asarray(rx, dtype=np.complex128).reshape(-1)).astype(float)
    n = min(a.size, b.size)
    if n < 8:
        return 0
    a, b = a[:n], b[:n]
    a = a - a.mean()
    b = b - b.mean()
    c = correlate(b, a, mode="full")
    mid = n - 1
    ml = min(int(max_lag), n - 1)
    i0 = mid - ml
    i1 = mid + ml + 1
    k = i0 + int(np.argmax(c[i0:i1]))
    return int(k - mid)


def apply_integer_delay(
    tx: np.ndarray,
    rx: np.ndarray,
    lag: int,
) -> tuple:
    """Trim TX/RX to apply integer lag; returns (tx, rx, n)."""
    tx = np.asarray(tx, dtype=np.complex128).reshape(-1)
    rx = np.asarray(rx, dtype=np.complex128).reshape(-1)
    if lag > 0:
        rx = rx[lag:]
    elif lag < 0:
        tx = tx[-lag:]
    n = min(tx.size, rx.size)
    return _as_col(tx[:n]), _as_col(rx[:n]), n


def coarse_align_streams(
    tx: np.ndarray,
    rx: np.ndarray,
    *,
    max_lag: int = COARSE_MAX_LAG,
) -> tuple:
    """
    Coarse-align RX to TX using envelope correlation.

    Returns ``(tx_aln, rx_aln, lag)``.
    """
    lag = estimate_envelope_delay(tx, rx, max_lag=max_lag)
    tx_a, rx_a, _ = apply_integer_delay(tx, rx, lag)
    return tx_a, rx_a, lag


def find_best_rx_start_envelope(
    tx: np.ndarray,
    rx_full: np.ndarray,
    *,
    search_len: Optional[int] = None,
    template_len: Optional[int] = None,
    hint_start: Optional[int] = None,
    local_radius: Optional[int] = None,
) -> tuple:
    """
    Find 0-based start index in ``rx_full`` that best matches |TX| envelope.

    If ``local_radius`` and ``hint_start`` are set, only search that neighborhood;
    otherwise search ``[0, search_len)``.

    Returns ``(start0, score)`` where score is normalized correlation in [-1, 1].
    """
    from scipy.signal import correlate

    tx = np.asarray(tx, dtype=np.complex128).reshape(-1)
    rx_full = np.asarray(rx_full, dtype=np.complex128).reshape(-1)
    if tx.size < 8 or rx_full.size < 8:
        return 0, 0.0

    win = int(template_len) if template_len else min(5000, tx.size)
    win = min(win, tx.size, rx_full.size)
    ta = np.abs(tx[:win]).astype(float)
    ta = ta - ta.mean()
    ta_n = float(np.linalg.norm(ta)) + 1e-12

    if local_radius is not None and hint_start is not None:
        i0 = max(0, int(hint_start) - int(local_radius))
        i1 = min(rx_full.size - win + 1, int(hint_start) + int(local_radius) + 1)
        if i1 <= i0:
            i0, i1 = 0, min(rx_full.size - win + 1, max(1, int(local_radius) * 2))
        seg = rx_full[i0 : i1 + win - 1]
        base = i0
    else:
        sl = int(search_len) if search_len and search_len > 0 else rx_full.size
        sl = min(sl, rx_full.size - win + 1)
        if sl < 1:
            return 0, 0.0
        seg = rx_full[: sl + win - 1]
        base = 0

    rb = np.abs(seg).astype(float)
    c = correlate(rb - rb.mean(), ta, mode="valid")
    if c.size < 1:
        return 0, 0.0
    peak_rel = int(np.argmax(c))
    start0 = base + peak_rel

    # normalized score at peak
    rw = np.abs(rx_full[start0 : start0 + win]).astype(float)
    rw = rw - rw.mean()
    score = float(np.dot(ta, rw) / (ta_n * (float(np.linalg.norm(rw)) + 1e-12)))
    return start0, score


def is_cw_tone(x: np.ndarray, *, max_cv: float = TONE_CV_MAX) -> bool:
    """True if |x| is nearly constant (CW / single-tone)."""
    a = np.abs(np.asarray(x, dtype=np.complex128).reshape(-1))
    if a.size < 16:
        return False
    m = float(np.mean(a))
    if m <= 1e-12:
        return False
    return float(np.std(a) / m) <= float(max_cv)


def estimate_tone_hz(x: np.ndarray, fs: float) -> float:
    """Peak FFT bin frequency (Hz), signed via fftfreq."""
    x = np.asarray(x, dtype=np.complex128).reshape(-1)
    n = min(8192, int(x.size))
    if n < 8 or fs <= 0:
        return 0.0
    w = np.hanning(n)
    X = np.fft.fft(x[:n] * w)
    f = np.fft.fftfreq(n, d=1.0 / float(fs))
    return float(f[int(np.argmax(np.abs(X)))])


def find_rx_tone_start(
    rx_full: np.ndarray,
    n_need: int,
    *,
    search_len: Optional[int] = None,
    level: float = 0.5,
) -> int:
    """
    First index where |RX| stays near its peak (skip quiet/settling head).

    Continuous tone has no packet edge; pick a stable high-level region.
    """
    rx = np.asarray(rx_full, dtype=np.complex128).reshape(-1)
    if rx.size < 8:
        return 0
    sl = min(int(search_len) if search_len else rx.size, rx.size)
    a = np.abs(rx[:sl])
    peak = float(np.max(a))
    if peak <= 0:
        return 0
    thr = float(level) * peak
    run = max(16, min(int(n_need) // 20, 256))
    above = (a >= thr).astype(np.float64)
    if above.size < run:
        return 0
    s = np.convolve(above, np.ones(run), mode="valid")
    hits = np.flatnonzero(s >= run * 0.95)
    if hits.size == 0:
        return int(np.argmax(a))
    start = int(hits[0])
    if start + int(n_need) > rx.size:
        start = max(0, rx.size - int(n_need))
    return start


def estimate_complex_delay(
    tx: np.ndarray,
    rx: np.ndarray,
    *,
    max_lag: int = 64,
) -> int:
    """Integer lag maximizing |corr| after removing DC (for CW refine)."""
    from scipy.signal import correlate

    a = np.asarray(tx, dtype=np.complex128).reshape(-1)
    b = np.asarray(rx, dtype=np.complex128).reshape(-1)
    n = min(a.size, b.size)
    if n < 8:
        return 0
    a = a[:n] - np.mean(a[:n])
    b = b[:n] - np.mean(b[:n])
    c = correlate(b, a, mode="full")
    mid = n - 1
    ml = min(int(max_lag), n - 1)
    i0 = mid - ml
    i1 = mid + ml + 1
    k = i0 + int(np.argmax(np.abs(c[i0:i1])))
    return int(k - mid)


def find_best_rx_start_tone(
    tx: np.ndarray,
    rx_full: np.ndarray,
    *,
    fs: float = FS_HZ,
    search_len: Optional[int] = None,
    template_len: int = 2048,
) -> tuple:
    """
    CW align: wipe TX tone freq on both, complex-corr template in RX search.

    Returns ``(start0, score, f_tx_hz, f_rx_hz)``.
    """
    from scipy.signal import correlate

    tx = np.asarray(tx, dtype=np.complex128).reshape(-1)
    rx = np.asarray(rx_full, dtype=np.complex128).reshape(-1)
    f_tx = estimate_tone_hz(tx, fs)
    f_rx = estimate_tone_hz(rx[: min(rx.size, int(search_len or 200_000))], fs)

    win = min(int(template_len), tx.size, 4096)
    if win < 16 or rx.size < win:
        return find_rx_tone_start(rx, win), 0.0, f_tx, f_rx

    n_t = np.arange(win, dtype=np.float64)
    # Mix TX template to DC using TX tone; mix RX with same LO (CFO left for later)
    lo_tx = np.exp(-1j * 2 * np.pi * f_tx * n_t / float(fs))
    tmpl = (tx[:win] - np.mean(tx[:win])) * lo_tx
    tmpl = tmpl - np.mean(tmpl)
    tn = float(np.linalg.norm(tmpl)) + 1e-12

    sl = int(search_len) if search_len and search_len > 0 else min(rx.size, 200_000)
    sl = min(sl, rx.size - win + 1)
    if sl < 1:
        return 0, 0.0, f_tx, f_rx

    n_r = np.arange(sl + win - 1, dtype=np.float64)
    rx_mix = (rx[: sl + win - 1] - np.mean(rx[: sl + win - 1])) * np.exp(
        -1j * 2 * np.pi * f_tx * n_r / float(fs)
    )
    c = correlate(rx_mix, tmpl, mode="valid")
    peak = int(np.argmax(np.abs(c)))
    start0 = peak
    # coherence-like score
    seg = rx_mix[peak : peak + win]
    score = float(np.abs(np.vdot(seg, tmpl)) / (tn * (float(np.linalg.norm(seg)) + 1e-12)))
    # Prefer a stable-level start if complex score is weak (flat CW corr)
    if score < 0.15:
        start0 = find_rx_tone_start(rx, win, search_len=sl + win)
        score = float(score)
    return start0, score, f_tx, f_rx


def load_rx_full_capture(
    *,
    prefer: str,
    mat_path: Path,
    txt_path: Path,
    txt_stride: int,
    csv_rx: Optional[np.ndarray],
) -> np.ndarray:
    """Load entire RX capture (no slice) for global coarse align."""
    mode = prefer.lower()
    if mode == "csv":
        if csv_rx is None:
            raise FileNotFoundError("no CSV feedback")
        return np.asarray(csv_rx, dtype=np.complex128).reshape(-1)

    if mode in ("auto", "mat") and mat_path.is_file():
        from scipy.io import loadmat

        m = loadmat(str(mat_path))
        key = _mat_rx_key(m)
        return np.asarray(m[key], dtype=np.complex128).reshape(-1)

    if mode in ("auto", "txt") and txt_path.is_file():
        return load_iqxel_txt(txt_path, stride=int(txt_stride)).reshape(-1)

    if mode == "auto" and csv_rx is not None:
        return np.asarray(csv_rx, dtype=np.complex128).reshape(-1)

    raise FileNotFoundError(f"cannot load full RX for prefer={prefer!r}")


def write_lut_data_map(
    table_y: np.ndarray,
    out_path: PathLike,
    *,
    scale: float = 128.0,
) -> Path:
    """
    Write LUT as ``lut_data_map_lut{k}`` dicts matching wifi_dpd_test_wifi7.py.

    Index 0 is always ``{\"i\": 0, \"q\": 0}`` (same prepend as MATLAB write_data /
    amamplot). Entries 1..N are ``round(real(table_y)*scale)`` /
    ``round(imag(table_y)*scale)``.
    """
    ty = np.asarray(table_y, dtype=np.complex128)
    if ty.ndim == 1:
        ty = ty.reshape(-1, 1)
    n_row, n_lut = ty.shape
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Auto-generated by xian_static_dpd_main1.py",
        f"# scale={scale:g}: i,q = round(LUT * {scale:g}); index 0 is zero pad",
        f"# table_y shape=({n_row}, {n_lut})",
        "",
    ]
    for k in range(n_lut):
        lines.append(f"lut_data_map_lut{k} = {{")
        lines.append('    0: {"i": 0, "q": 0},')
        for n in range(n_row):
            i_val = int(np.round(np.real(ty[n, k]) * scale))
            q_val = int(np.round(np.imag(ty[n, k]) * scale))
            comma = "," if n < n_row - 1 else ","
            lines.append(f'    {n + 1}: {{"i": {i_val}, "q": {q_val}}}{comma}')
        lines.append("}")
        lines.append("")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[LUT] map dict → {out}  (×{scale:g}, {n_lut} LUT(s), {n_row}+1 entries)")
    return out


def plot_aligned_time_domain(
    tx_data: np.ndarray,
    rx_data: np.ndarray,
    *,
    out_dir: Path,
    tx_slice_start: int,
    rx_slice_start: int,
    align_len: int,
    plot_start: int = ALIGN_PLOT_START,
    plot_end: int = ALIGN_PLOT_END,
    show: bool = False,
    tx_label: str = "TX",
    rx_label: str = "RX",
    tone_mode: bool = False,
) -> Path:
    """
    Time-domain compare after coarse align, **before gain compensation**.

    Plots ``[plot_start:plot_end)``:
      1) |TX|/|RX| (RX peak-scaled for overlay only)
      2) peak-normalized magnitude
      3) I (separate)
      4) Q (separate)
    Saves ``pre_gain_time_domain`` and ``align_time_domain`` (same figure).
    """
    import matplotlib.pyplot as plt

    tx = np.asarray(tx_data, dtype=np.complex128).reshape(-1)
    rx = np.asarray(rx_data, dtype=np.complex128).reshape(-1)
    n = min(tx.size, rx.size)
    tx, rx = tx[:n], rx[:n]

    i0 = max(0, int(plot_start))
    i1 = min(n, int(plot_end))
    if i0 >= i1:
        raise ValueError(
            f"align plot window empty: plot_start={plot_start}, "
            f"plot_end={plot_end}, N={n}"
        )
    tx = tx[i0:i1]
    rx = rx[i0:i1]
    t = np.arange(i0, i1)

    tx_abs = np.abs(tx)
    rx_abs = np.abs(rx)
    tx_peak = float(np.max(tx_abs)) if tx.size else 0.0
    rx_peak = float(np.max(rx_abs)) if rx.size else 0.0
    scale = (tx_peak / rx_peak) if rx_peak > 0 else 1.0

    # Phase-align RX for I/Q overlay (visual only; not gain_compensation).
    # LS: tx ≈ a*rx with a = vdot(rx, tx)/vdot(rx, rx); apply a/|a| (not exp(-j∠)).
    a = np.vdot(rx, tx) / (np.vdot(rx, rx) + 1e-30)
    rx_p = rx * (a / np.abs(a) if np.abs(a) > 0 else 1.0)
    rx_p = rx_p * scale

    fig, axes = plt.subplots(4, 1, sharex=True, figsize=(11, 10))
    title = (
        f"Pre-gain time domain  {tx_label} vs {rx_label}"
        f"{'  [TONE]' if tone_mode else ''}  "
        f"samples [{i0}:{i1})  N_win={i1 - i0}  (full N={n})  "
        f"tx_slice={tx_slice_start}  rx_slice={rx_slice_start}  "
        f"align_len={align_len}"
    )
    fig.suptitle(title)

    ax0 = axes[0]
    ax0.plot(t, tx_abs, label=f"|{tx_label}|", linewidth=0.8)
    ax0.plot(
        t,
        rx_abs * scale,
        label=f"|{rx_label}|×{scale:.3g} (peak overlay)",
        linewidth=0.8,
        alpha=0.85,
    )
    ax0.set_ylabel("Amplitude")
    ax0.grid(True, which="both", alpha=0.4)
    ax0.legend(loc="best")
    ax0.set_title("Raw |·| before gain compensation (RX peak-scaled for overlay)")

    ax1 = axes[1]
    tx_n = tx_abs / (tx_peak + 1e-12)
    rx_n = rx_abs / (rx_peak + 1e-12)
    ax1.plot(t, tx_n, label=f"|{tx_label}| / peak", linewidth=0.8)
    ax1.plot(t, rx_n, label=f"|{rx_label}| / peak", linewidth=0.8, alpha=0.85)
    ax1.set_ylabel("Normalized")
    ax1.set_ylim(-0.05, 1.15)
    ax1.grid(True, which="both", alpha=0.4)
    ax1.legend(loc="best")
    ax1.set_title("Peak-normalized (shape / delay check)")

    ax_i = axes[2]
    ax_i.plot(t, np.real(tx), label=f"I {tx_label}", linewidth=0.8)
    ax_i.plot(
        t,
        np.real(rx_p),
        label=f"I {rx_label} (ph+peak)",
        linewidth=0.8,
        alpha=0.85,
    )
    ax_i.set_ylabel("I")
    ax_i.grid(True, which="both", alpha=0.4)
    ax_i.legend(loc="best", fontsize=8)
    ax_i.set_title("I before gain (RX phase-aligned + peak-scale)")

    ax_q = axes[3]
    ax_q.plot(t, np.imag(tx), label=f"Q {tx_label}", linewidth=0.8)
    ax_q.plot(
        t,
        np.imag(rx_p),
        label=f"Q {rx_label} (ph+peak)",
        linewidth=0.8,
        alpha=0.85,
    )
    ax_q.set_ylabel("Q")
    ax_q.grid(True, which="both", alpha=0.4)
    ax_q.legend(loc="best", fontsize=8)
    ax_q.set_title("Q before gain (RX phase-aligned + peak-scale)")
    ax_q.set_xlabel("Sample index (after align)")

    fig.tight_layout()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for stem in ("pre_gain_time_domain", "align_time_domain"):
        fig.savefig(out_dir / f"{stem}.pdf")
        fig.savefig(out_dir / f"{stem}.png", dpi=120)
    if show:
        plt.show()
    else:
        plt.close(fig)
    png = out_dir / "pre_gain_time_domain.png"
    print(
        f"[PLOT] pre-gain time-domain [{i0}:{i1}) {tx_label} vs {rx_label} "
        f"→ {png}"
    )
    return png


def plot_tone_spectrum(
    tx_data: np.ndarray,
    rx_data: np.ndarray,
    *,
    out_dir: Path,
    fs: float = FS_HZ,
    tx_label: str = "TX",
    rx_label: str = "RX",
    show: bool = False,
) -> Path:
    """Overlay |FFT| of TX/RX for CW tone sanity check."""
    import matplotlib.pyplot as plt

    tx = np.asarray(tx_data, dtype=np.complex128).reshape(-1)
    rx = np.asarray(rx_data, dtype=np.complex128).reshape(-1)
    n = min(tx.size, rx.size, 8192)
    w = np.hanning(n)
    f = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / float(fs))) / 1e6
    Tx = np.fft.fftshift(np.fft.fft(tx[:n] * w))
    Rx = np.fft.fftshift(np.fft.fft(rx[:n] * w))
    tx_db = 20 * np.log10(np.abs(Tx) + 1e-15)
    rx_db = 20 * np.log10(np.abs(Rx) + 1e-15)
    rx_db = rx_db - np.max(rx_db) + np.max(tx_db)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(f, tx_db, label=tx_label, linewidth=0.9)
    ax.plot(f, rx_db, label=f"{rx_label} (peak-aligned dB)", linewidth=0.9, alpha=0.85)
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("Magnitude (dB)")
    ax.set_title(f"Tone spectrum  {tx_label} vs {rx_label}  (N={n}, fs={fs/1e6:.3g} MHz)")
    ax.grid(True, alpha=0.4)
    ax.legend(loc="best")
    fig.tight_layout()
    out_dir = Path(out_dir)
    png = out_dir / "tone_spectrum.png"
    fig.savefig(out_dir / "tone_spectrum.pdf")
    fig.savefig(png, dpi=120)
    if show:
        plt.show()
    else:
        plt.close(fig)
    print(f"[PLOT] tone spectrum → {png}")
    return png


def _mat_rx_key(m: dict) -> str:
    """Prefer rx_data (new captures); fall back to pa_data (older mats)."""
    if "rx_data" in m:
        return "rx_data"
    if "pa_data" in m:
        return "pa_data"
    keys = [k for k in m if not k.startswith("__")]
    raise KeyError(f"neither rx_data nor pa_data in mat; keys={keys}")


def load_rx_pa(
    n_tx: int,
    *,
    mat_path: Optional[PathLike] = None,
    txt_path: Optional[PathLike] = None,
    txt_stride: int = RX_TXT_STRIDE,
    csv_rx: Optional[np.ndarray] = None,
    prefer: str = "auto",
    rx_slice_start: Optional[int] = None,
    slice_len: Optional[int] = None,
) -> np.ndarray:
    """
    Load PA/RX complex samples.

    prefer: auto | mat | txt | csv
      auto: mat → txt → csv feedback

    If ``rx_slice_start`` (1-based) and ``slice_len`` are set, apply that
    window on the full capture before truncating to ``n_tx``.
    """
    mat_path = Path(mat_path) if mat_path else RX_MAT
    txt_path = Path(txt_path) if txt_path else RX_TXT
    mode = prefer.lower()

    def _window(iq: np.ndarray) -> np.ndarray:
        z = np.asarray(iq, dtype=np.complex128).reshape(-1)
        if rx_slice_start is not None and slice_len is not None:
            i0 = int(rx_slice_start) - 1
            z = z[i0 : i0 + int(slice_len)]
        return _as_col(z[:n_tx])

    def from_mat() -> np.ndarray:
        from scipy.io import loadmat

        m = loadmat(str(mat_path))
        key = _mat_rx_key(m)
        pa = np.asarray(m[key]).reshape(-1)
        print(f"[RX] mat key={key}")
        return _window(pa)

    def from_txt() -> np.ndarray:
        iq = load_iqxel_txt(txt_path, stride=int(txt_stride)).reshape(-1)
        return _window(iq)

    def from_csv() -> np.ndarray:
        if csv_rx is None:
            raise FileNotFoundError("no CSV feedback provided")
        return _window(np.asarray(csv_rx).reshape(-1))

    order = {
        "auto": ["mat", "txt", "csv"],
        "mat": ["mat"],
        "txt": ["txt"],
        "csv": ["csv"],
    }.get(mode, ["mat", "txt", "csv"])

    errors = []
    for kind in order:
        try:
            if kind == "mat":
                if not mat_path.is_file():
                    raise FileNotFoundError(mat_path)
                pa = from_mat()
                print(f"[RX] loaded mat {mat_path.name}  N={pa.size}")
                return pa
            if kind == "txt":
                if not txt_path.is_file():
                    raise FileNotFoundError(txt_path)
                pa = from_txt()
                print(f"[RX] loaded txt {txt_path.name}  N={pa.size}")
                return pa
            if kind == "csv":
                pa = from_csv()
                print(f"[RX] using CSV feedback  N={pa.size}")
                return pa
        except Exception as e:  # noqa: BLE001 — try next source
            errors.append(f"{kind}: {e}")

    raise RuntimeError(
        "failed to load RX/PA data; tried "
        + ", ".join(order)
        + " | "
        + " ; ".join(errors)
    )


def run_pipeline(
    csv_path: PathLike = INPUT_CSV,
    *,
    rx_prefer: str = "auto",
    mat_path: Optional[PathLike] = None,
    txt_path: Optional[PathLike] = None,
    txt_stride: int = RX_TXT_STRIDE,
    dac_csv_path: Optional[PathLike] = None,
    csv_decimate: int = 2,
    dac_csv_decimate: Optional[int] = None,
    csv_osr: Optional[int] = None,
    dac_csv_osr: Optional[int] = None,
    work_osr: Optional[int] = None,
    output_dir: PathLike = OUTPUT_DIR,
    plot: bool = True,
    show: bool = False,
    niter: int = NITER,
    max_table_value: float = MAX_TABLE_VALUE,
    num_lut: int = NUM_LUT,
    est_delay: int = EST_DELAY,
    order: int = ORDER,
    amp_thresh: float = AMP_THRESH,
    cfo_corr_len: int = CFO_CORR_LEN,
    enable_cfo: bool = True,
    pn_comp: Union[str, bool] = PN_COMP,
    pn_smooth_win: int = PN_SMOOTH_WIN,
    pn_amp_ratio: float = PN_AMP_RATIO,
    tx_slice_start: int = TX_SLICE_START,
    rx_slice_start: int = RX_SLICE_START,
    slice_len: int = SLICE_LEN,
    align_len: int = ALIGN_LEN,
    tx_source: str = "auto",
    lut_map_scale: float = 128.0,
    align_plot_start: int = ALIGN_PLOT_START,
    align_plot_end: int = ALIGN_PLOT_END,
    coarse_align: bool = COARSE_ALIGN,
    coarse_max_lag: int = COARSE_MAX_LAG,
    coarse_search_len: int = COARSE_SEARCH_LEN,
    coarse_local_only: bool = False,
    signal_mode: str = "auto",
    fs_hz: float = FS_HZ,
) -> dict:
    """
    Execute the MATLAB main flow; return dict with LUT and intermediate arrays.

    tx_source: ref | adc | dac | auto
      auto → ref if energy, else dac, else ADC.
    """
    import matplotlib

    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mat_resolved = Path(mat_path) if mat_path else RX_MAT
    txt_resolved = Path(txt_path) if txt_path else RX_TXT

    # Normalize RX prefer: feedback ≡ csv (ILA feedback_i/q)
    prefer = rx_prefer.lower()
    if prefer == "feedback":
        prefer = "csv"

    # If user points --txt at a non-default file under --rx auto, prefer txt over
    # the stock default mat (otherwise auto always picks the existing default mat).
    if prefer == "auto":
        if dac_csv_path and Path(dac_csv_path).is_file():
            prefer = "dac"
            print(f"[RX] auto→dac (custom --dac-csv {Path(dac_csv_path).name})")
        else:
            try:
                txt_custom = txt_resolved.resolve() != Path(RX_TXT).resolve()
            except OSError:
                txt_custom = str(txt_resolved) != str(RX_TXT)
            if txt_custom and txt_resolved.is_file():
                prefer = "txt"
                print(f"[RX] auto→txt (custom --txt {txt_resolved.name})")

    # --- load primary CSV (ILA) ---
    use_osr = csv_osr is not None or dac_csv_osr is not None
    if use_osr:
        # Load full-rate rows, then resample to a common work OSR.
        primary_dec = 1
        dac_dec = 1
        osr_tx = int(csv_osr) if csv_osr is not None else 4
        osr_dac = int(dac_csv_osr) if dac_csv_osr is not None else osr_tx
        work = int(work_osr) if work_osr is not None else int(min(osr_tx, osr_dac))
        print(
            f"[RATE] csv_osr={osr_tx}  dac_csv_osr={osr_dac}  work_osr={work}  "
            f"(load decimate=1 then resample)"
        )
    else:
        primary_dec = int(csv_decimate)
        dac_dec = (
            int(dac_csv_decimate)
            if dac_csv_decimate is not None
            else primary_dec
        )
        osr_tx = osr_dac = work = None

    ref_data, fb_data, adc_data, dac_primary = read_data(
        csv_path, decimate=primary_dec
    )
    print(
        f"[CSV] {Path(csv_path).name}  N={ref_data.size} "
        f"(after decimate={primary_dec})"
    )

    # Optional second CSV for DAC RX (keep primary dac for TX when --tx-source dac)
    dac_data = dac_primary
    dac_from_second = False
    if dac_csv_path is not None and Path(dac_csv_path).is_file():
        _r, _f, _a, dac_from_file = read_data(dac_csv_path, decimate=dac_dec)
        dac_peak_file = float(np.max(np.abs(dac_from_file))) if dac_from_file.size else 0.0
        print(
            f"[CSV] dac-csv {Path(dac_csv_path).name}  "
            f"N={dac_from_file.size} (decimate={dac_dec})  "
            f"dac_peak={dac_peak_file:.3g}"
        )
        if dac_peak_file > 0:
            dac_data = dac_from_file
            dac_from_second = True
        elif prefer == "dac":
            raise RuntimeError(
                f"--rx dac but no dac_i/q energy in {dac_csv_path}"
            )

    if use_osr:
        ref_data = resample_iq_to_osr(ref_data, osr_tx, work)
        fb_data = resample_iq_to_osr(fb_data, osr_tx, work)
        adc_data = resample_iq_to_osr(adc_data, osr_tx, work)
        dac_primary = resample_iq_to_osr(dac_primary, osr_tx, work)
        dac_src_osr = osr_dac if dac_from_second else osr_tx
        dac_data = resample_iq_to_osr(dac_data, dac_src_osr, work)
        print(
            f"[RATE] after resample → N  ref={ref_data.size}  "
            f"dac_tx={dac_primary.size}  dac_rx={dac_data.size}  "
            f"(work_osr={work})"
        )

    ref_peak = float(np.max(np.abs(ref_data))) if ref_data.size else 0.0
    fb_peak = float(np.max(np.abs(fb_data))) if fb_data.size else 0.0
    adc_peak = float(np.max(np.abs(adc_data))) if adc_data.size else 0.0
    dac_tx_peak = float(np.max(np.abs(dac_primary))) if dac_primary.size else 0.0
    dac_peak = float(np.max(np.abs(dac_data))) if dac_data.size else 0.0
    print(
        f"[CSV] peaks  ref={ref_peak:.3g}  feedback={fb_peak:.3g}  "
        f"adc={adc_peak:.3g}  dac_tx={dac_tx_peak:.3g}  dac_rx={dac_peak:.3g}"
    )

    src = tx_source.lower()
    if src == "auto":
        if prefer == "csv" and ref_peak > 0:
            src = "ref"
        elif prefer == "dac" and ref_peak > 0:
            src = "ref"
        elif prefer == "dac" and dac_from_second and dac_tx_peak > 0:
            # e.g. ref_iladata.csv (dac_* cols) vs dac_iladata.csv
            src = "dac"
            print(
                "[TX] auto→primary dac columns "
                f"(ref_peak={ref_peak:.3g}, dac_tx_peak={dac_tx_peak:.3g})"
            )
        elif ref_peak > 0:
            src = "ref"
        elif dac_tx_peak > 0 and prefer != "dac":
            src = "dac"
            print(
                "[TX] auto→dac "
                f"(ref_peak={ref_peak:.3g}, dac_peak={dac_tx_peak:.3g})"
            )
        elif adc_peak > 0:
            src = "adc"
            print(
                "[TX] ref/dac empty; using ADC as TX "
                f"(ref_peak={ref_peak:.3g}, adc_peak={adc_peak:.3g})"
            )
        else:
            raise RuntimeError(
                "TX empty: ref/dac/adc are all zero in CSV; check ILA dump"
            )
    if src == "ref":
        if ref_peak <= 0:
            raise RuntimeError("TX source=ref but ref_i/q are empty in CSV")
        tx_data = ref_data
        tx_label = "ref"
    elif src == "dac":
        # TX always from primary CSV dac_* (not overwritten by --dac-csv)
        if dac_tx_peak <= 0:
            raise RuntimeError(
                "TX source=dac but primary CSV dac_i/q are empty; "
                "use a dac/ref iladata.csv with dac columns"
            )
        tx_data = dac_primary
        stem = Path(csv_path).stem.lower()
        tx_label = "ref" if "ref" in stem else "dac"
    elif src == "adc":
        tx_data = adc_data
        tx_label = "adc"
    else:
        raise ValueError(f"unknown tx_source={tx_source!r}")
    print(f"[TX] source={src}  label={tx_label}  peak={float(np.max(np.abs(tx_data))):.3g}")

    # Detect CW / single-tone (envelope align is useless on flat |TX|)
    mode = (signal_mode or "auto").lower()
    if mode == "auto":
        tone_mode = is_cw_tone(tx_data)
        if tone_mode:
            print(
                f"[MODE] auto→tone  (|TX| CV="
                f"{float(np.std(np.abs(tx_data))/ (np.mean(np.abs(tx_data))+1e-12)):.4g} "
                f"< {TONE_CV_MAX})"
            )
        else:
            print("[MODE] auto→ofdm/packet")
    elif mode == "tone":
        tone_mode = True
        print("[MODE] tone (forced)")
    else:
        tone_mode = False
        print(f"[MODE] {mode}")

    # MATLAB: tx_data = tx_data(313:313+7000,:)
    t0 = int(tx_slice_start) - 1
    tx_data = tx_data[t0 : t0 + int(slice_len), :]
    print(f"[TX] slice {tx_slice_start}:{tx_slice_start}+{slice_len - 1} → N={tx_data.size}")

    if tone_mode:
        f_tx0 = estimate_tone_hz(tx_data, fs_hz)
        print(f"[TONE] TX freq ≈ {f_tx0/1e6:.6g} MHz  (fs={fs_hz/1e6:.3g} MHz)")
        # Gain match needs |tx|<amp_thresh samples; tone peak may be below 800 already.
        tx_pk = float(np.max(np.abs(tx_data)))
        if tx_pk >= float(amp_thresh) - 1e-9:
            amp_thresh = tx_pk * 1.05
            print(
                f"[TONE] raise amp_thresh → {amp_thresh:.4g} "
                f"(tone peak {tx_pk:.4g})"
            )

    # RX: feedback / dac CSV window, or mat/txt with global align
    use_csv_feedback = prefer == "csv"
    use_csv_dac = prefer == "dac"
    if prefer == "auto" and not mat_resolved.is_file():
        use_csv_feedback = not txt_resolved.is_file() and dac_peak <= 0

    def _align_rx_from_full(
        rx_full: np.ndarray,
        *,
        label: str,
        peak_val: float,
    ) -> tuple:
        """Same-timeline CSV RX: optional ±lag envelope align to TX."""
        nonlocal tx_data
        ml = int(coarse_max_lag) if coarse_align else 0
        rx_full = np.asarray(rx_full, dtype=np.complex128).reshape(-1)
        if coarse_align and ml > 0:
            load0 = max(0, t0 - ml)
            load1 = min(rx_full.size, t0 + int(slice_len) + ml)
            rx_long = _as_col(rx_full[load0:load1])
            off = t0 - load0
            from scipy.signal import correlate

            tx_abs = np.abs(tx_data.reshape(-1)).astype(float)
            rx_abs = np.abs(rx_long.reshape(-1)).astype(float)
            n_tx = min(tx_abs.size, int(slice_len))
            ta = tx_abs[:n_tx] - tx_abs[:n_tx].mean()
            c = correlate(rx_abs - rx_abs.mean(), ta, mode="valid")
            i0 = max(0, off - ml)
            i1 = min(c.size, off + ml + 1)
            peak = i0 + int(np.argmax(c[i0:i1]))
            lag_vs_nominal = peak - off
            rx_out = rx_long[peak : peak + n_tx, :]
            tx_data = tx_data[:n_tx, :]
            slice_used = int(tx_slice_start) + lag_vs_nominal
            print(f"[RX] source={label}  peak={peak_val:.3g}  N={rx_out.size}")
            print(
                f"[ALIGN] coarse envelope ({label}): same-window → "
                f"Δ={lag_vs_nominal:+d} samples (search ±{ml})"
            )
            return rx_out, slice_used
        rx_out = _as_col(rx_full[t0 : t0 + int(slice_len)])
        print(
            f"[RX] source={label}, same TX window → N={rx_out.size}  "
            f"peak={peak_val:.3g}"
        )
        return rx_out, int(tx_slice_start)

    if use_csv_feedback:
        if fb_peak <= 0:
            raise RuntimeError(
                "RX source=feedback but CSV feedback_i/q are all zero; "
                "check ILA dump or use --rx txt/mat/dac"
            )
        rx_data, rx_slice_used = _align_rx_from_full(
            fb_data, label="feedback", peak_val=fb_peak
        )
        rx_label = "feedback"
    elif use_csv_dac:
        if dac_peak <= 0:
            raise RuntimeError(
                "RX source=dac but dac_i/q are empty; pass --dac-csv "
                "dac_iladata.csv or a CSV that contains dac columns"
            )
        if src == "dac" and not dac_from_second:
            raise RuntimeError(
                "TX and RX cannot both be dac from the same CSV; "
                "use --csv ref_iladata.csv --tx-source dac "
                "--dac-csv dac_iladata.csv --rx dac"
            )
        # Cross-file / rate-matched dac: global envelope search (like iQxel).
        # Same-CSV dac still uses same-window ±lag.
        if dac_from_second or use_osr:
            rx_full = np.asarray(dac_data, dtype=np.complex128).reshape(-1)
            n_need = int(slice_len)
            print(
                f"[RX] source=dac  peak={dac_peak:.3g}  full N={rx_full.size}"
            )
            if coarse_align:
                start0, score = find_best_rx_start_envelope(
                    tx_data,
                    rx_full,
                    search_len=min(int(coarse_search_len), rx_full.size),
                    template_len=min(5000, tx_data.size),
                )
                if start0 + n_need > rx_full.size:
                    # fall back: clamp start
                    start0 = max(0, rx_full.size - n_need)
                rx_data = _as_col(rx_full[start0 : start0 + n_need])
                rx_slice_used = start0 + 1
                print(
                    f"[ALIGN] global envelope (dac csv): rx_slice → "
                    f"{rx_slice_used} (0-based {start0}), score={score:.4f}"
                )
            else:
                start0 = max(0, int(tx_slice_start) - 1)
                rx_data = _as_col(rx_full[start0 : start0 + n_need])
                rx_slice_used = start0 + 1
                print(
                    f"[RX] dac slice_start={rx_slice_used} "
                    f"(coarse align off)  N={rx_data.size}"
                )
        else:
            rx_data, rx_slice_used = _align_rx_from_full(
                dac_data, label="dac", peak_val=dac_peak
            )
        rx_label = "dac"
    else:
        # iQxel mat/txt: load full capture, auto-find start by envelope match
        rx_label = "iqxel" if prefer in ("txt", "mat", "auto") else prefer
        rx_full = load_rx_full_capture(
            prefer=prefer,
            mat_path=mat_resolved,
            txt_path=txt_resolved,
            txt_stride=txt_stride,
            csv_rx=fb_data,
        )
        print(
            f"[RX] source={rx_label}  loaded full N={rx_full.size}  "
            f"peak={float(np.max(np.abs(rx_full))):.3g}"
        )

        n_need = int(slice_len)
        if coarse_align:
            hint0 = int(rx_slice_start) - 1  # 0-based
            if tone_mode:
                start0, score, f_tx, f_rx = find_best_rx_start_tone(
                    tx_data,
                    rx_full,
                    fs=float(fs_hz),
                    search_len=min(int(coarse_search_len), rx_full.size),
                    template_len=min(2048, tx_data.size),
                )
                mode_s = "tone complex/DC wipe"
                print(
                    f"[TONE] RX freq ≈ {f_rx/1e6:.6g} MHz  "
                    f"(Δf≈{(f_rx - f_tx)/1e3:.4g} kHz vs TX)"
                )
            elif coarse_local_only:
                start0, score = find_best_rx_start_envelope(
                    tx_data,
                    rx_full,
                    hint_start=hint0,
                    local_radius=int(coarse_max_lag),
                    template_len=min(5000, tx_data.size),
                )
                mode_s = f"local±{int(coarse_max_lag)} around {int(rx_slice_start)}"
            else:
                start0, score = find_best_rx_start_envelope(
                    tx_data,
                    rx_full,
                    search_len=int(coarse_search_len),
                    template_len=min(5000, tx_data.size),
                )
                mode_s = f"global search_len={int(coarse_search_len)}"
            if start0 + n_need > rx_full.size:
                raise RuntimeError(
                    f"auto-align start={start0} + slice_len={n_need} exceeds "
                    f"RX length {rx_full.size}"
                )
            rx_data = _as_col(rx_full[start0 : start0 + n_need])
            rx_slice_used = start0 + 1  # 1-based for logs/plots
            print(
                f"[ALIGN] auto ({mode_s}): rx_slice → {rx_slice_used} "
                f"(0-based {start0}), score={score:.4f}  "
                f"(hint was {int(rx_slice_start)})"
            )
        else:
            start0 = int(rx_slice_start) - 1
            rx_data = _as_col(rx_full[start0 : start0 + n_need])
            rx_slice_used = int(rx_slice_start)
            print(
                f"[RX] slice_start={rx_slice_used} (coarse align off)  "
                f"N={rx_data.size}"
            )
    n = min(tx_data.size, rx_data.size, int(align_len))
    tx_data = tx_data[:n, :]
    rx_data = rx_data[:n, :]
    # Final integer refine on equal-length streams (catches residual few samples)
    # Skip for CW: flat envelope + CFO beat makes |corr| lag unreliable (hits ±max).
    if coarse_align and not tone_mode:
        lag2 = estimate_envelope_delay(
            tx_data, rx_data, max_lag=min(64, n // 4)
        )
        if lag2 != 0:
            tx_data, rx_data, n2 = apply_integer_delay(tx_data, rx_data, lag2)
            n = min(n2, int(align_len))
            tx_data = tx_data[:n, :]
            rx_data = rx_data[:n, :]
            print(f"[ALIGN] residual integer lag={lag2:+d} → N={n}")
    elif tone_mode and coarse_align:
        print("[ALIGN] tone: skip residual integer lag (use CFO / frac delay)")

    print(f"[ALIGN] 1:{align_len} → N={tx_data.size}  ({tx_label} vs {rx_label})")

    # Coarse-align check (before gain/CFO/frac) — always saved for slice tuning
    plot_aligned_time_domain(
        tx_data,
        rx_data,
        out_dir=out_dir,
        tx_slice_start=int(tx_slice_start),
        rx_slice_start=int(rx_slice_used),
        align_len=int(align_len),
        plot_start=int(align_plot_start),
        plot_end=int(align_plot_end),
        show=show,
        tx_label=tx_label,
        rx_label=rx_label,
        tone_mode=tone_mode,
    )
    if tone_mode:
        plot_tone_spectrum(
            tx_data,
            rx_data,
            out_dir=out_dir,
            fs=float(fs_hz),
            tx_label=tx_label,
            rx_label=rx_label,
            show=show,
        )

    # --- gain ---
    tx_gain, rx_gain = gain_compensation(tx_data, rx_data, amp_thresh=amp_thresh)

    rx_after_frac = rx_gain
    for it in range(int(niter)):
        print(f"[ITER] {it + 1}/{niter}")
        if enable_cfo:
            # Always save CFO phase plots (before/after) for diagnosis
            pa_cfo = frequency_offset_estimation(
                tx_gain,
                rx_gain,
                corr_len=cfo_corr_len,
                plot=True,
                save_dir=out_dir,
                tag=f"cfo_iter{it + 1}",
                show=show,
            )
        else:
            pa_cfo = rx_gain
            print("[CFO] skipped (--no-cfo)")

        # iQxel: strip slow common phase noise before DC / frac / LUT
        pn_mode = pn_comp
        if isinstance(pn_mode, str):
            pn_mode_l = pn_mode.strip().lower()
            if pn_mode_l in ("auto", ""):
                do_pn = rx_label in ("iqxel", "txt", "mat")
            elif pn_mode_l in ("1", "true", "yes", "on"):
                do_pn = True
            elif pn_mode_l in ("0", "false", "no", "off"):
                do_pn = False
            else:
                raise ValueError(f"unknown pn_comp={pn_comp!r} (use auto|on|off)")
        else:
            do_pn = bool(pn_mode)

        if do_pn:
            pa_pn, _pn = phase_noise_compensation(
                tx_gain,
                pa_cfo,
                smooth_win=int(pn_smooth_win),
                amp_ratio=float(pn_amp_ratio),
                plot=True,
                save_dir=out_dir,
                tag=f"pn_iter{it + 1}",
                show=show,
            )
        else:
            pa_pn = pa_cfo
            print("[PN] skipped")

        # DC: raw sliced TX + PN/CFO-compensated PA (MATLAB quirk on TX)
        tx_dc, rx_dc = dc_compensation(tx_data, pa_pn)

        # Fractional delay
        rx_after_frac = fractional_delay_estimation(tx_dc, rx_dc, plot=plot)
        if plot and not show:
            for i, num in enumerate(plt.get_fignums()[-2:], 1):
                plt.figure(num).savefig(out_dir / f"frac_delay_iter{it + 1}_{i}.pdf")
                plt.close(num)

        rx_gain = rx_after_frac

    # DPD trim (1000:end) 1-based
    t_dpd = DPD_TRIM_START - 1
    tx_dpd = tx_gain[t_dpd:, :]
    rx_dpd = rx_after_frac[t_dpd:, :]
    print(f"[DPD] trim 1000:end → N={tx_dpd.size}")

    table_x, table_y = static_dpd_memory(
        max_table_value,
        tx_dpd,
        rx_dpd,
        num_lut=num_lut,
        est_delay=est_delay,
        order=order,
    )

    # Save LUT
    lut_path = out_dir / "lut_table.npz"
    np.savez(lut_path, table_x=table_x, table_y=table_y)
    np.savetxt(out_dir / "lut_real.txt", np.real(table_y), fmt="%.10e")
    np.savetxt(out_dir / "lut_imag.txt", np.imag(table_y), fmt="%.10e")
    np.savetxt(out_dir / "lut_x.txt", table_x, fmt="%.10e")
    print(f"[LUT] saved {lut_path}")

    lut_map_path = write_lut_data_map(
        table_y,
        out_dir / "lut_data_map.py",
        scale=float(lut_map_scale),
    )

    amamplot(
        tx_dpd,
        rx_dpd,
        table_x,
        table_y,
        "PA-Rx",
        save_dir=out_dir,
        show=show,
    )
    print(f"[PLOT] AM-AM/AM-PM → {out_dir}")

    return {
        "table_x": table_x,
        "table_y": table_y,
        "tx_dpd": tx_dpd,
        "rx_dpd": rx_dpd,
        "output_dir": out_dir,
        "lut_map_path": lut_map_path,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Xian static DPD main (port of xian_static_DPD_main1.m)"
    )
    p.add_argument(
        "--csv",
        default=str(INPUT_CSV),
        help="Primary ILA CSV (ref/feedback/adc and/or dac columns)",
    )
    p.add_argument(
        "--dac-csv",
        default=None,
        help="Optional second CSV with dac_i/q (for --rx dac vs --tx-source ref)",
    )
    p.add_argument(
        "--csv-decimate",
        type=int,
        default=2,
        help="ILA row stride for --csv (MATLAB 1:2:end → 2). Ignored if --csv-osr set",
    )
    p.add_argument(
        "--dac-csv-decimate",
        type=int,
        default=None,
        help="ILA row stride for --dac-csv (default: same as --csv-decimate)",
    )
    p.add_argument(
        "--csv-osr",
        type=int,
        default=None,
        help="Oversampling label of --csv (e.g. 4 for ref 4x). Enables rate match",
    )
    p.add_argument(
        "--dac-csv-osr",
        type=int,
        default=None,
        help="Oversampling label of --dac-csv (e.g. 2 for pkt_out). With --csv-osr",
    )
    p.add_argument(
        "--work-osr",
        type=int,
        default=None,
        help="Common OSR after resample (default: min(csv-osr, dac-csv-osr))",
    )
    p.add_argument(
        "--rx",
        choices=("auto", "mat", "txt", "csv", "feedback", "dac"),
        default="auto",
        help=(
            "RX: mat/txt (iqxel), feedback/csv (ILA feedback), "
            "or dac (dac_i/q from --dac-csv or --csv)"
        ),
    )
    p.add_argument(
        "--mat",
        default=str(RX_MAT),
        help="path to *.mat with rx_data (or pa_data)",
    )
    p.add_argument("--txt", default=str(RX_TXT), help="path to I,Q txt (LitePoint ok)")
    p.add_argument(
        "--txt-stride",
        type=int,
        default=RX_TXT_STRIDE,
        help="decimate iQxel txt (0=auto from SamplingRate; 2 for 160Msps→80M)",
    )
    p.add_argument(
        "--tx-source",
        choices=("auto", "ref", "adc", "dac"),
        default="auto",
        help=(
            "TX from CSV: ref_i/q, dac_i/q, adc_i/q, or auto "
            "(ref→dac→adc by energy; dac_iladata.csv uses dac)"
        ),
    )
    p.add_argument(
        "--tx-slice-start",
        type=int,
        default=TX_SLICE_START,
        help="1-based TX start index after 2:1 (MATLAB tx(start:start+slice_len-1))",
    )
    p.add_argument(
        "--rx-slice-start",
        type=int,
        default=RX_SLICE_START,
        help="1-based RX start on mat/txt capture",
    )
    p.add_argument(
        "--slice-len",
        type=int,
        default=SLICE_LEN,
        help="samples taken from each stream before align_len trim",
    )
    p.add_argument(
        "--align-len",
        type=int,
        default=ALIGN_LEN,
        help="keep first N samples after TX/RX slice (MATLAB 1:5500)",
    )
    p.add_argument(
        "--align-plot-start",
        type=int,
        default=ALIGN_PLOT_START,
        help="align_time_domain plot start index (0-based, inclusive)",
    )
    p.add_argument(
        "--align-plot-end",
        type=int,
        default=ALIGN_PLOT_END,
        help="align_time_domain plot end index (0-based, exclusive)",
    )
    p.add_argument(
        "--no-coarse-align",
        action="store_true",
        help="disable abs-envelope auto align of RX to TX",
    )
    p.add_argument(
        "--coarse-max-lag",
        type=int,
        default=COARSE_MAX_LAG,
        help="±samples for feedback align / --coarse-local-only (default 512)",
    )
    p.add_argument(
        "--coarse-search-len",
        type=int,
        default=COARSE_SEARCH_LEN,
        help="iQxel global envelope search length (default 500000)",
    )
    p.add_argument(
        "--coarse-local-only",
        action="store_true",
        help="only search ±coarse-max-lag around --rx-slice-start (no global)",
    )
    p.add_argument(
        "--signal-mode",
        choices=("auto", "ofdm", "tone"),
        default="auto",
        help="auto: detect CW by |TX| CV; tone: complex/DC align + spectrum",
    )
    p.add_argument(
        "--fs",
        type=float,
        default=FS_HZ,
        help="sample rate (Hz) after CSV decimate / txt stride (default 80e6)",
    )
    p.add_argument("-o", "--output-dir", default=str(OUTPUT_DIR))
    p.add_argument("--no-plot", action="store_true")
    p.add_argument("--show", action="store_true", help="interactive matplotlib windows")
    p.add_argument("--niter", type=int, default=NITER)
    p.add_argument("--order", type=int, default=ORDER)
    p.add_argument("--num-lut", type=int, default=NUM_LUT)
    p.add_argument("--est-delay", type=int, default=EST_DELAY)
    p.add_argument("--max-table", type=float, default=MAX_TABLE_VALUE)
    p.add_argument("--amp-thresh", type=float, default=AMP_THRESH)
    p.add_argument("--cfo-corr-len", type=int, default=CFO_CORR_LEN)
    p.add_argument(
        "--lut-map-scale",
        type=float,
        default=128.0,
        help="scale for lut_data_map.py: i,q = round(LUT * scale) (default 128)",
    )
    p.add_argument(
        "--no-cfo",
        action="store_true",
        help="skip CFO (as in draft .m~ with CFO commented out)",
    )
    p.add_argument(
        "--pn-comp",
        default=str(PN_COMP),
        choices=["auto", "on", "off"],
        help="phase-noise compensation before LUT: auto=iQxel only (default), on, off",
    )
    p.add_argument(
        "--pn-smooth-win",
        type=int,
        default=PN_SMOOTH_WIN,
        help="PN moving-average window in samples (default 257 @ ~80 MHz)",
    )
    p.add_argument(
        "--pn-amp-ratio",
        type=float,
        default=PN_AMP_RATIO,
        help="high-|TX| fraction of peak used as PN anchors (default 0.25)",
    )
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    run_pipeline(
        args.csv,
        rx_prefer=args.rx,
        mat_path=args.mat,
        txt_path=args.txt,
        txt_stride=args.txt_stride,
        dac_csv_path=args.dac_csv,
        csv_decimate=args.csv_decimate,
        dac_csv_decimate=args.dac_csv_decimate,
        csv_osr=args.csv_osr,
        dac_csv_osr=args.dac_csv_osr,
        work_osr=args.work_osr,
        output_dir=args.output_dir,
        plot=not args.no_plot,
        show=args.show,
        niter=args.niter,
        max_table_value=args.max_table,
        num_lut=args.num_lut,
        est_delay=args.est_delay,
        order=args.order,
        amp_thresh=args.amp_thresh,
        cfo_corr_len=args.cfo_corr_len,
        enable_cfo=not args.no_cfo,
        pn_comp=args.pn_comp,
        pn_smooth_win=args.pn_smooth_win,
        pn_amp_ratio=args.pn_amp_ratio,
        tx_source=args.tx_source,
        tx_slice_start=args.tx_slice_start,
        rx_slice_start=args.rx_slice_start,
        slice_len=args.slice_len,
        align_len=args.align_len,
        lut_map_scale=args.lut_map_scale,
        align_plot_start=args.align_plot_start,
        align_plot_end=args.align_plot_end,
        coarse_align=not args.no_coarse_align,
        coarse_max_lag=args.coarse_max_lag,
        coarse_search_len=args.coarse_search_len,
        coarse_local_only=args.coarse_local_only,
        signal_mode=args.signal_mode,
        fs_hz=args.fs,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
