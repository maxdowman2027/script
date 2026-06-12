#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot time-domain I/Q and Welch PSD from I/Q CSV.

Supported input layouts:
  - single: sample_i / sample_q (one stream; Ch0 & Ch1 plots show same data)
  - 2ant:   ch0_sample_q/i, ch1_sample_q/i (dual-antenna, from parse_60bit_40bit_2ant_iq)

Large inputs: read only first MAX_ROWS rows. Output PDF defaults to
<input_stem>_spec.pdf beside the input CSV.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Optional, Sequence

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import welch
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages

# =============================================================================
# 配置区
# =============================================================================
CSV_FILE = r"D:\test_data\E22_M2\260611\phy_mode20_2ant\hesu_20m_mcs0_data_2ant_iq.csv"
OUTPUT_PDF = ""  # 空 → <input_stem>_spec.pdf
MAX_ROWS = 65536  # 大文件只读前 N 行；0 = 读全文件（可能内存不足）
TIME_PLOT_SAMPLES = 65535  # 时域图最多绘制的采样点数（0 = 与读取行数相同）
IQ_BIT_WIDTH = 10  # 归一化除数 2**IQ_BIT_WIDTH
IQ_MODE = "auto"  # auto | single | 2ant
OUTPUT_SUFFIX = "_spec"

fs = 80e6
fs_downsampled = fs

IQMode = str  # "auto" | "single" | "2ant"

SINGLE_IQ_COLS = ("sample_i", "sample_q")
TWO_ANT_IQ_COLS = (
    "ch0_sample_q",
    "ch0_sample_i",
    "ch1_sample_q",
    "ch1_sample_i",
)


@dataclass
class IQChannels:
    mode: str  # "single" or "2ant"
    ch0_i: np.ndarray
    ch0_q: np.ndarray
    ch1_i: np.ndarray
    ch1_q: np.ndarray


def default_output_pdf(csv_file: str) -> str:
    base, _ext = os.path.splitext(os.path.abspath(csv_file))
    return f"{base}{OUTPUT_SUFFIX}.pdf"


def _col_map(columns: Sequence[str]) -> dict:
    return {str(c).strip().lower(): str(c).strip() for c in columns}


def detect_iq_mode(columns: Sequence[str], *, mode: IQMode = "auto") -> str:
    lower = _col_map(columns)
    has_2ant = all(name in lower for name in TWO_ANT_IQ_COLS)
    has_single = "sample_i" in lower and "sample_q" in lower

    if mode == "2ant":
        if not has_2ant:
            raise ValueError(
                f"2ant mode requires {list(TWO_ANT_IQ_COLS)}; got {list(columns)}"
            )
        return "2ant"
    if mode == "single":
        if not has_single:
            raise ValueError(
                f"single mode requires sample_i and sample_q; got {list(columns)}"
            )
        return "single"

    if has_2ant:
        return "2ant"
    if has_single:
        return "single"
    raise ValueError(
        "Cannot detect I/Q layout; need sample_i/sample_q or "
        f"{list(TWO_ANT_IQ_COLS)}; got {list(columns)}"
    )


def read_iq_data(
    csv_file: str,
    max_rows: int = MAX_ROWS,
    *,
    mode: IQMode = "auto",
) -> Optional[IQChannels]:
    """Read single-stream or dual-antenna I/Q CSV."""
    try:
        head = pd.read_csv(csv_file, nrows=0)
        layout = detect_iq_mode(head.columns, mode=mode)
        lower = _col_map(head.columns)

        if layout == "2ant":
            usecols = [lower[name] for name in TWO_ANT_IQ_COLS]
        else:
            usecols = [lower["sample_i"], lower["sample_q"]]

        read_kwargs = {"usecols": usecols}
        if max_rows > 0:
            read_kwargs["nrows"] = max_rows

        df = pd.read_csv(csv_file, **read_kwargs)

        if layout == "2ant":
            ch0_q = df[lower["ch0_sample_q"]].to_numpy()
            ch0_i = df[lower["ch0_sample_i"]].to_numpy()
            ch1_q = df[lower["ch1_sample_q"]].to_numpy()
            ch1_i = df[lower["ch1_sample_i"]].to_numpy()
        else:
            ch0_i = df[lower["sample_i"]].to_numpy()
            ch0_q = df[lower["sample_q"]].to_numpy()
            ch1_i = ch0_i
            ch1_q = ch0_q

        if max_rows > 0:
            print(
                f"已读取前 {len(df)} 行（MAX_ROWS={max_rows}，mode={layout}），"
                f"源文件: {csv_file}"
            )
        else:
            print(f"已读取全部 {len(df)} 行（mode={layout}），源文件: {csv_file}")

        return IQChannels(mode=layout, ch0_i=ch0_i, ch0_q=ch0_q, ch1_i=ch1_i, ch1_q=ch1_q)

    except Exception as e:
        print(f"读取数据时出错: {e}")
        import traceback
        print(f"详细信息:\n{traceback.format_exc()}")
        return None


def normalize_data(data, *, bit_width: int = IQ_BIT_WIDTH):
    """归一化到约 [-1, 1]。"""
    return data / (2**bit_width)


def plot_time_waveform(
    i_data,
    q_data,
    fs_hz: float,
    title: str,
    ax,
    *,
    max_samples: int = TIME_PLOT_SAMPLES,
):
    """绘制 I/Q 时域波形（时间轴 us）。"""
    n = len(i_data)
    if max_samples > 0:
        n = min(n, max_samples)
    t_us = np.arange(n) / fs_hz * 1e6
    ax.plot(t_us, i_data[:n], color="C0", linewidth=0.6, label="I")
    ax.plot(t_us, q_data[:n], color="C1", linewidth=0.6, label="Q")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("时间 (us)", fontsize=8)
    ax.set_ylabel("幅度 (归一化)", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=7)
    return ax


