# plot_psd_2462.py — I/Q 时域 + PSD 绘图

## 脚本概述

`plot_psd_2462.py` 读取 I/Q CSV，生成 **两页 PDF**：

1. **时域**：Ch0 / Ch1 各一张 I、Q 归一化波形（µs）
2. **频域**：Ch0 / Ch1 Welch PSD（MHz，dB）

支持两种输入布局（`--mode auto|single|2ant`，默认 **auto** 按列名检测）：

| 模式 | 输入列 | 典型上游 |
|------|--------|----------|
| **single** | `sample_i`, `sample_q` | `*_iq_merged.csv`, 48-bit merge |
| **2ant** | `ch0_sample_q/i`, `ch1_sample_q/i` | `parse_60bit_40bit_2ant_iq.py`, `dump_64bit_to_iq8.py --mode 2ant` |

支持两种与 **2抽1** 相关的速率处理（可独立或组合使用）：

| 场景 | 配置 | 说明 |
|------|------|------|
| CSV 为 **全速率**，绘图前做软件 2抽1 | `--decimate 2 --no-upsample` | `I/Q[::2]`，有效 `fs = --fs / 2` |
| CSV 为 **硬件已 2抽1** | `--upsample 2`（默认常开） | 插值恢复点数，`--fs` 填 **原始 ADC 速率** |

处理顺序：**归一化 → 抽取（可选）→ 上采样（可选）→ 绘图**。

---

## 输入 / 输出

| 项 | 说明 |
|----|------|
| 默认输出 | **`<input_stem>_spec.pdf`** |
| `-o` | 显式指定 PDF 路径 |

---

## 配置区（脚本顶部）

| 变量 | 默认 | 含义 |
|------|------|------|
| `CSV_FILE` | — | 默认输入 CSV |
| `OUTPUT_PDF` | `""` | 空 → `<stem>_spec.pdf` |
| `MAX_ROWS` | 65536 | 读取行数上限；0 = 全文件 |
| `TIME_PLOT_SAMPLES` | 65535 | 时域最多绘制点数；0 = 与读取行数相同 |
| `IQ_BIT_WIDTH` | 8 | 归一化 `2**N`（8-bit→8，10-bit→10） |
| `IQ_MODE` | `2ant` | `auto` / `single` / `2ant` |
| `DECIMATE_FACTOR` | 1 | 2 = 2抽1（`[::2]`）；1 = 不抽取 |
| `UPSAMPLE_FACTOR` | 2 | 对已抽取数据上采样倍率；1 = 关闭 |
| `UPSAMPLE_METHOD` | `poly` | `poly` / `linear` / `repeat` |
| `fs` | 80e6 | **抽取前**原始采样率 Hz；抽取/上采样后自动调整有效速率 |

---

## 命令行

```bash
python plot_psd_2462.py

# 全速率数据，软件 2抽1 后绘图（80MHz → 40MHz）
python plot_psd_2462.py data.csv --decimate 2 --no-upsample --fs 80e6 --bit-width 12

# 10-bit 双天线（320MHz 原始速率）
python plot_psd_2462.py data_2ant_iq.csv --mode 2ant --bit-width 10 --fs 320e6

# 8-bit 双天线 + 硬件 2抽1 CSV 上采样
python plot_psd_2462.py data_iq8.csv --mode 2ant --bit-width 8 --fs 80e6 --upsample 2

# 已是抽取后速率的数据，不做抽取/上采样
python plot_psd_2462.py data.csv --no-upsample --no-decimate --fs 40e6

python plot_psd_2462.py data.csv -o out.pdf --max-rows 131072 --time-samples 8192
```

| 参数 | 说明 |
|------|------|
| `csv_file` | 输入 I/Q CSV |
| `-o`, `--output` | 输出 PDF |
| `--mode` | `auto` / `single` / `2ant` |
| `--max-rows` | 读取行数上限 |
| `--time-samples` | 时域显示点数 |
| `--bit-width` | ADC 位宽（归一化除数） |
| `--fs` | 原始采样率 Hz（抽取前）；有效速率随抽取/上采样自动更新 |
| `--decimate` | 抽取倍率；`2` = 2抽1（`[::2]`） |
| `--no-decimate` | 关闭抽取（等同 `--decimate 1`） |
| `--upsample` | 上采样倍率 |
| `--upsample-method` | `poly`（默认）/ `linear` / `repeat` |
| `--no-upsample` | 关闭上采样 |

### 2抽1 抽取（软件）

对 **全速率** CSV 在绘图前做 2:1 抽取：

- 对 I/Q 各取 `data[::2]`，样点数减半
- `--fs` 填 **抽取前** ADC 速率（如 80e6）；脚本自动用 `fs/2` 画时域与 PSD
- PDF 标题标注 `2抽1 x2`
- 与 `--upsample` 互斥使用（一般二选一）

### 2抽1 上采样（硬件已抽取）

硬件对 IQ 做 **2:1 抽取** 后写入 CSV 时：

- CSV 内样本间隔对应 **Fs/2**
- 绘图前可用 **×2 上采样** 恢复时间轴点数
- `--fs` 仍填 **完整 ADC 速率**（如 80e6 或 320e6）
- PDF 标题会标注 `上采样 x2`

---

## PDF 内容

### 页 1 — 时域

- 左：**Ch0** I/Q；右：**Ch1** I/Q（2ant 为真实双天线）
- 横轴：时间 µs；纵轴：归一化幅度

### 页 2 — PSD

- Welch，`NFFT ≤ 16384`，Hanning，50% overlap
- 左 Ch0 / 右 Ch1 独立频谱

---

## 数据流

```text
bin_to_64bit_csv → *_data.csv
  ├→ parse_60bit_40bit_2ant_iq.py → *_2ant_iq.csv ─┐
  └→ dump_64bit_to_iq8.py (--mode 2ant) → *_iq8.csv ┼→ plot_psd_2462.py → *_spec.pdf
parse_48bit_dump_iq → *_iq_merged.csv ─────────────┘
```

---

## 依赖

`pandas`、`numpy`、`matplotlib`、`scipy`

---

## 元数据

- **脚本**: `plot_psd_2462.py`
- **标签**: psd, welch, iq, 2ant, upsample, decimate, 2抽1, time_domain, ch0, ch1
