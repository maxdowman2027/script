#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xian static DPD training pipeline — Python port of xian_static_DPD_main1.m.

Aligned with ``dpd/20260804_3_data/xian_static_DPD_main1.m``:

  read_data(CSV) → TX (ref or adc) → RX (iqxel mat/txt, or CSV feedback)
  → slice/align → gain_compensation → [CFO → DC → fractional delay]
  → trim → static_dpd_memory → lut_data_map / amamplot

ILA on-chip compare (ref vs feedback_i/q)::

  python dpd/xian_static_dpd_main1.py --csv ... --rx feedback --tx-source ref

iQxel instrument RX::

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
from read_data import load_iqxel_txt, read_data  # noqa: E402
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

DPD_TRIM_START = 1000  # MATLAB (1000:end) 1-based → Python 999:
AMP_THRESH = 800.0
CFO_CORR_LEN = 5000

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
) -> Path:
    """
    Time-domain |TX| / |RX| after coarse slice+align, for tuning slice params.

    Plots only ``[plot_start:plot_end)`` (0-based sample indices after align).
    Top: absolute magnitude (RX scaled to TX peak for overlay).
    Bottom: each peak-normalized to 1 (peaks from the plot window).
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

    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(11, 6.5))
    title = (
        f"Aligned time domain  {tx_label} vs {rx_label}  "
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
        label=f"|{rx_label}|×{scale:.3g} (→{tx_label} peak)",
        linewidth=0.8,
        alpha=0.85,
    )
    ax0.set_ylabel("Amplitude")
    ax0.grid(True, which="both", alpha=0.4)
    ax0.legend(loc="best")
    ax0.set_title(f"Raw |·| ({rx_label} gain-matched to {tx_label} peak for overlay)")

    ax1 = axes[1]
    tx_n = tx_abs / (tx_peak + 1e-12)
    rx_n = rx_abs / (rx_peak + 1e-12)
    ax1.plot(t, tx_n, label=f"|{tx_label}| / peak", linewidth=0.8)
    ax1.plot(t, rx_n, label=f"|{rx_label}| / peak", linewidth=0.8, alpha=0.85)
    ax1.set_xlabel("Sample index (after align)")
    ax1.set_ylabel("Normalized")
    ax1.set_ylim(-0.05, 1.15)
    ax1.grid(True, which="both", alpha=0.4)
    ax1.legend(loc="best")
    ax1.set_title("Peak-normalized (shape / delay check)")

    fig.tight_layout()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = out_dir / "align_time_domain.pdf"
    png = out_dir / "align_time_domain.png"
    fig.savefig(pdf)
    fig.savefig(png, dpi=120)
    if show:
        plt.show()
    else:
        plt.close(fig)
    print(f"[PLOT] align time-domain [{i0}:{i1}) {tx_label} vs {rx_label} → {png}")
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
) -> dict:
    """
    Execute the MATLAB main flow; return dict with LUT and intermediate arrays.

    tx_source: ref | adc | auto
      auto → use ref if |ref| has energy, else ADC (common when ILA ref columns are 0).
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
        try:
            txt_custom = txt_resolved.resolve() != Path(RX_TXT).resolve()
        except OSError:
            txt_custom = str(txt_resolved) != str(RX_TXT)
        if txt_custom and txt_resolved.is_file():
            prefer = "txt"
            print(f"[RX] auto→txt (custom --txt {txt_resolved.name})")

    # --- load CSV (ILA) ---
    ref_data, fb_data, adc_data = read_data(csv_path)
    print(f"[CSV] {Path(csv_path).name}  N={ref_data.size} (after 2:1)")

    ref_peak = float(np.max(np.abs(ref_data))) if ref_data.size else 0.0
    fb_peak = float(np.max(np.abs(fb_data))) if fb_data.size else 0.0
    adc_peak = float(np.max(np.abs(adc_data))) if adc_data.size else 0.0
    print(
        f"[CSV] peaks  ref={ref_peak:.3g}  feedback={fb_peak:.3g}  adc={adc_peak:.3g}"
    )

    src = tx_source.lower()
    if src == "auto":
        if prefer == "csv" and ref_peak > 0:
            # ILA self-compare: default TX=ref when using feedback as RX
            src = "ref"
        elif ref_peak > 0:
            src = "ref"
        elif adc_peak > 0:
            src = "adc"
            print(
                "[TX] ref columns are empty; using ADC as TX "
                f"(ref_peak={ref_peak:.3g}, adc_peak={adc_peak:.3g})"
            )
        else:
            raise RuntimeError(
                "TX empty: both ref and adc are zero in CSV; check ILA dump"
            )
    if src == "ref":
        tx_data = ref_data
        tx_label = "ref"
    elif src == "adc":
        tx_data = adc_data
        tx_label = "adc"
    else:
        raise ValueError(f"unknown tx_source={tx_source!r}")
    print(f"[TX] source={src}  peak={float(np.max(np.abs(tx_data))):.3g}")

    # MATLAB: tx_data = tx_data(313:313+7000,:)
    t0 = int(tx_slice_start) - 1
    tx_data = tx_data[t0 : t0 + int(slice_len), :]
    print(f"[TX] slice {tx_slice_start}:{tx_slice_start}+{slice_len - 1} → N={tx_data.size}")

    # RX: CSV feedback uses the same TX window; mat/txt use rx_slice_start
    use_csv_feedback = prefer == "csv"
    if prefer == "auto" and not mat_resolved.is_file():
        use_csv_feedback = not txt_resolved.is_file()

    if use_csv_feedback:
        if fb_peak <= 0:
            raise RuntimeError(
                "RX source=feedback but CSV feedback_i/q are all zero; "
                "check ILA dump or use --rx txt/mat"
            )
        rx_label = "feedback"
        ml = int(coarse_max_lag) if coarse_align else 0
        if coarse_align and ml > 0:
            # Load feedback with margin so we can shift vs TX (same CSV timeline)
            fb_full = np.asarray(fb_data, dtype=np.complex128).reshape(-1)
            load0 = max(0, t0 - ml)
            load1 = min(fb_full.size, t0 + int(slice_len) + ml)
            rx_long = _as_col(fb_full[load0:load1])
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
            rx_data = rx_long[peak : peak + n_tx, :]
            # Keep TX length matched
            tx_data = tx_data[:n_tx, :]
            rx_slice_used = int(tx_slice_start) + lag_vs_nominal
            print(
                f"[RX] source=feedback  peak={fb_peak:.3g}  "
                f"N={rx_data.size}"
            )
            print(
                f"[ALIGN] coarse envelope (feedback): same-window → "
                f"Δ={lag_vs_nominal:+d} samples (search ±{ml})"
            )
        else:
            rx_data = _as_col(np.asarray(fb_data).reshape(-1)[t0 : t0 + int(slice_len)])
            rx_slice_used = int(tx_slice_start)
            print(
                f"[RX] source=feedback (CSV feedback_i/q), "
                f"same TX window → N={rx_data.size}  peak={fb_peak:.3g}"
            )
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
            if coarse_local_only:
                start0, score = find_best_rx_start_envelope(
                    tx_data,
                    rx_full,
                    hint_start=hint0,
                    local_radius=int(coarse_max_lag),
                    template_len=min(5000, tx_data.size),
                )
                mode = f"local±{int(coarse_max_lag)} around {int(rx_slice_start)}"
            else:
                start0, score = find_best_rx_start_envelope(
                    tx_data,
                    rx_full,
                    search_len=int(coarse_search_len),
                    template_len=min(5000, tx_data.size),
                )
                mode = f"global search_len={int(coarse_search_len)}"
            if start0 + n_need > rx_full.size:
                raise RuntimeError(
                    f"auto-align start={start0} + slice_len={n_need} exceeds "
                    f"RX length {rx_full.size}"
                )
            rx_data = _as_col(rx_full[start0 : start0 + n_need])
            rx_slice_used = start0 + 1  # 1-based for logs/plots
            print(
                f"[ALIGN] auto envelope ({mode}): rx_slice → {rx_slice_used} "
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
    if coarse_align:
        lag2 = estimate_envelope_delay(tx_data, rx_data, max_lag=min(64, n // 4))
        if lag2 != 0:
            tx_data, rx_data, n2 = apply_integer_delay(tx_data, rx_data, lag2)
            n = min(n2, int(align_len))
            tx_data = tx_data[:n, :]
            rx_data = rx_data[:n, :]
            print(f"[ALIGN] residual integer lag={lag2:+d} → N={n}")

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

        # DC: raw sliced TX + CFO-compensated PA (MATLAB quirk)
        tx_dc, rx_dc = dc_compensation(tx_data, pa_cfo)

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
        help="ILA CSV with ref/feedback/adc columns",
    )
    p.add_argument(
        "--rx",
        choices=("auto", "mat", "txt", "csv", "feedback"),
        default="auto",
        help=(
            "PA/RX source: mat/txt (iqxel), or csv/feedback "
            "(ILA CSV feedback_i/q vs ref for on-chip compare)"
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
        choices=("auto", "ref", "adc"),
        default="auto",
        help=(
            "TX from CSV: ref_i/q, adc_i/q, or auto "
            "(with --rx feedback/csv prefers ref when nonzero)"
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
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    run_pipeline(
        args.csv,
        rx_prefer=args.rx,
        mat_path=args.mat,
        txt_path=args.txt,
        txt_stride=args.txt_stride,
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
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
