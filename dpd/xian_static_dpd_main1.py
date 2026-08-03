#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xian static DPD training pipeline — Python port of xian_static_DPD_main1.m.

Pipeline (1:1 with MATLAB):
  read_data(CSV) → trim TX → load PA/RX (mat/txt/csv) → slice
  → gain_compensation → [CFO → DC → fractional delay]
  → static_dpd_memory → amamplot

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
# Config (mirrors MATLAB script defaults)
# =============================================================================
DATA_DIR = _THIS_DIR
INPUT_CSV = DATA_DIR / "gain168_test_data_3.csv"
# MATLAB loads gain168_iqxel_short_data.mat (pa_data). If missing, try txt / CSV feedback.
RX_MAT = DATA_DIR / "gain168_iqxel_short_data.mat"
RX_TXT = DATA_DIR / "gain168_iqxel_data.txt"
RX_TXT_STRIDE = 6  # MATLAB comment: pa_data(1:6:16384*6,:)

TX_TRIM_START = 89  # MATLAB tx_data(89:end) — 1-based
SLICE_START = 231  # MATLAB 231:7000
SLICE_END = 7000  # inclusive in MATLAB → Python end exclusive = 7000
DPD_TRIM_START = 1000  # MATLAB (1000:end) 1-based → Python 999:

MAX_TABLE_VALUE = 1023
NUM_LUT = 1
EST_DELAY = 0
ORDER = 3
NITER = 1

OUTPUT_DIR = DATA_DIR / "output" / "xian_static_dpd"


def _as_col(z: np.ndarray) -> np.ndarray:
    return np.asarray(z, dtype=np.complex128).reshape(-1, 1)


def load_rx_pa(
    n_tx: int,
    *,
    mat_path: Optional[PathLike] = None,
    txt_path: Optional[PathLike] = None,
    txt_stride: int = RX_TXT_STRIDE,
    csv_rx: Optional[np.ndarray] = None,
    prefer: str = "auto",
) -> np.ndarray:
    """
    Load PA/RX complex samples aligned to TX length.

    prefer: auto | mat | txt | csv
      auto: mat → txt → csv feedback
    """
    mat_path = Path(mat_path) if mat_path else RX_MAT
    txt_path = Path(txt_path) if txt_path else RX_TXT
    mode = prefer.lower()

    def from_mat() -> np.ndarray:
        from scipy.io import loadmat

        m = loadmat(str(mat_path))
        if "pa_data" not in m:
            keys = [k for k in m if not k.startswith("__")]
            raise KeyError(f"pa_data not in {mat_path}; keys={keys}")
        pa = np.asarray(m["pa_data"]).reshape(-1)
        return _as_col(pa[:n_tx])

    def from_txt() -> np.ndarray:
        # Two columns I,Q; optional stride (MATLAB 1:6:...)
        data = np.loadtxt(str(txt_path), delimiter=",")
        if data.ndim == 1:
            raise ValueError(f"unexpected 1-D data in {txt_path}")
        iq = data[:, 0] + 1j * data[:, 1]
        if txt_stride > 1:
            iq = iq[::txt_stride]
        return _as_col(iq[:n_tx])

    def from_csv() -> np.ndarray:
        if csv_rx is None:
            raise FileNotFoundError("no CSV feedback provided")
        return _as_col(np.asarray(csv_rx).reshape(-1)[:n_tx])

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

    # MATLAB: tx_data = tx_data(89:end,:)
    tx_data = tx_data[TX_TRIM_START - 1 :, :]

    # MATLAB: replace rx with iQxel / PA capture
    rx_data = load_rx_pa(
        tx_data.size,
        mat_path=mat_path,
        txt_path=txt_path,
        txt_stride=txt_stride,
        csv_rx=rx_csv,
        prefer=rx_prefer,
    )

    # Align lengths after load
    n = min(tx_data.size, rx_data.size)
    tx_data = tx_data[:n, :]
    rx_data = rx_data[:n, :]

    # MATLAB: tx/rx = (231:7000,:)  — 1-based inclusive end 7000
    i0 = SLICE_START - 1
    i1 = SLICE_END  # Python exclusive; MATLAB inclusive 7000 → slice to index 7000
    tx_data = tx_data[i0:i1, :]
    rx_data = rx_data[i0:i1, :]
    print(f"[SLICE] 231:7000 → N={tx_data.size}")

    # --- gain ---
    tx_gain, rx_gain = gain_compensation(tx_data, rx_data)

    rx_after_frac = rx_gain
    for it in range(int(niter)):
        print(f"[ITER] {it + 1}/{niter}")
        # CFO on gain-matched pair
        pa_cfo = frequency_offset_estimation(tx_gain, rx_gain, plot=plot)
        if plot and not show:
            for i, num in enumerate(plt.get_fignums()[-2:], 1):
                plt.figure(num).savefig(out_dir / f"cfo_iter{it + 1}_{i}.pdf")
                plt.close(num)

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
    t0 = DPD_TRIM_START - 1
    tx_dpd = tx_gain[t0:, :]
    rx_dpd = rx_after_frac[t0:, :]
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
        help="PA/RX source: mat (iqxel short), txt (stride), or CSV feedback",
    )
    p.add_argument("--mat", default=str(RX_MAT), help="path to *.mat with pa_data")
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
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
