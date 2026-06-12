# plot_psd_2462.py — I/Q 时域 + PSD 绘图

## 脚本概述

`plot_psd_2462.py` 读取 I/Q CSV，生成 **两页 PDF**：

1. **时域**：Ch0 / Ch1 各一张 I、Q 归一化波形（µs）
2. **频域**：Ch0 / Ch1 Welch PSD（MHz，dB）

支持两种输入布局（`--mode auto|single|2ant`，默认 **auto** 按列名检测）：

| 模式 | 输入列 | 说明 |
|------|--------|------|
| **single** | `sample_i`, `sample_q` | 单路连续 I/Q；Ch0/Ch1 子图相同 |
| **2ant** | `ch0_sample_q`, `ch0_sample_i`, `ch1_sample_q`, `ch1_sample_i` | 双天线 10-bit I/Q（`parse_60bit_40bit_2ant_iq.py` 输出） |

---

## 输入 / 输出

| 项 | 说明 |
|----|------|
| 默认输出 | **`<input_stem>_spec.pdf`** |
| `-o` | 显式指定 PDF 路径 |

示例：

```text
hesu_20m_mcs0_data_2ant_iq.csv  →  hesu_20m_mcs0_data_2ant_iq_spec.pdf
data_iq_merged.csv              →  data_iq_merged_spec.pdf
```

---

## 配置区（脚本顶部）

| 变量 | 默认 | 含义 |
|------|------|------|
| `CSV_FILE` | — | 默认输入 CSV |
| `OUTPUT_PDF` | `""` | 空 → `<stem>_spec.pdf` |
| `MAX_ROWS` | 65536 | 读取行数上限；0 = 全文件 |
| `TIME_PLOT_SAMPLES` | 65535 | 时域最多绘制点数；0 = 与读取行数相同 |
| `IQ_BIT_WIDTH` | 10 | 归一化 `2**N`（8-bit→8，10-bit→10） |
| `IQ_MODE` | `auto` | `auto` / `single` / `2ant` |
| `fs` | 80e6 | 采样率 Hz |

---

## 命令行

```bash
python plot_psd_2462.py

python plot_psd_2462.py D:\path\to\hesu_20m_mcs0_data_2ant_iq.csv

python plot_psd_2462.py data_2ant_iq.csv --mode 2ant --bit-width 10

python plot_psd_2462.py data_iq8.csv --mode single --bit-width 8

python plot_psd_2462.py data.csv -o out.pdf --max-rows 131072 --time-samples 8192
```

| 参数 | 说明 |
|------|------|
| `csv_file` | 输入 I/Q CSV |
| `-o`, `--output` | 输出 PDF |
| `--mode` | `auto` / `single` / `2ant` |
| `--max-rows` | 读取行数上限 |
| `--time-samples` | 时域显示点数 |
| `--bit-width` | ADC 位宽（归一化） |

---

## PDF 内容

### 页 1 — 时域

- 左：**Ch0** I/Q；右：**Ch1** I/Q（2ant 模式下为真实双天线数据）
- 横轴：时间 µs；纵轴：归一化幅度

### 页 2 — PSD

- Welch，`NFFT ≤ 65536`，Hanning，50% overlap
- 左 Ch0 / 右 Ch1 独立频谱

---

## 数据流

```text
parse_60bit_40bit_2ant_iq.py  →  *_2ant_iq.csv  ─┐
parse_48bit / dump_64bit_to_iq8 / merge_iq      ─┼→ plot_psd_2462.py → *_spec.pdf
```

---

## 依赖

`pandas`、`numpy`、`matplotlib`、`scipy`

---

## 元数据

- **脚本**: `plot_psd_2462.py`
- **标签**: psd, welch, iq, 2ant, dual_antenna, time_domain, ch0, ch1
