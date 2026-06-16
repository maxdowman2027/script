# dump_64bit_to_iq8.py — 64-bit dump 直拆 8-bit I/Q

## 脚本概述

`dump_64bit_to_iq8.py` 从 `*_data.csv`（`bin_to_64bit_csv.py` 输出）直接按字节拆出 **8-bit 有符号** I/Q，支持 **单路** 与 **双天线** 两种布局。流式处理，可单文件或目录批量。

---

## 模式对比

| 模式 | 每 64-bit 默认行数 | 字节顺序（从低位） | 输出列 |
|------|-------------------|-------------------|--------|
| **single** | 4 | `[7:0]q, [15:8]i` × N 组 16-bit | `sample_q`, `sample_i` |
| **2ant** | 2 | `[7:0]ch0_q, [15:8]ch0_i, [23:16]ch1_q, [31:24]ch1_i` × 2 组 32-bit | `ch0/ch1_sample_q/i` |

双天线模式下勿用 single 模式（会因 64-bit 字内 16-bit 重复字段产生梳状假频谱）。

---

## 原始数据列（校验用）

默认同时输出：

| 列 | 模式 | 含义 |
|----|------|------|
| `dump_data` | 全部 | 源 64-bit hex |
| `dump_data_16` | single | 本行对应 16-bit 原始块 |
| `dump_data_32` | 2ant | 本行对应 32-bit 原始块 |

校验：将 `dump_data_32` 按 4 字节从低到高转为有符号 8-bit，应等于同行四个 I/Q 列。

关闭：`--no-dump-data` / `--no-raw-chunk`

---

## 配置区

| 变量 | 默认 | 含义 |
|------|------|------|
| `IQ_MODE` | `2ant` | `single` / `2ant` |
| `PAIRS_PER_WORD` | 4 | single 模式每 word 对数 (1–4) |
| `SAMPLES_PER_WORD_2ANT` | 2 | 2ant 模式每 word 样本数 (1–2) |
| `KEEP_DUMP_DATA` | True | 输出 `dump_data` |
| `KEEP_RAW_CHUNK` | True | 输出 `dump_data_16/32` |
| `OUTPUT_SUFFIX` | `_iq8` | 默认 `<stem>_iq8.csv` |

---

## 命令行

```bash
python dump_64bit_to_iq8.py D:\path\to\*_data.csv

python dump_64bit_to_iq8.py input_data.csv --mode 2ant

python dump_64bit_to_iq8.py input_data.csv --mode single --pairs 4

python dump_64bit_to_iq8.py csv_folder -o D:\path\to\out_dir

python dump_64bit_to_iq8.py input.csv --no-raw-chunk --no-dump-data
```

| 参数 | 说明 |
|------|------|
| `input_csv` | `*_data.csv` 或目录 |
| `-o` | 输出 CSV 或批量输出目录 |
| `--mode` | `single` / `2ant` |
| `--pairs` | single：每 word 的 (q,i) 对数 |
| `--samples` | 2ant：每 word 的双天线样本数 |
| `--keep-dump-data` | 保留 64-bit 列（默认开） |
| `--no-dump-data` | 去掉 64-bit 列 |
| `--no-raw-chunk` | 去掉 16/32-bit 原始块列 |

---

## 数据流

```text
espwifi_modem_dump.bin
  → bin_to_64bit_csv.py → *_data.csv
  → dump_64bit_to_iq8.py (--mode 2ant) → *_iq8.csv
  → plot_psd_2462.py (--mode 2ant --bit-width 8 [--upsample 2])
```

---

## 依赖

标准库 + `csv`（无 pandas）

---

## 元数据

- **脚本**: `dump_64bit_to_iq8.py`
- **标签**: iq8, 8bit, 2ant, dual_antenna, dump_data, modem_dump
