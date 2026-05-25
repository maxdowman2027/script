#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整合仓库根目录下 `psd_plot.py`、`notch_cal.py`（算法同源，本文件内嵌）与 `clac_pwr_for_ofdm_signal.py` 的思路与能力。
1. 处理CSV文件，计算PSD，检测杂散并输出spur_scan_result.csv（含非DC相对40M倍频功率检查）
2. 读取spur_scan_result.csv并计算系数，输出spur_scan_result_coef.csv
3. 计算指定位置的功率并写回spur_scan_result_coef.csv
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import os
import glob
import csv
import re
from scipy.signal import welch
from scipy.signal.windows import hann
import ast
import math
from typing import List


# ===================== 1. 全局配置类（来自notch_cal.py） =====================
class RX_TIME_CTRL:
    """输入信号定点化配置"""
    def __init__(self):
        self.syncDfeFixedBits = 12    # 输入信号总比特数
        self.syncDfeFixedClip = 0.5   # 输入信号截位值

class SINGLE_TONE_SPUR_CTRL:
    """陷波滤波器系数定点化配置"""
    def __init__(self):
        self.notchCoefFixedBitsA = 16   # Y_Coef(a系数)总比特数
        self.notchCoefFixedClipA = 4  # Y_Coef截位值
        self.notchCoefFixedBitsB = 12   # X_Coef(b系数)总比特数
        self.notchCoefFixedClipB = 4  # X_Coef截位值

class GSetting:
    """全局配置类"""
    def __init__(self):
        self.RX_TIME_CTRL = RX_TIME_CTRL()
        self.SINGLE_TONE_SPUR_CTRL = SINGLE_TONE_SPUR_CTRL()

# 全局配置实例
gSetting = GSetting()

# ===================== 2. 常量定义 =====================
SYMMETRIC = 1    # 对称量化模式
ASYMMETRIC = 0   # 非对称量化模式


