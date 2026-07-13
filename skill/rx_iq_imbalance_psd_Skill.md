# rx_iq_imbalance_psd.py — RX IQ 抑制（镜像功率差）

## 脚本概述

`rx_iq_imbalance_psd.py` 读取 dump **I/Q CSV**，按信道带宽与单音偏移在 Welch PSD 上定位**主音**与**镜像音**，计算 IQ 抑制：

```text
iq_suppression_db = ori_tone_pwr_db - mir_tone_pwr_db
```

算法与 Xian 测试脚本 `myplot.psd_plot_rx_cal` 一致；Welch 参数复用 `plot_psd_2462.py` 的 `PSD_NFFT_STEP_MHZ`（`NFFT = Fs_MHz / 0.1`）。

**重要**：`phymd`（带宽）、`chan`（信道中心）、`freqcw`（CW 频率）均在**脚本顶部配置区**设置，**不从文件名解析**。

---

## 配置区（脚本顶部）

| 变量 | 含义 |
|------|------|
| `INPUT_CSV` | 默认输入 CSV（单文件） |
| `INPUT_DIR` | 批量目录（通常用命令行 positional 传目录） |
| `INPUT_GLOB` | 目录批量时的 glob，默认 `*.csv` |
| `OUTPUT_SUMMARY` | 汇总 CSV 路径；空 → 输入旁自动生成 |
| **`BW_MHZ`** | 信道带宽 MHz（20 / 40 / 80 / 160 / 320） |
| **`CH_FREQ_MHZ`** | 信道中心频率 MHz |
| **`FREQCW_MHZ`** | CW 单音频率 MHz |
| `MAX_ROWS` | 最多读取行数；0 = 全文件 |
| `IQ_MODE` | `auto` / `single` / `2ant` |
| `USE_CH` | 2ant 时选 0 或 1 |
| `BIT_WIDTH` | ADC 位宽，用于 `sig_pwr_db`；0 表示已是归一化 float |
| `TONE_BIN_SPAN` | 估计 bin 两侧各搜索 ±N 点取峰值 |
| `SAVE_PDF` | 是否输出 `*_iq_cal.pdf` |

### 带宽 → Welch 采样率（与 myplot 一致）

| `BW_MHZ` | `sample_freq_mhz` | `all_freq_mhz` |
|----------|-------------------|----------------|
| 20 | 40 | 40 |
| 40 | 80 | 80 |
| 80 | 160 | 160 |
| 其他 | 320 | 320 |

偏移频率：`diff_freq_mhz = abs(freqcw - ch_freq)`。  
主音在信道中心**左/右**由 `freqcw > ch_freq` 决定；镜像音在对称位置。

---

## 输入 CSV 格式

| 模式 | 列名 |
|------|------|
| **single** | `sample_i`, `sample_q` |
| **2ant** | `ch0_sample_i/q`, `ch1_sample_i/q` |

由 `plot_psd_2462.read_iq_data()` 读取（`--mode auto` 按列名检测）。

---

## 输出

| 产物 | 路径 |
|------|------|
| 汇总 CSV | `<input_stem>_iq_imbalance_summary.csv` 或目录下 `iq_imbalance_summary.csv` |
| PSD PDF（可选） | `<input_stem>_iq_cal.pdf`，标注主音/镜像竖线 |

### 汇总列说明

| 列 | 说明 |
|----|------|
| `ori_tone_pwr_db` | 主音 PSD 峰值（10·log10\|P\|，dB） |
| `mir_tone_pwr_db` | 镜像音 PSD 峰值（dB） |
| `iq_suppression_db` | IQ 抑制 = 主音 − 镜像（dB，越大越好） |
| `sig_pwr_db` | 时域 RMS 功率（myplot 同款公式） |
| `frequency_ori_mhz` / `frequency_mir_mhz` | 主/镜像估计频率 |
| `ori_signal_pos` / `mir_signal_pos` | PSD 数组中的 bin 索引 |

---

## 命令行

```bash
# 使用配置区（推荐）
python rx_iq_imbalance_psd.py

# 指定输入文件
python rx_iq_imbalance_psd.py "D:\path\to\iladata_adc_tone.csv"

# 批量目录（所有文件共用配置区 BW/CHAN/FREQCW）
python rx_iq_imbalance_psd.py "D:\path\to\dumps" -g "*.csv" -o summary.csv

# CLI 覆盖测试参数
python rx_iq_imbalance_psd.py data.csv --bw 40 --chan 5210 --freqcw 5250

# 2ant ch1、12-bit、不生成 PDF
python rx_iq_imbalance_psd.py data.csv --ch 1 --bit-width 12 --no-pdf
```

| 参数 | 说明 |
|------|------|
| `input` | CSV 文件或目录 |
| `-g`, `--glob` | 目录模式 glob |
| `--bw` | 覆盖 `BW_MHZ` |
| `--chan` | 覆盖 `CH_FREQ_MHZ` |
| `--freqcw` | 覆盖 `FREQCW_MHZ` |
| `-o`, `--output` | 汇总 CSV 路径 |
| `--max-rows` | 读取行数上限 |
| `--mode` | `auto` / `single` / `2ant` |
| `--ch` | 2ant 通道 0/1 |
| `--bit-width` | ADC 位宽 |
| `--no-pdf` | 跳过 PSD PDF |

---

## Python API

```python
from rx_iq_imbalance_psd import (
    config_test_params,
    load_iq_from_csv,
    psd_plot_rx_cal,
)

params = config_test_params(bw_mhz=20, ch_freq_mhz=5180, freqcw_mhz=5140)
i, q = load_iq_from_csv(path)
result, freq_mhz, pwr_db = psd_plot_rx_cal(i, q, params)
print(result.iq_suppression_db)
```

---

## 依赖

- `numpy`, `pandas`, `scipy`, `matplotlib`
- `plot_psd_2462.read_iq_data`（I/Q CSV 读取）

---

## 参考

- Xian：`D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rx_script\baselib\plot\myplot.py` → `psd_plot_rx_cal`
- 本仓库：`plot_psd_2462.py`（Welch 步进与 I/Q 列约定）
