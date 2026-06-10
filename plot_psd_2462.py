#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot time-domain I/Q and Welch PSD from sample_i / sample_q CSV.

Large inputs: read only first MAX_ROWS rows. Output PDF defaults to
<input_stem>_spec.pdf beside the input CSV.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional, Sequence, Tuple

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
CSV_FILE = r"D:\test_data\E22_M2\260610\axi_tone_48bit\espwifi_modem_dump.20260610-083342-006_data_iq8.csv"
OUTPUT_PDF = ""  # 空 → <input_stem>_spec.pdf
MAX_ROWS = 65536  # 大文件只读前 N 行；0 = 读全文件（可能内存不足）
TIME_PLOT_SAMPLES = 4096  # 时域图最多绘制的采样点数（0 = 与读取行数相同）
IQ_BIT_WIDTH = 8  # 归一化除数 2**IQ_BIT_WIDTH
OUTPUT_SUFFIX = "_spec"

fs = 160e6
fs_downsampled = fs


def default_output_pdf(csv_file: str) -> str:
    base, _ext = os.path.splitext(os.path.abspath(csv_file))
    return f"{base}{OUTPUT_SUFFIX}.pdf"


def detect_iq_columns(columns: Sequence[str]) -> Tuple[str, str]:
    names = [str(c).strip() for c in columns]
    lower = {c.lower(): c for c in names}
    if "sample_i" in lower and "sample_q" in lower:
        return lower["sample_i"], lower["sample_q"]
    if "sample_q" in lower and "sample_i" in lower:
        return lower["sample_i"], lower["sample_q"]
    raise ValueError(f"CSV must contain sample_i and sample_q; got {list(columns)}")


def read_data(csv_file: str, max_rows: int = MAX_ROWS):
    """读取 CSV 的 sample_i / sample_q；max_rows>0 时仅读文件前部。"""
    try:
        head = pd.read_csv(csv_file, nrows=0)
        i_col, q_col = detect_iq_columns(head.columns)

        read_kwargs = {"usecols": [i_col, q_col]}
        if max_rows > 0:
            read_kwargs["nrows"] = max_rows

        df = pd.read_csv(csv_file, **read_kwargs)

        dac_i = df[i_col].to_numpy()
        dac_q = df[q_col].to_numpy()

        if max_rows > 0:
            print(
                f"已读取前 {len(df)} 行（MAX_ROWS={max_rows}），"
                f"源文件: {csv_file}"
            )
        else:
            print(f"已读取全部 {len(df)} 行，源文件: {csv_file}")

        return dac_i, dac_q, dac_i, dac_q

    except Exception as e:
        print(f"读取数据时出错: {e}")
        import traceback
        print(f"详细信息:\n{traceback.format_exc()}")
        return None, None, None, None


def normalize_data(data, *, bit_width: int = IQ_BIT_WIDTH):
    """归一化到约 [-1, 1]（默认 8-bit ADC）。"""
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
    nfft = min(16384, n)
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
        description="Plot time-domain I/Q and PSD from sample_i/sample_q CSV."
    )
    p.add_argument(
        "csv_file",
        nargs="?",
        default=CSV_FILE,
        help="Input *_iq_merged.csv / *_iq8.csv",
    )
    p.add_argument(
        "-o",
        "--output",
        default=OUTPUT_PDF,
        help="Output PDF (default: <input_stem>_spec.pdf)",
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
        help="ADC bit width for normalization divisor (default 8)",
    )
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    csv_file = os.path.abspath(args.csv_file)
    output_pdf = os.path.abspath(args.output or default_output_pdf(csv_file))
    os.makedirs(os.path.dirname(output_pdf) or ".", exist_ok=True)

    dac_i_ch0, dac_q_ch0, dac_i_ch1, dac_q_ch1 = read_data(csv_file, max_rows=args.max_rows)
    if dac_i_ch0 is None:
        return False

    dac_i_ch0_norm = normalize_data(dac_i_ch0, bit_width=args.bit_width)
    dac_q_ch0_norm = normalize_data(dac_q_ch0, bit_width=args.bit_width)
    dac_i_ch1_norm = normalize_data(dac_i_ch1, bit_width=args.bit_width)
    dac_q_ch1_norm = normalize_data(dac_q_ch1, bit_width=args.bit_width)

    ch0_signal = dac_i_ch0_norm + 1j * dac_q_ch0_norm
    ch1_signal = dac_i_ch1_norm + 1j * dac_q_ch1_norm

    fs_hz = fs_downsampled
    fs_mhz = fs_hz / 1e6
    time_n = args.time_samples if args.time_samples > 0 else len(dac_i_ch0_norm)

    with PdfPages(output_pdf) as pdf:
        # Page 1: time domain
        fig_t = plt.figure(figsize=(15, 8), tight_layout=True)
        fig_t.suptitle(
            f"I/Q 时域波形 (采样率: {fs_mhz:.0f} MHz, 显示前 {min(time_n, len(dac_i_ch0_norm))} 点)",
            fontsize=14,
            y=0.98,
        )
        gs_t = gridspec.GridSpec(1, 2, figure=fig_t)
        ax_t0 = fig_t.add_subplot(gs_t[0, 0])
        plot_time_waveform(
            dac_i_ch0_norm,
            dac_q_ch0_norm,
            fs_hz,
            "Ch0 - I/Q 时域",
            ax_t0,
            max_samples=time_n,
        )
        ax_t1 = fig_t.add_subplot(gs_t[0, 1])
        plot_time_waveform(
            dac_i_ch1_norm,
            dac_q_ch1_norm,
            fs_hz,
            "Ch1 - I/Q 时域",
            ax_t1,
            max_samples=time_n,
        )
        pdf.savefig(fig_t)
        plt.close(fig_t)

        # Page 2: PSD
        fig_f = plt.figure(figsize=(15, 8), tight_layout=True)
        fig_f.suptitle(f"I/Q 功率谱密度 (采样率: {fs_mhz:.0f} MHz)", fontsize=14, y=0.98)
        gs_f = gridspec.GridSpec(1, 2, figure=fig_f)
        ax_f0 = fig_f.add_subplot(gs_f[0, 0])
        plot_psd(ch0_signal, fs_mhz, "Ch0 - I/Q PSD", ax_f0, "blue")
        ax_f1 = fig_f.add_subplot(gs_f[0, 1])
        plot_psd(ch1_signal, fs_mhz, "Ch1 - I/Q PSD", ax_f1, "orange")
        pdf.savefig(fig_f)
        plt.close(fig_f)

        print(f"时域 + 频谱 PDF 已保存到: {output_pdf}")

    plt.close("all")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