# ===================== 3. IIR滤波器类（来自notch_cal.py） =====================
class IIR_FILTER_CLASS:
    def __init__(self):
        """类初始化：初始化所有成员变量"""
        # 基础状态标记
        self.initFlag = 0               # 滤波器初始化标记（0=未初始化，1=已初始化）
        self.iirNotchFixedSettingFlag = 0  # 定点化配置标记

        # 滤波器核心参数
        self.TapsNum = 0                # 滤波器阶数（抽头数）
        self.X_Coef = []                # 浮点分子系数（b系数，归一化后）
        self.Y_Coef = []                # 浮点分母系数（a系数，归一化后）
        self.Reg = []                   # 延迟寄存器（复数类型）

        # 定点化相关参数
        self.inputBits = 0              # 输入信号总比特数
        self.inputClip = 0.0            # 输入信号截位值
        self.coefBitsA = 0              # Y_Coef总比特数
        self.coefBitsClipA = 0.0        # Y_Coef截位值
        self.coefFractionBitsA = 0      # Y_Coef小数部分比特数
        self.coefBitsB = 0              # X_Coef总比特数
        self.coefBitsClipB = 0.0        # X_Coef截位值
        self.coefFractionBitsB = 0      # X_Coef小数部分比特数
        self.X_CoefFixed = []           # 定点整数分子系数
        self.Y_CoefFixed = []           # 定点整数分母系数

    # -------------------- 辅助函数：内存管理 --------------------
    def freeMemory(self):
        """释放内存（Python靠垃圾回收，仅清空列表）"""
        self.X_Coef.clear()
        self.Y_Coef.clear()
        self.Reg.clear()
        self.X_CoefFixed.clear()
        self.Y_CoefFixed.clear()
        self.TapsNum = 0
        self.initFlag = 0

    # -------------------- 辅助函数：寄存器初始化 --------------------
    def initial(self):
        """初始化延迟寄存器（置零）"""
        self.Reg = [complex(0.0, 0.0) for _ in range(self.TapsNum)]

    # -------------------- 辅助函数：浮点数转定点整数 --------------------
    def float2FixedIntOut(self, data: float, clipping: float, Bits: int, symmetryFlag: int) -> int:
        # 防止除零错误
        if clipping == 0:
            raise ValueError("clipping不能为0，会导致除零错误")

        # 1. 计算定点数最大值：max = 2^(Bits-1)
        max_val = 1 << (Bits - 1)

        # 2. 缩放：将浮点数映射到定点数范围
        temp = (data / clipping) * max_val

        # 3. 四舍五入取整（正数+0.5，负数-0.5）
        if temp >= 0:
            temp = int(temp + 0.5)
        else:
            temp = int(temp - 0.5)

        # 4. 限幅（防止定点数溢出）
        if symmetryFlag == SYMMETRIC:
            # 对称模式：[-max_val+1, max_val-1]
            if temp > max_val - 1:
                temp = max_val - 1
            elif temp < -(max_val - 1):
                temp = -(max_val - 1)
        else:
            # 非对称模式：[-max_val, max_val-1]
            if temp > max_val - 1:
                temp = max_val - 1
            elif temp < -max_val:
                temp = -max_val

        return int(temp)

    def iir_notch_coef(self, f0, Q, fs):
        b = [0.0] * 3
        a = [0.0] * 3

        if f0 != 0:
            w0 = 2.0 * math.pi * f0 / fs
            attenuate = 0.707
            alpha = math.tan(w0 / Q / 2.0) * math.sqrt(1 - attenuate**2) / attenuate

            b[0] = 1.0
            b[1] = -2.0 * math.cos(w0)
            b[2] = 1.0

            a[0] = 1 + alpha
            a[1] = -2.0 * math.cos(w0)
            a[2] = 1 - alpha
        else:
            rou = 0.965
            b[0] = 1.0
            b[1] = -2.0
            b[2] = 1.0
            a[0] = 1.0
            a[1] = -2 * rou
            a[2] = rou * rou

        return b, a

    # -------------------- 核心功能2：系数归一化 --------------------
    def setCoef(self, B, A, order):
        if self.initFlag == 1:
            self.freeMemory()

        # 标记为已初始化
        self.initFlag = 1
        self.TapsNum = order

        # 拷贝系数到成员变量
        self.X_Coef = [0.0] * (self.TapsNum + 1)
        self.Y_Coef = [0.0] * (self.TapsNum + 1)
        for i in range(self.TapsNum + 1):
            self.X_Coef[i] = B[i]
            self.Y_Coef[i] = A[i]

        # 分母系数归一化（确保Y_Coef[0] = 1.0，增加浮点精度容错）
        if not abs(self.Y_Coef[0] - 1.0) < 1e-9:
            for i in range(self.TapsNum, -1, -1):
                self.X_Coef[i] /= self.Y_Coef[0]
                self.Y_Coef[i] /= self.Y_Coef[0]

        # 初始化延迟寄存器
        self.initial()
        # 重置定点化标记
        self.iirNotchFixedSettingFlag = 0

    # -------------------- 核心功能3：系数定点化 --------------------
    def setCoefFixed(self):
        """
        将归一化后的浮点系数转换为定点整数系数
        """
        # 标记定点化配置开始
        self.iirNotchFixedSettingFlag = 1

        # 读取输入信号定点化参数（预留）
        self.inputBits = gSetting.RX_TIME_CTRL.syncDfeFixedBits
        self.inputClip = gSetting.RX_TIME_CTRL.syncDfeFixedClip

        # 处理Y_Coef(a系数)的定点化参数
        self.coefBitsA = gSetting.SINGLE_TONE_SPUR_CTRL.notchCoefFixedBitsA
        self.coefBitsClipA = gSetting.SINGLE_TONE_SPUR_CTRL.notchCoefFixedClipA
        int_bits_A = int(math.log10(self.coefBitsClipA) / math.log10(2.0) + 0.5)
        self.coefFractionBitsA = self.coefBitsA - int_bits_A - 1

        # 处理X_Coef(b系数)的定点化参数（修正所有Bug）
        self.coefBitsB = gSetting.SINGLE_TONE_SPUR_CTRL.notchCoefFixedBitsB
        self.coefBitsClipB = gSetting.SINGLE_TONE_SPUR_CTRL.notchCoefFixedClipB
        int_bits_B = int(math.log10(self.coefBitsClipB) / math.log10(2.0) + 0.5)
        self.coefFractionBitsB = self.coefBitsB - int_bits_B - 1

        # 初始化定点系数数组
        self.X_CoefFixed = [0] * (self.TapsNum + 1)
        self.Y_CoefFixed = [0] * (self.TapsNum + 1)

        # 浮点系数转定点整数
        for i in range(self.TapsNum + 1):
            self.X_CoefFixed[i] = self.float2FixedIntOut(
                self.X_Coef[i], self.coefBitsClipB, self.coefBitsB, SYMMETRIC
            )
            self.Y_CoefFixed[i] = self.float2FixedIntOut(
                self.Y_Coef[i], self.coefBitsClipA, self.coefBitsA, SYMMETRIC
            )
        return str(self.X_CoefFixed), str(self.Y_CoefFixed)


