import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import os
import glob
import csv
from scipy.signal import welch
from scipy.signal.windows import hann
import re


def read_spur_config(config_file):
    """
    读取杂散配置CSV文件，获取phy_mode、channel、Used_Frequency信息

    参数:
        config_file: 配置文件路径

    返回:
        配置字典，键为(phy_mode, channel)，值为Used_Frequency的列表
    """
    spur_config = {}
    with open(config_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            phy_mode = int(row['phy_mode'])
            channel = int(row['channel'])
            used_freq = row['Used_Frequency']

            # 跳过无效或no_spur的配置
            if used_freq != 'invalid' and used_freq != "['no_spur']":
                try:
                    # 尝试将字符串转换为数值
                    used_freq = float(used_freq)
                    # 同一phy_mode和channel配置下可能有多个Used_Frequency，使用列表存储
                    if (phy_mode, channel) not in spur_config:
                        spur_config[(phy_mode, channel)] = []
                    spur_config[(phy_mode, channel)].append(used_freq)
                except ValueError:
                    continue
    return spur_config


def update_config_file(config_file, config_updates):
    """
    更新配置文件的pwr列

    参数:
        config_file: 配置文件路径
        config_updates: 要更新的配置信息字典，键为(phy_mode, channel, Used_Frequency)，值为pwr值
    """
    # 读取所有配置行
    config_rows = []
    fieldnames = None

    with open(config_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames
        for row in reader:
            config_rows.append(row)

    # 更新配置行的pwr列
    updated_count = 0
    for row in config_rows:
        try:
            phy_mode = int(row['phy_mode'])
            channel = int(row['channel'])
            used_freq = row['Used_Frequency']

            if used_freq != 'invalid' and used_freq != "['no_spur']":
                used_freq = float(used_freq)
                # 检查是否有对应的更新值
                config_key = (phy_mode, channel, used_freq)
                if config_key in config_updates:
                    new_pwr = config_updates[config_key]
                    row['pwr'] = str(new_pwr)
                    updated_count += 1
                    print(f"更新配置: phy_mode={phy_mode}, channel={channel}, Used_Frequency={used_freq}, pwr={new_pwr:.6f}")
        except Exception as e:
            print(f"处理配置行时出错: {e}")
            continue

    # 将更新后的配置写回文件
    backup_file = config_file + '.bak'
    os.replace(config_file, backup_file)
    print(f"已创建备份文件: {backup_file}")

    with open(config_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(config_rows)

    print(f"配置文件更新完成，共更新 {updated_count} 行")


def read_data_from_csv(file_path, i_col, q_col):
    """
    从CSV文件中读取指定列的I和Q数据，并转换为复数格式

    参数:
        file_path: CSV文件路径
        i_col: I信号列名
        q_col: Q信号列名

    返回:
        复数格式的数据数组
    """
    data = []
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            x = float(row[i_col])/(2**12)
            y = float(row[q_col])/(2**12)
            data.append(complex(x, y))
    return np.array(data)


def plot_time_domain(data, file_name, figure):
    """
    绘制时域I和Q信号图

    参数:
        data: 复数数据数组
        file_name: 文件名（用于标题）
        figure: 图形对象
    """
    plt.figure(figure)
    plt.plot(np.real(data), 'o-', label='I信号')
    plt.plot(np.imag(data), 'rs-', label='Q信号')
    plt.ylabel('幅度')
    plt.xlabel('时间采样点')
    plt.title(f'{file_name} - 时域信号')
    plt.legend()
    plt.grid()


def plot_freq_domain(freqAxis, Pxx_den, file_name, figure):
    """
    绘制频域功率谱密度图

    参数:
        freqAxis: 频率轴
        Pxx_den: 功率谱密度
        file_name: 文件名（用于标题）
        figure: 图形对象
    """
    plt.figure(figure)
    plt.plot(freqAxis, 10 * np.log10(np.abs(Pxx_den)), 'b-')
    plt.title(f'{file_name} - 功率谱密度')
    plt.xlabel('频率 (MHz)')
    plt.ylabel('功率密度 (dB)')
    plt.grid()


def calc_pow_for_ofdm_signal(dataIn, Fs, NFFT, rfGain, spurPos=None):
    """
    计算OFDM信号的时域功率、频域功率及杂散功率（对应MATLAB脚本功能）

    参数:
        dataIn: 输入时域信号 (numpy array)
        Fs: 采样频率 (单位与spurPos一致，如MHz)
        NFFT: FFT点数
        rfGain: 射频增益 (dB)
        spurPos: 目标杂散频率位置 (可选，与Fs同单位)

    返回:
        包含各功率值、频率轴等结果的字典
    """
    # 1. 计算功率谱密度 (PSD) - 对应MATLAB pwelch
    # return_onesided=False 对应'twosided'，返回双边谱

    f, Pxx_den = welch(
        dataIn,
        fs=Fs,
        window=hann(NFFT),
        noverlap=NFFT // 2,  # MATLAB默认noverlap为窗长50%
        nfft=NFFT,
        return_onesided=False,
        scaling='density'  # 输出功率谱密度(W/Hz)
    )

    # 频率轴中心化 - 对应MATLAB freqAxis = F - Fs/2
    freqAxis = f - Fs / 2

    # 频率分辨率 (与Fs同单位，如MHz)
    freqResolution = Fs / NFFT

    # 2. 时域功率计算 (dBm)
    # 公式: 10*log10(平均功率) - 增益补偿
    timeDomainPower = 10 * np.log10(np.mean(np.abs(dataIn) ** 2)) - rfGain / 2

    # 3. 频域功率计算 (dBm) - 积分PSD
    # 公式: 10*log10(PSD积分) - 增益补偿
    freqDomainPower = 10 * np.log10(np.sum(Pxx_den * freqResolution)) - rfGain / 2

    # 4. 杂散检测 - 方式1: 找最大谱线
    PmaxOfSpur = np.max(Pxx_den)
    idxSpur = np.argmax(Pxx_den)
    spurPower_max = 10 * np.log10(PmaxOfSpur * freqResolution) - rfGain / 2
    spurFreqMHz_max = freqAxis[idxSpur] + Fs / 2

    print(f"Debug info (max spur): idx={idxSpur}, freqAxis[idx]={freqAxis[idxSpur]:.3f} MHz, f[idx]={f[idxSpur]:.3f} MHz, Pxx_den[idx]={Pxx_den[idxSpur]:.6e}, power={spurPower_max:.2f} dBm")

    # 5. 杂散检测 - 方式2: 根据指定spurPos计算 (可选)
    spurPower_pos = None
    spurFreqMHz_pos = None
    if spurPos is not None:
        print(f"\nDebug info (target spur): spurPos={spurPos:.3f} MHz")

        # 找到最接近指定spurPos的频率索引（直接在原始f频率轴上匹配）
        freq_diff = np.abs(f - spurPos)
        spurPosIdx = np.argmin(freq_diff)

        print(f"Found idx={spurPosIdx}, freqAxis[idx]={freqAxis[spurPosIdx]:.3f} MHz, f[idx]={f[spurPosIdx]:.3f} MHz, Pxx_den[idx]={Pxx_den[spurPosIdx]:.6e}")

        spurPower_pos = 10 * np.log10(Pxx_den[spurPosIdx] * freqResolution) - rfGain / 2
        spurFreqMHz_pos = f[spurPosIdx]  # 直接使用f轴的频率，与方式1的结果保持一致

    # 返回结果字典
    return {
        "timeDomainPower_dBm": timeDomainPower,
        "freqDomainPower_dBm": freqDomainPower,
        "spurPower_max_dBm": spurPower_max,
        "spurFreqMHz_max": spurFreqMHz_max,
        "spurPower_pos_dBm": spurPower_pos,
        "spurFreqMHz_pos": spurFreqMHz_pos,
        "freqAxis": freqAxis,
        "freq":f,
        "Pxx_den": Pxx_den,
        "freqResolution": freqResolution
    }


def process_directory(directory, i_col, q_col, Fs, NFFT, rfGain, spur_config, config_file, output_dir='output'):
    """
    处理指定目录下的所有CSV文件，检索包含phy_mode%d_chan%d模式的文件，
    提取phy_mode和chan值，并根据spur_config计算指定频率位置的杂散功率，
    最后将结果写入到一个合并的CSV文件中，并更新配置文件的pwr列。

    参数:
        directory: 要处理的目录
        i_col: CSV文件中I信号列名
        q_col: CSV文件中Q信号列名
        Fs: 采样频率 (MHz)
        NFFT: FFT点数
        rfGain: 射频增益 (dB)
        spur_config: 杂散配置字典，键为(phy_mode, channel)，值为Used_Frequency
        config_file: 配置文件路径（用于更新pwr列）
        output_dir: 输出文件目录
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 定义正则表达式模式以匹配包含phy_mode%d_chan%d的文件名
    pattern = re.compile(r'phy_mode(\d+)_chan(\d+)')

    # 收集所有符合条件的CSV文件
    csv_files = []
    # 递归搜索目录
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.csv') and pattern.search(file):
                csv_files.append(os.path.join(root, file))

    # 收集计算结果
    results = []
    # 用于存储要更新的配置信息
    config_updates = {}

    for csv_file in csv_files:
        file_name = os.path.basename(csv_file)
        print(f"正在处理文件: {file_name}")

        # 提取phy_mode和chan值
        match = pattern.search(file_name)
        if match:
            phy_mode = int(match.group(1))
            chan = int(match.group(2))
        else:
            print(f"  警告: 文件 {file_name} 不符合phy_mode%d_chan%d模式，跳过")
            continue

        # 读取数据
        dataIn = read_data_from_csv(csv_file, i_col, q_col)

        # 检查是否有对应的杂散频率配置
        used_freqs = []
        if (phy_mode, chan) in spur_config:
            used_freqs = spur_config[(phy_mode, chan)]
            print(f"  配置的杂散频率位置: {used_freqs} MHz")

        # 计算功率（不指定spurPos的基础计算）
        result = calc_pow_for_ofdm_signal(dataIn, Fs, NFFT, rfGain, spurPos=None)

        # 临时禁用绘图功能以避免权限问题
        plt.close('all')
        plot_time_domain(dataIn, file_name, 1)
        plot_freq_domain(result["freq"], result["Pxx_den"], file_name, 2)

        # 保存图片到PDF文件
        pdf_path = os.path.join(output_dir, f'{os.path.splitext(file_name)[0]}.pdf')
        pp = PdfPages(pdf_path)
        pp.savefig(1)
        pp.savefig(2)
        pp.close()

        # 收集基础结果（包含max spur信息）
        base_result_entry = {
            'phy_mode': phy_mode,
            'chan': chan,
            'timeDomainPower_dBm': result['timeDomainPower_dBm'],
            'freqDomainPower_dBm': result['freqDomainPower_dBm'],
            'spurPower_max_dBm': result['spurPower_max_dBm'],
            'spurFreqMHz_max': result['spurFreqMHz_max']
        }

        #如果有配置的Used_Frequency，为每个频率创建单独的结果行
        if len(used_freqs) > 0:
            for used_freq in used_freqs:
                # 针对每个Used_Frequency重新计算杂散功率
                pos_result = calc_pow_for_ofdm_signal(dataIn, Fs, NFFT, rfGain, spurPos=used_freq)

                # 创建新的结果条目，包含基础信息和该频率的杂散功率
                result_entry = base_result_entry.copy()
                result_entry['Used_Frequency'] = used_freq
                result_entry['spurPower_pos_dBm'] = pos_result['spurPower_pos_dBm']
                results.append(result_entry)

                # 保存要更新的配置信息
                config_key = (phy_mode, chan, used_freq)
                config_updates[config_key] = pos_result['spurPower_pos_dBm']
        else:
            # 如果没有配置Used_Frequency，只添加基础结果
            results.append(base_result_entry)

        # 打印结果
        print(f"  时域功率 (dBm): {result['timeDomainPower_dBm']:.2f}")
        print(f"  频域功率 (dBm): {result['freqDomainPower_dBm']:.2f}")
        print(f"  最大杂散功率 (dBm): {result['spurPower_max_dBm']:.2f}")
        print(f"  最大杂散频率 (MHz): {result['spurFreqMHz_max']:.2f}")
        print()

    # 将所有结果写入到一个CSV文件中
    output_csv_path = os.path.join(output_dir, 'phy_mode_chan_power_results.csv')
    if results:
        df = pd.DataFrame(results)
        # 按phy_mode和chan排序
        df = df.sort_values(by=['phy_mode', 'chan'])
        # 保存到CSV文件
        df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
        print(f"所有结果已保存到: {output_csv_path}")
    else:
        print("未找到符合条件的CSV文件")

    # 更新配置文件的pwr列
    update_config_file(config_file, config_updates)


# ---------------------- 测试示例 ----------------------
if __name__ == "__main__":
    # 配置参数
    directory = r'D:\users\gxu\spur_scan\260309\scan_spur_data\xtal_duty_disable\loop_num5\20m'  # 数据文件目录
    i_col = ' sample i_ch0'  # I信号列名
    q_col = ' sample q_ch0'  # Q信号列名
    Fs = 80  # 采样频率 (MHz)
    NFFT = 8000  # FFT点数
    rfGain = 98  # 射频增益 (dB)
    output_dir = r'D:\users\gxu\spur_scan\260309\scan_spur_data\xtal_duty_disable\loop_num5\20m'  # 输出目录
    config_file = r"D:\users\gxu\spur_scan\260309\scan_spur_data\normal\loop_num3\20m\result\spur_scan_result_coef.csv"  # 配置文件路径

    # 读取杂散配置
    spur_config = read_spur_config(config_file)
    print(f"成功读取 {len(spur_config)} 个有效杂散配置")

    # 处理目录下的所有CSV文件
    process_directory(directory, i_col, q_col, Fs, NFFT, rfGain, spur_config, config_file, output_dir)

    print("处理完成！")