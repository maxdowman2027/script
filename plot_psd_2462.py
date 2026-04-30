#!/usr/bin/env python3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 非交互式后端，用于生成PDF
import matplotlib.pyplot as plt
from scipy.signal import welch
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
    # 创建PDF文件
output_pdf = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\dump_node_124\FPGA752_0x_20260428\2462_vht_mcs8_bcc_nss1_psd.pdf"
# 采样率（80MHz）
fs = 80e6  # 80MHz
# 同时调整采样率
# fs_downsampled = fs / 2
fs_downsampled = fs 
def read_data():
    """读取CSV数据"""
    csv_file = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\dump_node_124\FPGA752_0x_20260428\adcdump_dacdata.csv"
    try:
        df = pd.read_csv(csv_file)

        # 提取所需列的数据
        dac_i_ch0 = df['sample_i'].values
        dac_q_ch0 = df['sample_q'].values
        dac_i_ch1 = df['sample_i'].values
        dac_q_ch1 = df['sample_q'].values

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

def plot_psd(data_complex, fs, title, ax, color):
    """绘制功率谱密度(PSD)图"""
    # 使用welch方法计算PSD
    NFFT = min(8000, len(data_complex))  # 调整NFFT大小，确保不大于信号长度
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

def main():


    # 读取数据
    dac_i_ch0, dac_q_ch0, dac_i_ch1, dac_q_ch1 = read_data()
    if dac_i_ch0 is None:
        return False

    # 归一化数据到[-1, 1]范围
    dac_i_ch0_norm = normalize_data(dac_i_ch0)
    dac_q_ch0_norm = normalize_data(dac_q_ch0)
    dac_i_ch1_norm = normalize_data(dac_i_ch1)
    dac_q_ch1_norm = normalize_data(dac_q_ch1)

    # 对数据进行2抽1降采样
    dac_i_ch0_norm = dac_i_ch0_norm[::2]
    dac_q_ch0_norm = dac_q_ch0_norm[::2]
    dac_i_ch1_norm = dac_i_ch1_norm[::2]
    dac_q_ch1_norm = dac_q_ch1_norm[::2]



    # 合并I和Q数据为复数信号
    ch0_signal = np.array([complex(i, q) for i, q in zip(dac_i_ch0_norm, dac_q_ch0_norm)])
    ch1_signal = np.array([complex(i, q) for i, q in zip(dac_i_ch1_norm, dac_q_ch1_norm)])


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
    main()