# ===================== 4. PSD分析和杂散检测函数（来自psd_plot.py） =====================
DC_MARGIN_MHZ = 0.1  # |F| <= 该值视为 DC/中心频点邻域


def is_dc_bin(f_mhz: float, dc_margin: float = DC_MARGIN_MHZ) -> bool:
    return abs(f_mhz) <= dc_margin


def is_40m_harmonic_bin(chan_val: int, f_mhz: float) -> bool:
    """40 MHz 栅格倍频点判定（与杂散筛选规则一致）。"""
    if chan_val > 14:
        return (chan_val + f_mhz) % 40 == 0
    if chan_val == 14:
        return (2484 + f_mhz) % 40 == 0
    return (2412 + 5 * (chan_val - 1) + f_mhz) % 40 == 0


def psd_bin_power_db(p_value) -> float:
    return float(10 * np.log10(np.abs(p_value)))


def find_non_harmonic_above_40m_harmonic(
    chan_val: int,
    F,
    P,
    *,
    spur_thr: float = 18,
    dc_margin: float = DC_MARGIN_MHZ,
) -> dict:
    """
    检查是否存在：非 DC 且非 40M 倍频栅格点，其 PSD 功率高于所有 40M 倍频点中的最大功率。

    仅统计功率 > spur_thr 的非倍频点，避免噪声底误报。
    """
    harm_pwr_db: List[float] = []
    for i in range(len(F)):
        if is_dc_bin(F[i], dc_margin):
            continue
        if is_40m_harmonic_bin(chan_val, F[i]):
            harm_pwr_db.append(psd_bin_power_db(P[i]))

    if not harm_pwr_db:
        return {
            "harm_40m_ref_pwr_db": "",
            "non_harm_above_40m_freq": ["no_40m_ref"],
            "non_harm_above_40m_pwr": ["no_40m_ref"],
            "non_harm_above_40m_diff": ["no_40m_ref"],
            "has_non_harm_above_40m": "no_40m_ref",
        }

    ref_pwr = max(harm_pwr_db)
    freqs: List[float] = []
    pwrs: List[float] = []
    diffs: List[float] = []
    for i in range(len(F)):
        if is_dc_bin(F[i], dc_margin):
            continue
        if is_40m_harmonic_bin(chan_val, F[i]):
            continue
        p_db = psd_bin_power_db(P[i])
        if p_db <= spur_thr or p_db <= ref_pwr:
            continue
        freqs.append(round(float(F[i]), 4))
        pwrs.append(round(p_db, 2))
        diffs.append(round(p_db - ref_pwr, 2))

    return {
        "harm_40m_ref_pwr_db": round(ref_pwr, 2),
        "non_harm_above_40m_freq": freqs if freqs else ["none"],
        "non_harm_above_40m_pwr": pwrs if pwrs else ["none"],
        "non_harm_above_40m_diff": diffs if diffs else ["none"],
        "has_non_harm_above_40m": "yes" if freqs else "no",
    }


def _safe_plot_basename(file_path: str) -> str:
    name = os.path.splitext(os.path.basename(file_path))[0]
    return re.sub(r"[^\w\-.]+", "_", name)[:120]


