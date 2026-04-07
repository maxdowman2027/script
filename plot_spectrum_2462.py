#!/usr/bin/env python3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 非交互式后端，用于生成PDF
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages

def read_data():
    """读取CSV数据"""
    csv_file = r"D:\test_data\wifi7\260327_hesu_nss2\2462_hesu_mcs0_bcc_nss2.csv"
    try:
        df = pd.read_csv(csv_file)

        # 提取所需列的数据（使用实际的列名）
        dac_i_ch0 = df['dac_i_ch0[11:0]'].values
        dac_q_ch0 = df['dac_q_ch0[11:0]'].values
        dac_i_ch1 = df['dac_i_ch1[11:0]'].values
        dac_q_ch1 = df['dac_q_ch1[11:0]'].values

        return dac_i_ch0, dac_q_ch0, dac_i_ch1, dac_q_ch1

    except Exception as e:
        print(f"读取数据时出错: {e}")
        import traceback
        print(f"详细信息:\n{traceback.format_exc()}")
        return None, None, None, None

def normalize_data(data):
    """归一化数据到范围 [-1, 1]"""
    data_min = np.min(data)
    data_max = np.max(data)
    normalized_data = 2 * (data - data_min) / (data_max - data_min) - 1
    return normalized_data

def plot_spectrum(data, fs, title, ax, color):
    """绘制频谱图"""
    # 计算FFT
    n = len(data)
    fft_data = np.fft.fft(data)
    fft_freq = np.fft.fftfreq(n, 1/fs)

    # 只保留正频率部分
    positive_indices = np.where(fft_freq >= 0)
    fft_freq_positive = fft_freq[positive_indices]
    fft_data_positive = fft_data[positive_indices]

    # 计算幅度（dB）
    magnitude = np.abs(fft_data_positive)
    magnitude_db = 20 * np.log10(magnitude + 1e-10)  # 添加小值避免log10(0)

    # 绘制
    ax.plot(fft_freq_positive, magnitude_db, color=color, linewidth=0.8)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel('频率 (MHz)', fontsize=8)
    ax.set_ylabel('幅度 (dB)', fontsize=8)
    ax.grid(True, which='both', axis='both', alpha=0.3)
    ax.set_xlim([0, fs/2])  # Nyquist频率
    ax.set_ylim([np.min(magnitude_db) - 10, np.max(magnitude_db) + 10])

    return ax

def main():
    # 采样率（80MHz）
    fs = 80e6

    # 读取数据
    dac_i_ch0, dac_q_ch0, dac_i_ch1, dac_q_ch1 = read_data()
    if dac_i_ch0 is None:
        return False

    # 归一化数据
    dac_i_ch0_norm = normalize_data(dac_i_ch0)
    dac_q_ch0_norm = normalize_data(dac_q_ch0)
    dac_i_ch1_norm = normalize_data(dac_i_ch1)
    dac_q_ch1_norm = normalize_data(dac_q_ch1)

    # 创建PDF文件
    output_pdf = r"D:\test_data\wifi7\260327_hesu_nss2\2462_hesu_mcs0_bcc_nss2_spectrum.pdf"
    with PdfPages(output_pdf) as pdf:
        # 创建图形
        fig = plt.figure(figsize=(15, 10), tight_layout=True)

        # 标题
        fig.suptitle('DAC输出频谱图 (采样率: 80MHz)', fontsize=14, y=0.98)

        # 使用gridspec安排子图
        gs = gridspec.GridSpec(2, 2, figure=fig)

        # 绘制CH0的I和Q通道
        ax1 = fig.add_subplot(gs[0, 0])
        plot_spectrum(dac_i_ch0_norm, fs, 'Ch0 - I 通道频谱', ax1, 'blue')

        ax2 = fig.add_subplot(gs[0, 1])
        plot_spectrum(dac_q_ch0_norm, fs, 'Ch0 - Q 通道频谱', ax2, 'green')

        # 绘制CH1的I和Q通道
        ax3 = fig.add_subplot(gs[1, 0])
        plot_spectrum(dac_i_ch1_norm, fs, 'Ch1 - I 通道频谱', ax3, 'orange')

        ax4 = fig.add_subplot(gs[1, 1])
        plot_spectrum(dac_q_ch1_norm, fs, 'Ch1 - Q 通道频谱', ax4, 'red')

        # 保存到PDF
        pdf.savefig(fig)

        # 创建总览图（四个通道叠加）
        fig_combined = plt.figure(figsize=(12, 6), tight_layout=True)
        ax_combined = fig_combined.add_subplot(111)

        plot_spectrum(dac_i_ch0_norm, fs, '', ax_combined, 'blue')
        plot_spectrum(dac_q_ch0_norm, fs, '', ax_combined, 'green')
        plot_spectrum(dac_i_ch1_norm, fs, '', ax_combined, 'orange')
        plot_spectrum(dac_q_ch1_norm, fs, '', ax_combined, 'red')

        ax_combined.set_title('所有通道频谱叠加 (Ch0-I:蓝色, Ch0-Q:绿色, Ch1-I:橙色, Ch1-Q:红色)', fontsize=12)
        ax_combined.set_xlabel('频率 (MHz)', fontsize=10)
        ax_combined.set_ylabel('幅度 (dB)', fontsize=10)
        ax_combined.grid(True, which='both', axis='both', alpha=0.3)
        ax_combined.set_xlim([0, fs/2])

        pdf.savefig(fig_combined)

        # 创建数据统计信息表格
        fig_stats = plt.figure(figsize=(10, 6), tight_layout=True)
        ax_stats = fig_stats.add_subplot(111)
        ax_stats.axis('tight')
        ax_stats.axis('off')

        # 计算统计数据
        stats_data = [
            ["Ch0 - I", np.mean(dac_i_ch0), np.std(dac_i_ch0), np.min(dac_i_ch0), np.max(dac_i_ch0)],
            ["Ch0 - Q", np.mean(dac_q_ch0), np.std(dac_q_ch0), np.min(dac_q_ch0), np.max(dac_q_ch0)],
            ["Ch1 - I", np.mean(dac_i_ch1), np.std(dac_i_ch1), np.min(dac_i_ch1), np.max(dac_i_ch1)],
            ["Ch1 - Q", np.mean(dac_q_ch1), np.std(dac_q_ch1), np.min(dac_q_ch1), np.max(dac_q_ch1)]
        ]

        # 创建表格
        table = ax_stats.table(
            cellText=stats_data,
            colLabels=["通道", "平均值", "标准差", "最小值", "最大值"],
            loc='center',
            cellLoc='center'
        )

        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.2)

        # 为表头设置样式
        for j in range(len(stats_data[0])):
            cell = table[0, j]
            cell.set_text_props(weight='bold')
            cell.set_facecolor('#e6e6e6')

        plt.title('数据统计信息', fontsize=12)
        pdf.savefig(fig_stats)

        print(f"频谱图已保存到: {output_pdf}")

    plt.close('all')  # 关闭所有图形
    return True

if __name__ == "__main__":
    main()