def plot_psd(data_complex, fs_mhz: float, title: str, ax, color: str):
    """绘制功率谱密度 (PSD) 图。"""
    n = len(data_complex)
    nfft = min(65536, n)
    if nfft < 8:
        ax.set_title(f"{title} (too few samples)")
        return ax

    overlap = nfft // 2
    win = np.hanning(nfft)

    freq_hz, pxx = welch(
        data_complex,
        fs_mhz * 1e6,
        win,
        noverlap=overlap,
        nfft=nfft,
        return_onesided=False,
        detrend=False,
    )

    freq_mhz = np.fft.fftshift(freq_hz) / 1e6
    psd = np.fft.fftshift(pxx)
    psd_db = 10 * np.log10(np.maximum(np.abs(psd), 1e-30))

    ax.plot(freq_mhz, psd_db, color=color, linewidth=0.8)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("频率 (MHz)", fontsize=8)
    ax.set_ylabel("功率密度 (dB)", fontsize=8)
    ax.grid(True, which="both", axis="both", alpha=0.3)
    ax.set_xlim([-fs_mhz / 2, fs_mhz / 2])
    ax.set_ylim([np.min(psd_db) - 10, np.max(psd_db) + 10])
    return ax


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Plot time-domain I/Q and PSD from sample_i/q or dual-antenna "
            "ch0/ch1 I/Q CSV."
        )
    )
    p.add_argument(
        "csv_file",
        nargs="?",
        default=CSV_FILE,
        help="Input *_iq_merged.csv / *_iq8.csv / *_2ant_iq.csv",
    )
    p.add_argument(
        "-o",
        "--output",
        default=OUTPUT_PDF,
        help="Output PDF (default: <input_stem>_spec.pdf)",
    )
    p.add_argument(
        "--mode",
        choices=("auto", "single", "2ant"),
        default=IQ_MODE,
        help="I/Q layout: auto-detect, single (sample_i/q), or 2ant (default: auto)",
    )
    p.add_argument(
        "--max-rows",
        type=int,
        default=MAX_ROWS,
        help="Read only first N rows (default: MAX_ROWS; 0 = entire file)",
    )
    p.add_argument(
        "--time-samples",
        type=int,
        default=TIME_PLOT_SAMPLES,
        help="Max samples shown on time plot (0 = all read rows)",
    )
    p.add_argument(
        "--bit-width",
        type=int,
        default=IQ_BIT_WIDTH,
        help="ADC bit width for normalization divisor (default 10)",
    )
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    csv_file = os.path.abspath(args.csv_file)
    output_pdf = os.path.abspath(args.output or default_output_pdf(csv_file))
    os.makedirs(os.path.dirname(output_pdf) or ".", exist_ok=True)

    iq = read_iq_data(csv_file, max_rows=args.max_rows, mode=args.mode)
    if iq is None:
        return False

    ch0_i = normalize_data(iq.ch0_i, bit_width=args.bit_width)
    ch0_q = normalize_data(iq.ch0_q, bit_width=args.bit_width)
    ch1_i = normalize_data(iq.ch1_i, bit_width=args.bit_width)
    ch1_q = normalize_data(iq.ch1_q, bit_width=args.bit_width)

    ch0_signal = ch0_i + 1j * ch0_q
    ch1_signal = ch1_i + 1j * ch1_q

    fs_hz = fs_downsampled
    fs_mhz = fs_hz / 1e6
    time_n = args.time_samples if args.time_samples > 0 else len(ch0_i)
    mode_label = "双天线" if iq.mode == "2ant" else "单路"

    with PdfPages(output_pdf) as pdf:
        fig_t = plt.figure(figsize=(15, 8), tight_layout=True)
        fig_t.suptitle(
            f"I/Q 时域波形 ({mode_label}, 采样率: {fs_mhz:.0f} MHz, "
            f"显示前 {min(time_n, len(ch0_i))} 点)",
            fontsize=14,
            y=0.98,
        )
        gs_t = gridspec.GridSpec(1, 2, figure=fig_t)
        plot_time_waveform(
            ch0_i,
            ch0_q,
            fs_hz,
            "Ch0 - I/Q 时域",
            fig_t.add_subplot(gs_t[0, 0]),
            max_samples=time_n,
        )
        plot_time_waveform(
            ch1_i,
            ch1_q,
            fs_hz,
            "Ch1 - I/Q 时域",
            fig_t.add_subplot(gs_t[0, 1]),
            max_samples=time_n,
        )
        pdf.savefig(fig_t)
        plt.close(fig_t)

        fig_f = plt.figure(figsize=(15, 8), tight_layout=True)
        fig_f.suptitle(
            f"I/Q 功率谱密度 ({mode_label}, 采样率: {fs_mhz:.0f} MHz)",
            fontsize=14,
            y=0.98,
        )
        gs_f = gridspec.GridSpec(1, 2, figure=fig_f)
        plot_psd(ch0_signal, fs_mhz, "Ch0 - I/Q PSD", fig_f.add_subplot(gs_f[0, 0]), "blue")
        plot_psd(ch1_signal, fs_mhz, "Ch1 - I/Q PSD", fig_f.add_subplot(gs_f[0, 1]), "orange")
        pdf.savefig(fig_f)
        plt.close(fig_f)

        print(f"时域 + 频谱 PDF 已保存到: {output_pdf} (mode={iq.mode})")

    plt.close("all")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