def save_spectrum_plots_pdf(
    file_path: str,
    data,
    F,
    P,
    spur_frequencies,
    plot_dir: str,
    *,
    spur_thr: float = 18,
    anomaly_frequencies=None,
) -> str:
    """
    Save IQ time-domain and PSD spectrum plots (same style as psd_plot.py) to a PDF.
    Detected spur frequencies are marked on the PSD figure.
    """
    os.makedirs(plot_dir, exist_ok=True)
    pdf_path = os.path.join(plot_dir, f"{_safe_plot_basename(file_path)}.pdf")

    plt.close("all")
    fig_iq = plt.figure(figsize=(10, 4))
    plt.plot(np.real(data), "o-", markersize=2, label="I")
    plt.plot(np.imag(data), "rs-", markersize=2, label="Q")
    plt.ylabel("magnitude")
    plt.xlabel("time sample")
    plt.title(os.path.basename(file_path))
    plt.grid(True)
    plt.legend(loc="best", fontsize=8)

    F_shift = np.fft.fftshift(F)
    P_db = 10 * np.log10(np.abs(np.fft.fftshift(P)))
    fig_psd = plt.figure(figsize=(10, 4))
    plt.plot(F_shift, P_db, "b-", linewidth=0.8, label="PSD")
    plt.axhline(
        spur_thr,
        color="gray",
        linestyle="--",
        linewidth=1,
        label=f"thr {spur_thr} dB",
    )
    spur_mhz = []
    for sf in spur_frequencies:
        if isinstance(sf, str) and sf.strip().lower() == "no_spur":
            continue
        try:
            spur_mhz.append(float(sf))
        except (TypeError, ValueError):
            continue
    for sf in spur_mhz:
        idx = int(np.argmin(np.abs(F - sf)))
        idx_s = int(np.argmin(np.abs(F_shift - F[idx])))
        plt.plot(
            F_shift[idx_s],
            P_db[idx_s],
            "ro",
            markersize=8,
            label="spur" if sf == spur_mhz[0] else None,
        )
    plt.title(os.path.basename(file_path))
    plt.xlabel("Freq (MHz)")
    plt.ylabel("power density (dB)")
    plt.grid(True)
    anomaly_mhz = []
    if anomaly_frequencies:
        for af in anomaly_frequencies:
            if isinstance(af, str) and af.strip().lower() in ("none", "no_40m_ref", "no_spur"):
                continue
            try:
                anomaly_mhz.append(float(af))
            except (TypeError, ValueError):
                continue
    for af in anomaly_mhz:
        idx = int(np.argmin(np.abs(F - af)))
        idx_s = int(np.argmin(np.abs(F_shift - F[idx])))
        plt.plot(
            F_shift[idx_s],
            P_db[idx_s],
            "^",
            color="orange",
            markersize=9,
            label=">40M harm" if af == anomaly_mhz[0] else None,
        )
    if spur_mhz or anomaly_mhz:
        plt.legend(loc="best", fontsize=8)

    with PdfPages(pdf_path) as pdf:
        pdf.savefig(fig_iq, bbox_inches="tight")
        pdf.savefig(fig_psd, bbox_inches="tight")
    plt.close(fig_iq)
    plt.close(fig_psd)
    return pdf_path


