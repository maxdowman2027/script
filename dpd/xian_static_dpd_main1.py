#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xian static DPD training pipeline — Python port of xian_static_DPD_main1.m.

Aligned with ``dpd/20260804_3_data/xian_static_DPD_main1.m``:

  read_data(CSV) → TX slice 313:313+7000 → load mat ``rx_data`` 1596:1596+7000
  → both 1:5500 → gain_compensation(amp<800)
  → [CFO(corr_len=5000) → DC → fractional delay]
  → trim 1000:end → static_dpd_memory(numLUT=1, estDelay=0, order=3)
  → amamplot

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
from read_data import read_data  # noqa: E402
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
RX_TXT_STRIDE = 1  # short txt already at sample rate; set 6 for long captures

# MATLAB: tx_data(313:313+7000,:), rx_data(1596:1596+7000,:), then both (1:5500,:)
TX_SLICE_START = 313  # 1-based
RX_SLICE_START = 1596  # 1-based
SLICE_LEN = 7001  # inclusive end = start + 7000 → length 7001
ALIGN_LEN = 5500

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
        data = np.loadtxt(str(txt_path), delimiter=",")
        if data.ndim == 1:
            raise ValueError(f"unexpected 1-D data in {txt_path}")
        iq = data[:, 0] + 1j * data[:, 1]
        if txt_stride > 1:
            iq = iq[::txt_stride]
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
                print(
                    f"[RX] loaded txt {txt_path.name} stride={txt_stride}  N={pa.size}"
                )
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
) -> dict:
    """
    Execute the MATLAB main flow; return dict with LUT and intermediate arrays.
    """
    import matplotlib

    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- load CSV (ILA) ---
    tx_data, rx_csv, adc_data = read_data(csv_path)
    print(f"[CSV] {Path(csv_path).name}  tx={tx_data.size} (after 2:1)")
    _ = adc_data  # available for debug; MATLAB importfile20 skips adc

    # MATLAB: tx_data = tx_data(313:313+7000,:)
    t0 = int(tx_slice_start) - 1
    tx_data = tx_data[t0 : t0 + int(slice_len), :]
    print(f"[TX] slice {tx_slice_start}:{tx_slice_start}+{slice_len - 1} → N={tx_data.size}")

    # MATLAB: rx_data = load(...).rx_data; rx_data(1596:1596+7000,:)
    # CSV feedback fallback uses the same TX window on ILA feedback.
    use_csv_window = rx_prefer == "csv"
    mat_resolved = Path(mat_path) if mat_path else RX_MAT
    if rx_prefer == "auto" and not mat_resolved.is_file():
        txt_resolved = Path(txt_path) if txt_path else RX_TXT
        use_csv_window = not txt_resolved.is_file()

    if use_csv_window:
        rx_data = _as_col(np.asarray(rx_csv).reshape(-1)[t0 : t0 + int(slice_len)])
        print(f"[RX] CSV feedback same TX window → N={rx_data.size}")
    else:
        rx_data = load_rx_pa(
            int(slice_len),
            mat_path=mat_path,
            txt_path=txt_path,
            txt_stride=txt_stride,
            csv_rx=rx_csv,
            prefer=rx_prefer,
            rx_slice_start=int(rx_slice_start),
            slice_len=int(slice_len),
        )

    n = min(tx_data.size, rx_data.size, int(align_len))
    tx_data = tx_data[:n, :]
    rx_data = rx_data[:n, :]
    print(f"[ALIGN] 1:{align_len} → N={tx_data.size}")
    # --- gain ---
    tx_gain, rx_gain = gain_compensation(tx_data, rx_data, amp_thresh=amp_thresh)

    rx_after_frac = rx_gain
    for it in range(int(niter)):
        print(f"[ITER] {it + 1}/{niter}")
        if enable_cfo:
            pa_cfo = frequency_offset_estimation(
                tx_gain, rx_gain, corr_len=cfo_corr_len, plot=plot
            )
            if plot and not show:
                for i, num in enumerate(plt.get_fignums()[-2:], 1):
                    plt.figure(num).savefig(out_dir / f"cfo_iter{it + 1}_{i}.pdf")
                    plt.close(num)
        else:
            pa_cfo = rx_gain

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
        choices=("auto", "mat", "txt", "csv"),
        default="auto",
        help="PA/RX source: mat (iqxel short), txt, or CSV feedback",
    )
    p.add_argument(
        "--mat",
        default=str(RX_MAT),
        help="path to *.mat with rx_data (or pa_data)",
    )
    p.add_argument("--txt", default=str(RX_TXT), help="path to I,Q txt")
    p.add_argument("--txt-stride", type=int, default=RX_TXT_STRIDE)
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
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
