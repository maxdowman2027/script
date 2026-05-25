# spur_scan_process.py — 杂散扫描一体化处理

## 脚本概述

**路径**：`spur_notch/spur_scan_process.py`（仓库根执行：`python spur_notch/spur_scan_process.py`）

整合根目录 **`psd_plot.py`**（PSD + 杂散检测）、**`notch_cal.py`**（IIR 陷波系数与定点化，本脚本内嵌同源实现）、**`clac_pwr_for_ofdm_signal.py`**（OFDM 频点功率）的能力，形成**三步流水线**：

```text
ADC/IQ CSV (phy_mode*_chan*.csv)
    → [1] spur_scan_result.csv        （杂散频点、diff_pwr、pwr 初值）
    → [1b] output/spectrum/*.pdf      （每文件 IQ 时域 + PSD 频谱图，可选）
    → [2] spur_scan_result_coef.csv   （Used_Frequency、X/Y_CoefFixed 定点系数）
    → [3] 回写 spur_scan_result_coef.csv 的 pwr 列（按 Used_Frequency 实测杂散功率）
```

**依赖**：`numpy`、`pandas`、`matplotlib`、`scipy`（`welch`）。

**相关脚本**（同目录，分工不同）：

| 脚本 | 关系 |
|------|------|
| `spur_notch/notch_cal.py` | 独立陷波系数/定点化，算法与内嵌 `IIR_FILTER_CLASS` 同源，便于单测 |
| `spur_notch/spur_scan_regression.py` | 批量解析 coef CSV、寄存器草稿 |
| `spur_notch/spur_analysis.py` | 两份 scan/coef 结果对比 |
| 根目录 `psd_plot.py`、`clac_pwr_for_ofdm_signal.py` | 被本脚本吸收的思路来源 |

---

## 输入数据要求

### 目录与文件名

- **输入目录** `INPUT_DIR`：递归或单层放置 IQ 采样 CSV。
- **文件名**：须能从 basename 解析 **`phy_mode(\d+)`** 与 **`chan(\d+)`**（正则 `(?:phy_mode(\d+))|(?:chan(\d+))`）。
- 示例：`..._phy_mode0_chan6_....csv`

### CSV 列（IQ 数据）

| 列名 | 说明 |
|------|------|
| ` sample i_ch0` | I 路（注意列名**前导空格**） |
| ` sample q_ch0` | Q 路 |

步骤 1 直接读原始整数；步骤 3 功率计算时 I/Q **除以 2^12** 再组成复数。

---

## 三步流程详解

### 步骤 1：`detect_spurs_from_csv` → `spur_scan_result.csv`

**输出目录**：`{OUTPUT_DIR}/result/spur_scan_result.csv`

**PSD**：`welch`，`NFFT=16000`，`overlap=NFFT/2`，Hanning 窗，`return_onesided=False`。

**杂散候选**：谱线功率 `10*log10(|P|) > SPUR_THR`（默认 **18 dB**）。

**参考功率 `avg_pwr`**：±1 MHz 处（`|F|==1`）两条谱线功率的算术平均。

**信道相关筛选**（相对偏移 `F[i]`，单位 MHz）：

| 条件 | 保留规则 |
|------|----------|
| 排除 DC 邻域 | `F[i] < -0.1` 或 `F[i] > 0.1` |
| `channel > 14` | `(channel + F[i]) % 40 == 0` |
| `channel == 14` | `(2484 + F[i]) % 40 == 0` |
| 其它 2.4G 信道 | `(2412 + 5*(channel-1) + F[i]) % 40 == 0` |

**无杂散**：写入 `frequency/diff_pwr/pwr = no_spur`（列表字段为字符串 `no_spur`）。

**非 DC 相对 40M 倍频功率检查**（写入 `spur_scan_result.csv` 扩展列）：

- **DC 排除**：`|F| <= 0.1` MHz（`DC_MARGIN_MHZ`）视为中心/DC 邻域，不参与比较。  
- **40M 倍频参考**：非 DC 且满足 40 MHz 栅格规则（与上表杂散筛选 `% 40 == 0` 相同）的频点，取其中 PSD 功率 **最大值** `harm_40m_ref_pwr_db`。  
- **异常判定**：非 DC、**非** 40M 倍频、且 `PSD > SPUR_THR`、且 **功率 > harm_40m_ref_pwr_db** 的频点记入 `non_harm_above_40m_*`；`has_non_harm_above_40m` 为 `yes`/`no`/`no_40m_ref`（无倍频参考点时）。  
- 控制台对 `yes` 打印 `[WARN]`；频谱 PDF 上用**橙色三角**标出异常频点。

**频谱图输出**（`SAVE_SPECTRUM_PLOTS=True`，默认开启）：

- 目录：`{OUTPUT_DIR}/output/spectrum/`
- 每个输入 CSV 一个 PDF（与 `psd_plot.py` 相同两页）：**IQ 时域**（I/Q 波形）、**PSD 频谱**（`fftshift` 后功率密度 dB）
- PSD 图含：`SPUR_THR` 水平参考线；40M 栅格杂散 **红点**；高于倍频参考的非倍频点 **橙色三角**
- 关闭：`main_process(..., save_spectrum_plots=False)` 或脚本底部 `SAVE_SPECTRUM_PLOTS = False`

**输出列**：

