#!/usr/bin/env python3
import argparse
import os
import sys

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 非交互式后端，用于生成PDF
import matplotlib.pyplot as plt
from scipy.signal import welch
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages

# =============================================================================
# 配置区
# =============================================================================
CSV_FILE = r"D:\test_data\E22_M2\260609\data\espwifi_modem_dump.20260609-085029-008_data_iq_merged.csv"
OUTPUT_PDF = r"D:\test_data\E22_M2\260609\data\espwifi_modem_dump.20260609-085029-008_data_iq_merged_spec.pdf"
MAX_ROWS = 65536  # 大文件只读前 N 行；0 = 读全文件（可能内存不足）
IQ_COLS = ("sample_i", "sample_q")

fs = 160e6
fs_downsampled = fs


def read_data(csv_file: str, max_rows: int = MAX_ROWS):
    """读取 CSV 的 sample_i / sample_q；max_rows>0 时仅读文件前部。"""
    try:
        read_kwargs = {"usecols": list(IQ_COLS)}
        if max_rows > 0:
            read_kwargs["nrows"] = max_rows

        df = pd.read_csv(csv_file, **read_kwargs)

        dac_i = df[IQ_COLS[0]].to_numpy()
        dac_q = df[IQ_COLS[1]].to_numpy()

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

def normalize_data(data):
    """归一化数据到范围 [-1, 1]"""
    # data_min = np.min(data)
    # data_max = np.max(data)
    # normalized_data = 2 * (data - data_min) / (data_max - data_min) - 1
    normalized_data = data / (2**8)
    return normalized_data

def plot_psd(data_complex, fs, title, ax, color):
    """绘制功率谱密度(PSD)图"""
    # 使用welch方法计算PSD
    NFFT = min(16384, len(data_complex))  # 调整NFFT大小，确保不大于信号长度
    overlap = NFFT / 2
    win = np.hanning(NFFT)

    [F, P] = welch(data_complex, fs, win, noverlap=overlap, nfft=NFFT,
                   return_onesided=False, detrend=False)

    # 绘制PSD
    ax.plot(np.fft.fftshift(F), 10 * np.log10(np.abs(np.fft.fftshift(P))),
            color=color, linewidth=0.8)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel('频率 (MHz)', fontsize=8)
    ax.set_ylabel('功率密度 (dB)', fontsize=8)
    ax.grid(True, which='both', axis='both', alpha=0.3)

    # 设置频率范围（-40MHz到40MHz）
    ax.set_xlim([-fs/2, fs/2])

    # 自动设置Y轴范围
    psd_db = 10 * np.log10(np.abs(P))
    ax.set_ylim([np.min(psd_db) - 10, np.max(psd_db) + 10])

    return ax

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Plot PSD from sample_i/sample_q CSV (large files: read head only).")
    p.add_argument("csv_file", nargs="?", default=CSV_FILE, help="Input *_iq_merged.csv")
    p.add_argument("-o", "--output", default=OUTPUT_PDF, help="Output PDF path")
    p.add_argument(
        "--max-rows",
        type=int,
        default=MAX_ROWS,
        help="Read only first N rows (default: config MAX_ROWS; 0 = entire file)",
    )
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    output_pdf = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output_pdf) or ".", exist_ok=True)

    dac_i_ch0, dac_q_ch0, dac_i_ch1, dac_q_ch1 = read_data(args.csv_file, max_rows=args.max_rows)
    if dac_i_ch0 is None:
        return False

    # 归一化数据到[-1, 1]范围
    dac_i_ch0_norm = normalize_data(dac_i_ch0)
    dac_q_ch0_norm = normalize_data(dac_q_ch0)
    dac_i_ch1_norm = normalize_data(dac_i_ch1)
    dac_q_ch1_norm = normalize_data(dac_q_ch1)

    # dac_i_ch0_norm = dac_i_ch0
    # dac_q_ch0_norm = dac_q_ch0
    # dac_i_ch1_norm = dac_i_ch1
    # dac_q_ch1_norm = dac_q_ch1
    # 对数据进行2抽1降采样
    # dac_i_ch0_norm = dac_i_ch0_norm[::2]
    # dac_q_ch0_norm = dac_q_ch0_norm[::2]
    # dac_i_ch1_norm = dac_i_ch1_norm[::2]
    # dac_q_ch1_norm = dac_q_ch1_norm[::2]



    ch0_signal = dac_i_ch0_norm + 1j * dac_q_ch0_norm
    ch1_signal = dac_i_ch1_norm + 1j * dac_q_ch1_norm


    with PdfPages(output_pdf) as pdf:
        # 创建图形
        fig = plt.figure(figsize=(15, 8), tight_layout=True)

        # 标题
        fig.suptitle(f'DAC输出功率谱密度图 (采样率: {fs_downsampled/1e6:.0f}MHz)', fontsize=14, y=0.98)

        # 使用gridspec安排子图
        gs = gridspec.GridSpec(1, 2, figure=fig)

        # 绘制CH0的PSD
        ax1 = fig.add_subplot(gs[0, 0])
        plot_psd(ch0_signal, fs_downsampled/1e6, 'Ch0 - I/Q 合并频谱 (2抽1降采样)', ax1, 'blue')

        # 绘制CH1的PSD
        ax2 = fig.add_subplot(gs[0, 1])
        plot_psd(ch1_signal, fs_downsampled/1e6, 'Ch1 - I/Q 合并频谱 (2抽1降采样)', ax2, 'orange')

        # 保存到PDF
        pdf.savefig(fig)

        print(f"功率谱密度图已保存到: {output_pdf}")

    plt.close('all')  # 关闭所有图形
    return True

if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
