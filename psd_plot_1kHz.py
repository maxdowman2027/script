import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import os
import glob
import csv
import re
from scipy.signal import welch


def calculate_psd(data, Fs, nfft, window, overlap):
    """计算功率谱密度"""
    [F, P] = welch(data, Fs, window, noverlap=overlap, nfft=nfft,
                  return_onesided=False, detrend=False)
    return F, P


def plot_spectrum(F, P, title, output_pdf, file_name, resolution_khz):
    """绘制频谱图，只显示DC附近2MHz范围"""
    # 转换为dB
    P_dB = 10 * np.log10(np.abs(P))

    # 找到DC附近±1MHz的频率索引
    freq_min = -1.0  # MHz
    freq_max = 1.0   # MHz
    freq_mask = (F >= freq_min) & (F <= freq_max)

    # 绘制频谱图
    fig = plt.figure(figsize=(10, 6))
    plt.plot(F[freq_mask], P_dB[freq_mask], 'b-', linewidth=1)

    plt.title(f"{file_name}\nFrequency Range: DC ± 1 MHz (Resolution: {resolution_khz} kHz)", fontsize=12)
    plt.xlabel('Frequency (MHz)', fontsize=11)
    plt.ylabel('Power Density (dB)', fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.xlim(freq_min, freq_max)

    # 自动调整y轴范围以显示所有信号
    visible_P = P_dB[freq_mask]
    if len(visible_P) > 0:
        y_min = np.min(visible_P) - 5
        y_max = np.max(visible_P) + 5
        plt.ylim(y_min, y_max)

    output_pdf.savefig(fig)
    plt.close(fig)


def plot_time_domain(data, title, output_pdf):
    """绘制时域波形图"""
    fig = plt.figure(figsize=(10, 4))
    plt.plot(np.real(data), 'b-', label='I (Real)', linewidth=0.5)
    plt.plot(np.imag(data), 'r-', label='Q (Imaginary)', linewidth=0.5)
    plt.title(title, fontsize=12)
    plt.xlabel('Time Sample', fontsize=11)
    plt.ylabel('Magnitude', fontsize=11)
    plt.legend()
    plt.grid(True, alpha=0.3)
    output_pdf.savefig(fig)
    plt.close(fig)


def main(resolution_khz=1):
    # 配置参数
    # 重要参数说明：
    # 频率分辨率 = Fs / NFFT
    # 分辨率可配置：1kHz、5kHz、10kHz等
    FS = 160e6         # 采样率：160 MHz (与原代码保持一致)

    # 根据分辨率计算FFT长度
    resolution_hz = resolution_khz * 1000
    NFFT = int(FS / resolution_hz)  # FFT长度：根据分辨率计算
    OVERLAP = NFFT // 2 # 重叠长度：50%重叠
    WINDOW = np.hanning(NFFT) # Hanning窗口

    print(f"Configuration: Resolution = {resolution_khz} kHz, FFT length = {NFFT} points")
    print(f"Frequency resolution: {FS/NFFT/1000:.1f} kHz")

    # 工作目录设置
    os.chdir(r'D:/users/gxu/spur_scan/260228/dump')
    mypath = os.getcwd()
    print(f"Working directory: {mypath}")

    # 查找CSV文件
    my_files = glob.glob('*.csv')
    if not my_files:
        print("No CSV files found in the current directory.")
        return

    # 输出目录
    output_path = os.path.join(mypath, 'pdf')
    os.makedirs(output_path, exist_ok=True)

    print(f"Found {len(my_files)} CSV files")

    for m in range(len(my_files)):
        file_name = my_files[m]
        print(f"Processing: {file_name}")

        # 提取文件名中的参数
        pattern = re.compile(r"(?:phy_mode(\d+))|(?:chan(\d+))", re.IGNORECASE)
        matches = pattern.findall(file_name)
        phy_mode_val = None
        chan_val = None
        for name in matches:
            if name[0]:
                phy_mode_val = int(name[0])
            if name[1]:
                chan_val = int(name[1])

        # 读取CSV文件中的IQ数据
        data = []
        with open(file_name, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    # 尝试读取不同格式的IQ数据列
                    if 'sample_i_ch0' in row and 'sample_q_ch0' in row:
                        x = float(row['sample_i_ch0'])
                        y = float(row['sample_q_ch0'])
                    elif ' idata_ch0' in row and ' qdata_ch0 ' in row:
                        x = float(row[' idata_ch0'])
                        y = float(row[' qdata_ch0 '])
                    elif 'chip_top_inst/u_fpga_host_inf/host_mux_top_ch0/u_host_data_mux/rx_i_fe_fpga[9:0]' in row:
                        x = float(row['chip_top_inst/u_fpga_host_inf/host_mux_top_ch0/u_host_data_mux/rx_i_fe_fpga[9:0]'])
                        y = float(row['chip_top_inst/u_fpga_host_inf/host_mux_top_ch0/u_host_data_mux/rx_q_fe_fpga[9:0]'])
                    else:
                        # 如果以上列名均不匹配，使用第一个和第二个列
                        keylist = list(row.keys())
                        if len(keylist) >= 2:
                            x = float(row[keylist[0]])
                            y = float(row[keylist[1]])
                        else:
                            continue

                    data.append(complex(x, y))
                except Exception as e:
                    print(f"Error reading row: {e}")
                    continue

        if not data:
            print(f"Warning: No valid IQ data found in {file_name}")
            continue

        # 创建PDF文件
        pdf_filename = os.path.join(output_path, f"{os.path.splitext(file_name)[0]}.pdf")
        pp = PdfPages(pdf_filename)

        # 绘制时域波形图
        plot_time_domain(data, f"{file_name} - Time Domain", pp)

        # 计算功率谱密度
        [F, P] = calculate_psd(data, FS, NFFT, WINDOW, OVERLAP)

        # 绘制频谱图(DC±1MHz范围)
        plot_spectrum(F, P, f"{file_name} - Frequency Domain", pp, file_name, resolution_khz)

        pp.close()
        print(f"Results saved to: {pdf_filename}")

    print("Processing completed!")


if __name__ == "__main__":
    # 可配置分辨率：1, 5, 10 kHz
    # 如果1kHz分辨率数据量太大，可以尝试5kHz或10kHz
    resolution = 5  # 可修改为 1, 5, 10
    main(resolution_khz=resolution)
