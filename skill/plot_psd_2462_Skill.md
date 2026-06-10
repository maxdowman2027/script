# plot_psd_2462.py — I/Q 时域 + PSD 绘图

## 脚本概述

`plot_psd_2462.py` 读取含 **`sample_i`**、**`sample_q`** 列的 CSV，生成 **两页 PDF**：

1. **时域**：I、Q 归一化幅度 vs 时间（µs），Ch0 / Ch1 双子图  
2. **频域**：Welch 功率谱密度（dB），Ch0 / Ch1 双子图  

适用于 `parse_48bit_dump_iq --merge-iq`、`dump_64bit_to_iq8.py`、`modem_dump_pipeline.py` 等下游 I/Q 文件。

---

## 输入 / 输出

| 项 | 说明 |
|----|------|
| 输入列 | `sample_i`、`sample_q`（列名大小写不敏感） |
| 默认输出 | **`<input_stem>_spec.pdf`**（与输入 CSV 同目录） |
| `-o` | 显式指定 PDF 路径 |

示例：

```text
espwifi_modem_dump..._data_iq8.csv
  → espwifi_modem_dump..._data_iq8_spec.pdf
```

---

## 配置区（脚本顶部）

| 变量 | 默认 | 含义 |
|------|------|------|
| `CSV_FILE` | — | 默认输入 CSV |
| `OUTPUT_PDF` | `""` | 空 → 自动 `<stem>_spec.pdf` |
| `MAX_ROWS` | 65536 | 读取行数上限；0 = 全文件 |
| `TIME_PLOT_SAMPLES` | 4096 | 时域图最多绘制点数；0 = 与读取行数相同 |
| `IQ_BIT_WIDTH` | 8 | 归一化除数 `2**N`（8-bit 用 8，10-bit 用 10） |
| `fs` | 160e6 | 采样率 Hz（改脚本内变量或后续扩展 CLI） |

---

## 命令行

```bash
python plot_psd_2462.py

python plot_psd_2462.py D:\path\to\data_iq8.csv

python plot_psd_2462.py data_iq_merged.csv -o D:\out\custom.pdf

python plot_psd_2462.py data.csv --max-rows 0 --time-samples 16384

python plot_psd_2462.py data.csv --bit-width 10
```

| 参数 | 说明 |
|------|------|
| `csv_file` | 输入 I/Q CSV |
| `-o`, `--output` | 输出 PDF（默认 `<stem>_spec.pdf`） |
| `--max-rows` | 读取行数上限 |
| `--time-samples` | 时域显示点数 |
| `--bit-width` | ADC 位宽（归一化） |

---

## PDF 内容

### 页 1 — 时域

- 横轴：时间 **µs**（`sample_index / fs`）
- 纵轴：I、Q 归一化幅度（默认 ÷256）
- 左：Ch0；右：Ch1（当前脚本对单路 I/Q 数据 Ch0/Ch1 相同）

### 页 2 — PSD

- Welch 法，`NFFT ≤ 16384`，Hanning 窗，50% overlap  
- 横轴：频率 **MHz**（双边谱 fftshift）  
- 纵轴：10·log10(|P|)

---

## 数据流位置

```text
*_data_iq_merged.csv / *_iq8.csv
  → plot_psd_2462.py
  → <stem>_spec.pdf（时域 + PSD）
```

---

## 依赖

`pandas`、`numpy`、`matplotlib`、`scipy`

---

## 元数据

- **脚本**: `plot_psd_2462.py`
- **标签**: psd, welch, iq, time_domain, spec, pdf, sample_i, sample_q
