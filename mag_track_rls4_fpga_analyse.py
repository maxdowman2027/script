#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RLS4.0 FPGA mag-track regression CSV -> EVM vs tx_pwr (PDF), analogous to txmagtrk_analyse.py for E22.

Input: mag_track_test_res_*.csv with chan, dly, tx_pwr, tx_mag_track_on, amplitude, evm, ...

Panel rule: one PDF page per (chan, dly, ...) mag tuple where tx_mag_track_on=1 exists.
tx_mag_track_on=0 baselines: same chan only (pool all dly and mag params per tx_pwr); FPGA-on lines use strict tuple.

Uses analyze_mag_track_test_res.load_mag_track_csv for delimiter/encoding/column normalization.
"""

from __future__ import annotations

import argparse
import gc
import os
import sys
import traceback
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

from analyze_mag_track_test_res import load_mag_track_csv, natural_sort_key

TRACK_COL = "tx_mag_track_on"  # 0 = FPGA magtrack off; 1 = on
AMP_COL = "amplitude"  # 1 = magtrack on (Instruments)

# X-axis: swept transmit power (dBm)
DEFAULT_X_COL = "tx_pwr"

# Panel grouping: chan separates figures; dly fixes delay for comparison on one chart;
# remaining columns match other mag-track tunables (same tuple => compare four flag combos vs tx_pwr).
DEFAULT_GROUP_COLS: Tuple[str, ...] = (
    "chan",
    "dly",
    "start_point",
    "win_len",
    "chn_len",
    "chn_ofst",
    "start_mode",
)

STYLE_MAP = {
    (0, 0): {
        "linestyle": "-",
        "marker": "o",
        "linewidth": 2,
        "alpha": 0.9,
        "markerfacecolor": "none",
        "markeredgewidth": 2,
        "color": "#2c7bb6",
        "label_suffix": "magtrack off (FPGA tx_mag_track_on=0, instr amp=0)",
    },
    (0, 1): {
        "linestyle": "--",
        "marker": "^",
        "linewidth": 2,
        "alpha": 0.9,
        "markerfacecolor": "none",
        "markeredgewidth": 2,
        "color": "#d7191c",
        "label_suffix": "magtrack on (Instruments) (FPGA off, amplitude=1)",
    },
    (1, 0): {
        "linestyle": "-",
        "marker": "s",
        "linewidth": 2,
        "alpha": 0.9,
        "markerfacecolor": "none",
        "markeredgewidth": 2,
        "color": "#1a9641",
        "label_suffix": "FPGA magtrack on (tx_mag_track_on=1, instr amp=0)",
    },
    (1, 1): {
        "linestyle": "--",
        "marker": "D",
        "linewidth": 2,
        "alpha": 0.9,
        "markerfacecolor": "none",
        "markeredgewidth": 2,
        "color": "#fdae61",
        "label_suffix": "FPGA magtrack on + magtrack on (Instruments)",
    },
}

CONFIG = {
    "X_COL": DEFAULT_X_COL,
    "GROUP_COLS": list(DEFAULT_GROUP_COLS),
    "EVM_COLS": ["evm"],
}


def read_and_preprocess_rls4_csv(
    csv_file_path: str,
    encoding: str = "utf-8",
    x_col: Optional[str] = None,
    group_cols: Optional[Sequence[str]] = None,
    evm_infer: bool = True,
) -> Tuple[Optional[pd.DataFrame], Dict]:
    """
    Load CSV; aggregate mean EVM for each (panel keys, tx_pwr, tx_mag_track_on, amplitude).
    Returns (agg_df, diag) or (None, diag).
    """
    x_col = (x_col or CONFIG["X_COL"]).strip().lower()
    group_cols = [c.strip().lower() for c in (group_cols or CONFIG["GROUP_COLS"])]
    evm_cols = [c.lower() for c in CONFIG["EVM_COLS"]]

    diag: Dict = {}
    try:
        df, diag = load_mag_track_csv(csv_file_path, encoding=encoding, evm_infer=evm_infer)
    except Exception as e:
        print(f"[ERROR] load_mag_track_csv failed: {e}")
        return None, {"error": str(e), **diag}

    need = [TRACK_COL, AMP_COL, x_col] + list(group_cols) + evm_cols
    miss = [c for c in need if c not in df.columns]
    if miss:
        print(f"[ERROR] Missing columns after load: {miss}")
        return None, diag

    num_cols = [TRACK_COL, AMP_COL, x_col] + list(group_cols) + evm_cols
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=[TRACK_COL, AMP_COL, x_col] + evm_cols)

    # Only 0/1 flags after coercion (same as loader expectation)
    df = df[df[TRACK_COL].isin([0.0, 1.0]) & df[AMP_COL].isin([0.0, 1.0])].copy()
    if df.empty:
        print("[WARN] No rows with valid 0/1 tx_mag_track_on and amplitude after numeric coerce")
        return None, diag

    group_cols_agg = [c for c in list(group_cols) + [x_col, TRACK_COL, AMP_COL] if c in df.columns]
    present_evm = [c for c in evm_cols if c in df.columns]
    if not present_evm:
        print("[WARN] No EVM columns present")
        return None, diag

    out = df.groupby(group_cols_agg, dropna=False)[present_evm[0]].mean().reset_index()
    for c in present_evm[1:]:
        g = df.groupby(group_cols_agg, dropna=False)[c].mean().reset_index()
        out = out.merge(g, on=group_cols_agg, how="outer")

    print(
        f"[OK] Preprocessed: agg rows={len(out)} | x_col={x_col!r} | panel keys={group_cols} "
        f"(FPGA-on curves strict per tuple; tx_mag_track_on=0 baselines: same chan, pool all dly/mag)"
    )
    return out, diag


def _filter_by_group_key(agg_df: pd.DataFrame, key: Tuple, gcols: Sequence[str]) -> pd.DataFrame:
    flt = np.ones(len(agg_df), dtype=bool)
    for i, gcol in enumerate(gcols):
        flt &= agg_df[gcol] == key[i]
    return agg_df.loc[flt].copy()


def _as_f(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def _trk0_baseline_same_chan(
    agg_df: pd.DataFrame,
    chan: float,
    amp: int,
    x_col: str,
    evm_col: str,
) -> pd.DataFrame:
    """
    tx_mag_track_on=0: ignore mag tuple and dly — only match chan (and amplitude).
    Mean EVM at each tx_pwr over all rows with same chan, trk=0, fixed amp.
    """
    trk_f = _as_f(agg_df[TRACK_COL])
    ch_f = _as_f(agg_df["chan"])
    amp_f = _as_f(agg_df[AMP_COL])
    ch = float(chan)
    sub = agg_df.loc[
        (trk_f <= 0.5)
        & (amp_f == float(amp))
        & np.isfinite(ch_f)
        & np.isclose(ch_f.astype(float), ch, rtol=0.0, atol=1e-6)
    ]
    if sub.empty:
        return pd.DataFrame(columns=[x_col, evm_col])
    return sub.groupby(x_col, dropna=False)[evm_col].mean().reset_index()


def _subset_trk1(panel_full: pd.DataFrame, amp: int) -> pd.DataFrame:
    trk_f = _as_f(panel_full[TRACK_COL])
    amp_f = _as_f(panel_full[AMP_COL])
    return panel_full[(trk_f >= 0.5) & (amp_f == float(amp))].copy()


def _plot_one_series(
    ax: plt.Axes,
    sub: pd.DataFrame,
    evm_col: str,
    x_col: str,
    trk: int,
    amp: int,
    style_map: Dict,
    zorder: int,
    linewidth: Optional[float] = None,
    label_extra: str = "",
) -> int:
    if sub.empty:
        return 0
    sub = sub.sort_values(x_col)
    st = style_map[(trk, amp)]
    lw = linewidth if linewidth is not None else st["linewidth"]
    ax.plot(
        sub[x_col],
        sub[evm_col],
        color=st["color"],
        linestyle=st["linestyle"],
        marker=st["marker"],
        linewidth=lw,
        alpha=st["alpha"],
        markerfacecolor=st["markerfacecolor"],
        markeredgewidth=st["markeredgewidth"],
        markersize=6,
        zorder=zorder,
        label=st["label_suffix"] + label_extra,
    )
    return 1


def plot_fpga_panel_with_trk0_relaxed_baselines(
    ax: plt.Axes,
    agg_df: pd.DataFrame,
    key: Tuple,
    gcols: Sequence[str],
    evm_col: str,
    x_col: str,
    style_map: Dict,
) -> Tuple[int, List[str]]:
    """
    One chart: FPGA magtrack-on (1,0)/(1,1) for strict mag tuple `key`, plus
    tx_mag_track_on=0 baselines (0,0)/(0,1): mean EVM vs tx_pwr for same chan only
    (all dly / mag params pooled), so they always overlay FPGA-on curves for comparison.
    """
    warnings: List[str] = []
    if "chan" not in gcols:
        warnings.append("group_cols missing chan; cannot build tx_mag_track_on=0 baselines")
        return 0, warnings

    chan = float(key[gcols.index("chan")])
    panel_full = _filter_by_group_key(agg_df, key, gcols)
    if panel_full.empty:
        return 0, warnings

    trk_f = _as_f(panel_full[TRACK_COL])
    if not ((trk_f >= 0.5).any()):
        return 0, warnings

    drawn = 0
    for amp in (0, 1):
        sub0 = _trk0_baseline_same_chan(agg_df, chan, amp, x_col, evm_col)
        extra = " [tx_mag_track_on=0: mean over dly & mag params, same chan]"
        if sub0.empty:
            warnings.append(f"No tx_mag_track_on=0, amplitude={amp} data for chan={chan}")
        drawn += _plot_one_series(
            ax,
            sub0,
            evm_col,
            x_col,
            0,
            amp,
            style_map,
            zorder=2,
            linewidth=2.3,
            label_extra=extra,
        )

    for amp in (0, 1):
        sub1 = _subset_trk1(panel_full, amp)
        drawn += _plot_one_series(ax, sub1, evm_col, x_col, 1, amp, style_map, zorder=4)

    return drawn, warnings


def generate_and_save_figs(
    agg_df: pd.DataFrame,
    pdf_save_path: str,
    x_col: str,
    group_cols: Sequence[str],
) -> bool:
    if os.path.exists(pdf_save_path):
        try:
            os.remove(pdf_save_path)
            print(f"[INFO] Removed existing PDF: {pdf_save_path}")
        except OSError as e:
            print(f"[ERROR] Could not remove PDF: {e}")
            return False

    evm_cols = [c for c in CONFIG["EVM_COLS"] if c in agg_df.columns]
    if not evm_cols:
        print("[WARN] No EVM columns in aggregated data")
        return False

    gcols = [c for c in group_cols if c in agg_df.columns]
    if not gcols:
        print("[WARN] No group columns in data")
        return False

    sub1 = agg_df[agg_df[TRACK_COL] == 1.0]
    if sub1.empty:
        print("[WARN] No rows with tx_mag_track_on=1; PDF will have no pages")
        keys: List[Tuple] = []
    else:
        keys = sorted(sub1.groupby(gcols, dropna=False).groups.keys(), key=lambda t: tuple(t))
    print(f"\n[INFO] PDF panels (FPGA-on mag tuples + tx_mag_track_on=0 baselines by chan): {len(keys)}")

    pdf = PdfPages(pdf_save_path)
    total = 0
    plot_warnings: List[str] = []
    try:
        for key in keys:
            key_str = " | ".join(f"{g}={v}" for g, v in zip(gcols, key))
            for evm_col in evm_cols:
                fig, ax = plt.subplots(figsize=(10, 6))
                title = (
                    f"{evm_col.upper()} (RLS4.0 FPGA) — compare vs {x_col}\n{key_str}\n"
                    "Green/orange: FPGA magtrack on (strict mag tuple). "
                    "Blue/red: tx_mag_track_on=0 (mean EVM over all dly & mag params, same chan)."
                )
                ax.set_title(title, fontsize=10, fontweight="bold", pad=10)
                ax.set_xlabel(f"{x_col} (dBm)", fontsize=10, fontweight="bold")
                ax.set_ylabel(f"{evm_col.upper()} (dB)", fontsize=10, fontweight="bold")
                ax.grid(True, alpha=0.3)

                n_curves, wlist = plot_fpga_panel_with_trk0_relaxed_baselines(
                    ax, agg_df, tuple(key), gcols, evm_col, x_col, STYLE_MAP
                )
                plot_warnings.extend(wlist)
                if n_curves == 0:
                    plt.close(fig)
                    continue

                total += 1
                ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=7, frameon=True)
                fig.tight_layout()
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)
                gc.collect()
                print(f"[OK] Fig {total}: {key_str[:90]}...")
    finally:
        pdf.close()

    warn_path = os.path.splitext(pdf_save_path)[0] + "_plot_warnings.txt"
    if plot_warnings:
        try:
            with open(warn_path, "w", encoding="utf-8") as wf:
                wf.write("\n".join(plot_warnings[:500]))
                if len(plot_warnings) > 500:
                    wf.write(f"\n... ({len(plot_warnings) - 500} more)\n")
            print(f"[INFO] Plot warnings written: {warn_path}")
        except OSError:
            pass

    print(f"\n[OK] PDF saved: {pdf_save_path} ({total} pages)")
    return total > 0


def batch_process_csv(
    csv_dir: str,
    pdf_save_root_dir: str,
    recursive: bool = False,
    encoding: str = "utf-8",
    x_col: Optional[str] = None,
    group_cols: Optional[Sequence[str]] = None,
    evm_infer: bool = True,
) -> None:
    csv_files: List[str] = []
    for root, _, files in os.walk(csv_dir):
        for fn in files:
            if fn.lower().endswith(".csv"):
                csv_files.append(os.path.abspath(os.path.join(root, fn)))
        if not recursive:
            break

    if not csv_files:
        print("[WARN] No CSV files found")
        return

    x_col = (x_col or CONFIG["X_COL"]).strip().lower()
    group_cols = [c.strip().lower() for c in (group_cols or CONFIG["GROUP_COLS"])]

    print(f"\n[INFO] Found {len(csv_files)} CSV file(s)")
    os.makedirs(pdf_save_root_dir, exist_ok=True)

    for csv_path in csv_files:
        gc.collect()
        agg, diag = read_and_preprocess_rls4_csv(
            csv_path,
            encoding=encoding,
            x_col=x_col,
            group_cols=group_cols,
            evm_infer=evm_infer,
        )
        if agg is None or agg.empty:
            print(f"[WARN] Skip: {csv_path}")
            continue
        base = os.path.splitext(os.path.basename(csv_path))[0]
        pdf_path = os.path.join(pdf_save_root_dir, f"{base}_rls4_magtrk.pdf")
        generate_and_save_figs(agg, pdf_path, x_col, group_cols)
        diag_path = os.path.join(pdf_save_root_dir, f"{base}_load_diag.txt")
        try:
            with open(diag_path, "w", encoding="utf-8") as f:
                for k, v in sorted(diag.items()):
                    f.write(f"{k}: {v}\n")
        except OSError:
            pass
        del agg
        gc.collect()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "RLS4.0 FPGA mag_track_test_res CSV -> EVM vs tx_pwr PDF. "
            "One page per mag tuple where tx_mag_track_on=1 exists; overlays tx_mag_track_on=0 "
            "baselines (tx_mag_track_on=0, same chan, all dly/mag pooled) with FPGA-on curves."
        )
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="CSV file or directory of CSVs (default: built-in sample path if exists)",
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        default=None,
        help="Output directory for PDF (+ optional diag .txt)",
    )
    parser.add_argument("--encoding", default="utf-8", help="CSV encoding passed to loader")
    parser.add_argument(
        "--x-column",
        default=DEFAULT_X_COL,
        metavar="COL",
        help=f"X-axis column after normalize (default: {DEFAULT_X_COL})",
    )
    parser.add_argument(
        "--group-cols",
        default=None,
        metavar="LIST",
        help="Comma-separated panel key columns (default: chan,dly,start_point,win_len,chn_len,chn_ofst,start_mode)",
    )
    parser.add_argument(
        "--no-evm-infer",
        action="store_true",
        help="Pass through to loader: do not infer EVM from other columns",
    )
    parser.add_argument("-r", "--recursive", action="store_true", help="Walk subdirs for CSV when input is a directory")
    args = parser.parse_args()

    default_csv = (
        r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\mag_track_test_res\rls4\20260514"
        r"\mag_track_test_res_20260514_115140.csv"
    )
    inp = args.input or default_csv
    if not os.path.exists(inp):
        print(f"[ERROR] Input not found: {inp}", file=sys.stderr)
        sys.exit(1)

    out_dir = args.out_dir
    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(os.path.abspath(inp)), "rls4_magtrk_pdf_out")

    CONFIG["X_COL"] = args.x_column.strip().lower()
    if args.group_cols:
        CONFIG["GROUP_COLS"] = [c.strip().lower() for c in args.group_cols.split(",") if c.strip()]

    group_cols = list(CONFIG["GROUP_COLS"])

    try:
        if os.path.isdir(inp):
            batch_process_csv(
                inp,
                out_dir,
                recursive=args.recursive,
                encoding=args.encoding,
                x_col=CONFIG["X_COL"],
                group_cols=group_cols,
                evm_infer=not args.no_evm_infer,
            )
        else:
            os.makedirs(out_dir, exist_ok=True)
            agg, diag = read_and_preprocess_rls4_csv(
                inp,
                encoding=args.encoding,
                x_col=CONFIG["X_COL"],
                group_cols=group_cols,
                evm_infer=not args.no_evm_infer,
            )
            if agg is None or agg.empty:
                sys.exit(1)
            base = os.path.splitext(os.path.basename(inp))[0]
            pdf_path = os.path.join(out_dir, f"{base}_rls4_magtrk.pdf")
            generate_and_save_figs(agg, pdf_path, CONFIG["X_COL"], group_cols)
            diag_path = os.path.join(out_dir, f"{base}_load_diag.txt")
            with open(diag_path, "w", encoding="utf-8") as f:
                for k, v in sorted(diag.items()):
                    f.write(f"{k}: {v}\n")
            print(f"\n[INFO] Diagnostics: {diag_path}")
        print(f"\n[OK] Done. Output dir: {out_dir}")
    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