def detect_spurs_from_csv(
    input_dir,
    output_dir,
    FS,
    SPUR_THR=18,
    *,
    spectrum_plot_dir=None,
    dc_margin: float = DC_MARGIN_MHZ,
):
    """
    处理目录下的CSV文件，计算PSD，检测杂散并输出spur_scan_result.csv。

    spectrum_plot_dir: 若指定，将每个文件的 IQ/PSD 图保存为 PDF（与 psd_plot.py 一致）。
    同时检查非 DC 频点是否存在功率高于 40M 倍频栅格参考（见 harm_40m_* / has_non_harm_above_40m 列）。
    """
    os.makedirs(output_dir, exist_ok=True)
    csv_file_path = os.path.join(output_dir, "spur_scan_result.csv")

    csv_header = [
        "phy_mode",
        "channel",
        "frequency",
        "diff_pwr",
        "pwr",
        "harm_40m_ref_pwr_db",
        "non_harm_above_40m_freq",
        "non_harm_above_40m_pwr",
        "non_harm_above_40m_diff",
        "has_non_harm_above_40m",
    ]

    # 清空并创建输出文件
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_header)
        writer.writeheader()

    my_files = glob.glob(os.path.join(input_dir, '*.csv'))
    saved_plots: List[str] = []

    for m in range(len(my_files)):
        file_name = my_files[m]
        basename = os.path.basename(file_name)

        pattern = re.compile(r"(?:phy_mode(\d+))|(?:chan(\d+))", re.IGNORECASE)
        matches = pattern.findall(basename)
        phy_mode_val = None
        chan_val = None

        for name in matches:
            if name[0]:
                phy_mode_val = int(name[0])
            if name[1]:
                chan_val = int(name[1])

        if phy_mode_val is None or chan_val is None:
            print(f"无法提取phy_mode或chan值，跳过文件: {basename}")
            continue

        print(f"phymode{phy_mode_val}-chan{chan_val}")

        # 读取CSV文件
        data = []
        with open(file_name, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                x = float(row[' sample i_ch0'])
                y = float(row[' sample q_ch0'])
                data.append(complex(x, y))

        # 计算PSD
        NFFT = 16000
        overlap = NFFT / 2
        win = np.hanning(NFFT)
        [F, P] = welch(data, FS, win, noverlap=overlap, nfft=NFFT, return_onesided=False, detrend=False)

        # 检测杂散
        result_indices = []
        for idx, value in enumerate(P):
            if (10 * np.log10(np.abs((value)))) > SPUR_THR:
                result_indices.append(idx)

        # 找到1MHz和-1MHz位置的功率用于平均
        result_indices_f = []
        for fi, fv in enumerate(F):
            if np.abs(fv) == 1.0:
                result_indices_f.append(fi)

        if len(result_indices_f) >= 2:
            avg_pwr = ((10 * np.log10(np.abs((P[result_indices_f[0]])))) + (10 * np.log10(np.abs((P[result_indices_f[1]]))))) / 2
        else:
            avg_pwr = 0

        print(f"avg_pwr is {avg_pwr}")

        SPUR_F = []
        diff_pwr = []
        pwr = []

        for i in result_indices:
            if not is_dc_bin(F[i], dc_margin):
                if is_40m_harmonic_bin(chan_val, F[i]):
                    SPUR_F.append(F[i])
                    diff_pwr.append(round((psd_bin_power_db(P[i]) - avg_pwr), 2))
                    pwr.append(round((psd_bin_power_db(P[i]) - 58), 2))

        # 处理无杂散情况
        if len(SPUR_F) == 0:
            SPUR_F.append("no_spur")
            diff_pwr.append('no_spur')
            pwr.append('no_spur')

        harm_check = find_non_harmonic_above_40m_harmonic(
            chan_val, F, P, spur_thr=SPUR_THR, dc_margin=dc_margin
        )
        if harm_check["has_non_harm_above_40m"] == "yes":
            print(
                f"[WARN] 非40M倍频且高于倍频参考: phy_mode={phy_mode_val} chan={chan_val} "
                f"ref={harm_check['harm_40m_ref_pwr_db']} dB "
                f"freq={harm_check['non_harm_above_40m_freq']}"
            )

        # 写入结果
        param_dict = {
            "phy_mode": phy_mode_val,
            "channel": chan_val,
            "frequency": SPUR_F,
            "diff_pwr": diff_pwr,
            "pwr": pwr,
            **harm_check,
        }

        with open(csv_file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=csv_header)
            writer.writerow(param_dict)

        if spectrum_plot_dir:
            try:
                anomaly_freqs = harm_check.get("non_harm_above_40m_freq")
                pdf_path = save_spectrum_plots_pdf(
                    file_name,
                    data,
                    F,
                    P,
                    SPUR_F,
                    spectrum_plot_dir,
                    spur_thr=SPUR_THR,
                    anomaly_frequencies=anomaly_freqs,
                )
                saved_plots.append(pdf_path)
            except Exception as ex:
                print(f"[WARN] 频谱图保存失败 {basename}: {ex}")

    print(f"杂散检测完成，结果已保存到: {csv_file_path}")
    if spectrum_plot_dir and saved_plots:
        print(
            f"频谱图已保存 {len(saved_plots)} 个 PDF 至: "
            f"{os.path.abspath(spectrum_plot_dir)}"
        )
    return csv_file_path


# ===================== 5. 系数计算函数（来自notch_cal.py） =====================
def calculate_notch_coefficients(input_csv_path, output_csv_path, Q=10.0):
    """
    读取spur_scan_result.csv，计算陷波滤波器系数并输出spur_scan_result_coef.csv
    """
    try:
        df = pd.read_csv(input_csv_path, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(input_csv_path, encoding='gbk')
    except FileNotFoundError:
        print(f"❌ 错误：未找到文件 {input_csv_path}")
        return False
    except Exception as e:
        print(f"❌ 读取CSV失败 {input_csv_path}：{e}")
        return False

    if 'frequency' not in df.columns:
        print(f"❌ 跳过 {input_csv_path}：未找到'frequency'列")
        return False

    iir_filter = IIR_FILTER_CLASS()
    processed_rows = []

    for idx, row in df.iterrows():
        original_row = row.to_dict()
        freq_val = row['frequency']

        if isinstance(freq_val, str) and freq_val.strip().lower() == 'no_supr':
            original_row['Used_Frequency'] = 'no_supr'
            original_row['X_CoefFixed'] = 'no_supr'
            original_row['Y_CoefFixed'] = 'no_supr'
            processed_rows.append(original_row)
            continue

        valid_freqs = []
        try:
            if isinstance(freq_val, str):
                clean_str = freq_val.strip().replace("'", '"')
                if '[' in clean_str and ']' in clean_str:
                    freq_list = ast.literal_eval(clean_str)
                    if isinstance(freq_list, list):
                        for item in freq_list:
                            try:
                                if isinstance(item, str):
                                    item_clean = item.strip().replace(',', '.')
                                    item_float = float(item_clean)
                                else:
                                    item_float = float(item)
                                valid_freqs.append(item_float)
                            except (ValueError, TypeError):
                                continue
                else:
                    clean_single = clean_str.replace(',', '.')
                    valid_freqs.append(float(clean_single))
            else:
                if isinstance(freq_val, list):
                    for item in freq_val:
                        try:
                            valid_freqs.append(float(item))
                        except (ValueError, TypeError):
                            continue
                else:
                    valid_freqs.append(float(freq_val))
        except (ValueError, TypeError, SyntaxError) as e:
            print(f"⚠️  警告：第{idx+1}行frequency值'{freq_val}'无效 → {e}")
            original_row['Used_Frequency'] = 'invalid'
            original_row['X_CoefFixed'] = 'invalid'
            original_row['Y_CoefFixed'] = 'invalid'
            processed_rows.append(original_row)
            continue

        if not valid_freqs:
            original_row['Used_Frequency'] = 'invalid'
            original_row['X_CoefFixed'] = 'invalid'
            original_row['Y_CoefFixed'] = 'invalid'
            processed_rows.append(original_row)
        else:
            for f0 in valid_freqs:
                new_row = original_row.copy()
                new_row['Used_Frequency'] = f0

                if (original_row['phy_mode'] == 0):
                    m20_pos = 0
                elif abs(f0) < 20:
                    m20_pos = 1
                elif abs(f0) < 40:
                    m20_pos = 3
                elif abs(f0) < 60:
                    m20_pos = 5
                else:
                    m20_pos = 7

                if f0 < 0:
                    m20_pos = m20_pos * (-1)

                notch_freq = float(abs((m20_pos * 10) - f0))
                if abs(notch_freq) > 7:
                    fs = 40.0
                else:
                    fs = 20.0

                B, A = iir_filter.iir_notch_coef(notch_freq, Q, fs)
                order = 2
                iir_filter.setCoef(B, A, order)
                x_fixed, y_fixed = iir_filter.setCoefFixed()

                new_row['X_CoefFixed'] = x_fixed
                new_row['Y_CoefFixed'] = y_fixed
                processed_rows.append(new_row)

    processed_df = pd.DataFrame(processed_rows)

    cols = df.columns.tolist()
    if 'Used_Frequency' not in cols:
        cols.insert(cols.index('frequency')+1, 'Used_Frequency')
    if 'X_CoefFixed' not in cols:
        cols.insert(cols.index('Used_Frequency')+1, 'X_CoefFixed')
    if 'Y_CoefFixed' not in cols:
        cols.insert(cols.index('X_CoefFixed')+1, 'Y_CoefFixed')
    processed_df = processed_df[cols]

    try:
        processed_df.to_csv(output_csv_path, index=False, encoding='utf-8')
    except Exception:
        processed_df.to_csv(output_csv_path, index=False, encoding='gbk')

    print(f"系数计算完成，结果已保存到: {output_csv_path}")
    return True


# ===================== 6. 功率计算函数（来自clac_pwr_for_ofdm_signal.py） =====================
def calc_pow_for_ofdm_signal(dataIn, Fs, NFFT, rfGain, spurPos=None):
    """
    计算OFDM信号的时域功率、频域功率及杂散功率
    """
    f, Pxx_den = welch(
        dataIn,
        fs=Fs,
        window=hann(NFFT),
        noverlap=NFFT // 2,
        nfft=NFFT,
        return_onesided=False,
        scaling='density'
    )

    freqAxis = f - Fs / 2
    freqResolution = Fs / NFFT

    timeDomainPower = 10 * np.log10(np.mean(np.abs(dataIn) ** 2)) - rfGain / 2
    freqDomainPower = 10 * np.log10(np.sum(Pxx_den * freqResolution)) - rfGain / 2

    PmaxOfSpur = np.max(Pxx_den)
    idxSpur = np.argmax(Pxx_den)
    spurPower_max = 10 * np.log10(PmaxOfSpur * freqResolution) - rfGain / 2
    spurFreqMHz_max = freqAxis[idxSpur] + Fs / 2

    spurPower_pos = None
    spurFreqMHz_pos = None
    if spurPos is not None:
        freq_diff = np.abs(f - spurPos)
        spurPosIdx = np.argmin(freq_diff)
        spurPower_pos = 10 * np.log10(Pxx_den[spurPosIdx] * freqResolution) - rfGain / 2
        spurFreqMHz_pos = f[spurPosIdx]

    return {
        "timeDomainPower_dBm": timeDomainPower,
        "freqDomainPower_dBm": freqDomainPower,
        "spurPower_max_dBm": spurPower_max,
        "spurFreqMHz_max": spurFreqMHz_max,
        "spurPower_pos_dBm": spurPower_pos,
        "spurFreqMHz_pos": spurFreqMHz_pos,
        "freqAxis": freqAxis,
        "freq": f,
        "Pxx_den": Pxx_den,
        "freqResolution": freqResolution
    }


def read_data_from_csv(file_path, i_col, q_col):
    """
    从CSV文件中读取指定列的I和Q数据，并转换为复数格式
    """
    data = []
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            x = float(row[i_col]) / (2**12)
            y = float(row[q_col]) / (2**12)
            data.append(complex(x, y))
    return np.array(data)


def read_spur_config(config_file):
    """
    读取杂散配置CSV文件，获取phy_mode、channel、Used_Frequency信息
    """
    spur_config = {}
    with open(config_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                phy_mode = int(row['phy_mode'])
                channel = int(row['channel'])
                used_freq = row['Used_Frequency']

                if used_freq != 'invalid' and used_freq != "['no_spur']":
                    try:
                        used_freq = float(used_freq)
                        if (phy_mode, channel) not in spur_config:
                            spur_config[(phy_mode, channel)] = []
                        spur_config[(phy_mode, channel)].append(used_freq)
                    except ValueError:
                        continue
            except Exception as e:
                print(f"读取配置行时出错: {e}")
                continue
    return spur_config


def update_config_file(config_file, config_updates):
    """
    更新配置文件的pwr列
    """
    config_rows = []
    fieldnames = None

    with open(config_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames
        for row in reader:
            config_rows.append(row)

    updated_count = 0
    for row in config_rows:
        try:
            phy_mode = int(row['phy_mode'])
            channel = int(row['channel'])
            used_freq = row['Used_Frequency']

            if used_freq != 'invalid' and used_freq != "['no_spur']":
                used_freq = float(used_freq)
                config_key = (phy_mode, channel, used_freq)
                if config_key in config_updates:
                    new_pwr = config_updates[config_key]
                    row['pwr'] = str(new_pwr)
                    updated_count += 1
                    print(f"更新配置: phy_mode={phy_mode}, channel={channel}, Used_Frequency={used_freq}, pwr={new_pwr:.6f}")
        except Exception as e:
            print(f"处理配置行时出错: {e}")
            continue

    backup_file = config_file + '.bak'
    os.replace(config_file, backup_file)
    print(f"已创建备份文件: {backup_file}")

    with open(config_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(config_rows)

    print(f"配置文件更新完成，共更新 {updated_count} 行")


def process_directory_for_power(directory, i_col, q_col, Fs, NFFT, rfGain, spur_config, config_file, output_dir='output'):
    """
    处理目录下的CSV文件，计算指定位置的功率并更新配置文件
    """
    os.makedirs(output_dir, exist_ok=True)

    pattern = re.compile(r'phy_mode(\d+)_chan(\d+)')
    csv_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.csv') and pattern.search(file):
                csv_files.append(os.path.join(root, file))

    config_updates = {}

    for csv_file in csv_files:
        file_name = os.path.basename(csv_file)
        print(f"正在处理文件: {file_name}")

        match = pattern.search(file_name)
        if match:
            phy_mode = int(match.group(1))
            chan = int(match.group(2))
        else:
            print(f"警告: 文件 {file_name} 不符合phy_mode%d_chan%d模式，跳过")
            continue

        dataIn = read_data_from_csv(csv_file, i_col, q_col)

        used_freqs = []
        if (phy_mode, chan) in spur_config:
            used_freqs = spur_config[(phy_mode, chan)]
            print(f"配置的杂散频率位置: {used_freqs} MHz")

        if len(used_freqs) > 0:
            for used_freq in used_freqs:
                pos_result = calc_pow_for_ofdm_signal(dataIn, Fs, NFFT, rfGain, spurPos=used_freq)
                config_key = (phy_mode, chan, used_freq)
                config_updates[config_key] = pos_result['spurPower_pos_dBm']

        print()

    update_config_file(config_file, config_updates)


# ===================== 7. 主流程控制函数 =====================
def main_process(
    input_dir,
    output_dir,
    FS,
    SPUR_THR,
    Q,
    rfGain,
    NFFT,
    *,
    save_spectrum_plots=True,
):
    """
    主流程控制函数
    """
    # 步骤1：检测杂散并生成spur_scan_result.csv
    result_dir = os.path.join(output_dir, 'result')
    spectrum_plot_dir = None
    if save_spectrum_plots:
        spectrum_plot_dir = os.path.join(output_dir, 'output', 'spectrum')
    spur_scan_result_csv = detect_spurs_from_csv(
        input_dir,
        result_dir,
        FS,
        SPUR_THR,
        spectrum_plot_dir=spectrum_plot_dir,
        dc_margin=DC_MARGIN_MHZ,
    )

    # 步骤2：计算陷波系数并生成spur_scan_result_coef.csv
    spur_scan_result_coef_csv = os.path.join(result_dir, "spur_scan_result_coef.csv")
    calculate_notch_coefficients(spur_scan_result_csv, spur_scan_result_coef_csv, Q)

    # 步骤3：读取配置并计算指定位置的功率
    spur_config = read_spur_config(spur_scan_result_coef_csv)

    if len(spur_config) > 0:
        power_output_dir = os.path.join(output_dir, 'output')
        process_directory_for_power(
            input_dir,
            ' sample i_ch0',
            ' sample q_ch0',
            FS,
            NFFT,
            rfGain,
            spur_config,
            spur_scan_result_coef_csv,
            power_output_dir
        )
    else:
        print("未找到有效的杂散配置")

    print("\n所有处理完成！")


if __name__ == "__main__":
    # 配置参数
    INPUT_DIR = r'D:\path\to\iq_csv'  # 数据文件目录
    OUTPUT_DIR = INPUT_DIR  # 输出目录与输入目录相同
    FS = 80  # 采样频率 (MHz)
    SPUR_THR = 18  # 杂散检测阈值 (dB)
    Q = 5.0  # 陷波滤波器Q值
    RF_GAIN = 98  # 射频增益 (dB)
    NFFT = 16000  # FFT点数
    SAVE_SPECTRUM_PLOTS = True  # 步骤1：IQ/PSD 频谱 PDF → OUTPUT_DIR/output/spectrum/

    print("=" * 60)
    print("开始杂散扫描处理流程")
    print("=" * 60)

    main_process(
        INPUT_DIR,
        OUTPUT_DIR,
        FS,
        SPUR_THR,
        Q,
        RF_GAIN,
        NFFT,
        save_spectrum_plots=SAVE_SPECTRUM_PLOTS,
    )