| 列 | 含义 |
|----|------|
| `phy_mode` | 从文件名解析 |
| `channel` | 从文件名解析 |
| `frequency` | 杂散相对频偏列表（MHz），或 `no_spur` |
| `diff_pwr` | 相对 avg_pwr 的 dB 差 |
| `pwr` | `10*log10(|P|)-58` 的初值（dB 量纲，与历史脚本一致） |
| `harm_40m_ref_pwr_db` | 非 DC 的 40M 倍频点中最大 PSD (dB) |
| `non_harm_above_40m_freq` / `_pwr` / `_diff` | 高于该参考的非倍频点（>SPUR_THR） |
| `has_non_harm_above_40m` | `yes` / `no` / `no_40m_ref` |

---

### 步骤 2：`calculate_notch_coefficients` → `spur_scan_result_coef.csv`

读取 `spur_scan_result.csv`，对每条有效 `frequency` 计算 **2 阶 IIR 陷波** 浮点系数并 **定点化**（`IIR_FILTER_CLASS`）。

**陷波频率映射**（`Used_Frequency` = 原 `f0`）：

- `phy_mode == 0` → `m20_pos = 0`
- `|f0| < 20` → 1；`< 40` → 3；`< 60` → 5；否则 7；`f0 < 0` 时 `m20_pos` 取反
- `notch_freq = |m20_pos * 10 - f0|`；`notch_freq > 7` 时 `fs=40`，否则 `fs=20`（MHz）
- `iir_notch_coef(notch_freq, Q, fs)` → `setCoef` → `setCoefFixed`

**多频点**：一行多个频率时**展开为多行**，每行一个 `Used_Frequency` 与一组 `X_CoefFixed` / `Y_CoefFixed`。

**新增列**：`Used_Frequency`、`X_CoefFixed`、`Y_CoefFixed`（字符串形式的定点整数列表）。

**异常/无杂散**：`no_supr` / `invalid` 标记（代码中 `no_supr` 与结果里 `no_spur` 拼写不一致，以 CSV 实际内容为准）。

**定点配置**（`gSetting`）：

| 类 | 典型参数 |
|----|----------|
| `RX_TIME_CTRL` | `syncDfeFixedBits=12`, `syncDfeFixedClip=0.5` |
| `SINGLE_TONE_SPUR_CTRL` | A: 16bit/clip4；B: 12bit/clip4 |

---

### 步骤 3：`process_directory_for_power` → 更新 `pwr` 列

- 从 `spur_scan_result_coef.csv` 读取 `read_spur_config`：`(phy_mode, channel) → [Used_Frequency, ...]`。
- 再次遍历输入目录中 `phy_mode(\d+)_chan(\d+).csv`，用 `calc_pow_for_ofdm_signal` 在 **`spurPos=Used_Frequency`** 处算 **`spurPower_pos_dBm`**。
- `update_config_file`：按 `(phy_mode, channel, Used_Frequency)` 匹配行，更新 **`pwr`**；原文件备份为 **`*.bak`**。

**功率参数**：`Fs`、`NFFT`、`rfGain`（脚本底部 `RF_GAIN`，默认 98）；与步骤 1 的 `welch` 设置应对齐。

---

## 配置参数（`if __name__ == "__main__"`）

在脚本底部修改后运行：

| 变量 | 默认 | 含义 |
|------|------|------|
| `INPUT_DIR` | （示例路径） | IQ CSV 根目录 |
| `OUTPUT_DIR` | 常与 `INPUT_DIR` 相同 | 结果根目录 |
| `FS` | 160 | 采样率 (MHz) |
| `SPUR_THR` | 18 | PSD 杂散检测阈值 (dB) |
| `Q` | 5.0 | 陷波 Q 值 |
| `RF_GAIN` | 98 | 功率换算射频增益 (dB) |
| `NFFT` | 16000 | FFT 点数 |
| `SAVE_SPECTRUM_PLOTS` | True | 是否在 `output/spectrum/` 保存 IQ/PSD PDF |

---

## 运行方式

```bash
# 在仓库根目录
python spur_notch/spur_scan_process.py
```

```python
from spur_notch.spur_scan_process import main_process

main_process(
    input_dir=r"D:\path\to\iq_csv",
    output_dir=r"D:\path\to\out",
    FS=160,
    SPUR_THR=18,
    Q=5.0,
    rfGain=98,
    NFFT=16000,
)
```

若作为包导入失败，可将 `spur_notch` 加入 `PYTHONPATH` 或在 `spur_notch` 目录下用 `python -c "import spur_scan_process"` 方式调用（推荐仓库根 + 上述命令行）。

---

## 产物目录结构

```text
OUTPUT_DIR/
├── result/
│   ├── spur_scan_result.csv
│   └── spur_scan_result_coef.csv   # 步骤 3 会原地更新 pwr 并生成 .bak
└── output/
    ├── spectrum/                   # 步骤 1：每 CSV 一个 IQ+PSD 频谱 PDF
    │   └── phy_mode0_chan6.pdf
    └── ...                         # 步骤 3 功率处理占位目录
```

---

## 常见问题

1. **跳过文件**：文件名无法解析 `phy_mode`/`chan` → 打印跳过，不写入 result。  
2. **列名不匹配**：IQ 列必须为 ` sample i_ch0` / ` sample q_ch0`（含前导空格）。  
3. **无有效杂散配置**：步骤 3 打印「未找到有效的杂散配置」，coef 文件仍由步骤 2 生成。  
4. **与 `notch_cal.py` 对照**：系数公式以 `IIR_FILTER_CLASS.iir_notch_coef` 为准；独立跑 `notch_cal.py` 可验证定点结果。

---

## Skill 元数据

- **描述**: 杂散扫描 PSD 检测、陷波系数定点化、频点功率回写的一体化流水线。  
- **标签**: spur, notch, PSD, IIR, spur_scan, WiFi RX, spur_notch  
