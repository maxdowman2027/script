# tx_adcdump_data_parse.py — #dump_data bit 字段解析

## 脚本概述

`tx_adcdump_data_parse.py` 从含 `#dump_data` 列的 CSV（通常为 `bin_to_64bit_csv.py` 产出的 `*_data.csv`）中，按配置的 bit 范围提取字段，输出为 **有符号（补码）** 或 **无符号** 整型列。支持单文件或**目录批量**处理。

---

## 预设 (preset)

| preset | 用途 | 输出列（示例） |
|--------|------|----------------|
| `3tap10` | 3-tap 10-bit I/Q（每 64-bit 6 字段） | `sample_i_0`, `sample_q_0`, … |
| `2tap12` | 2-tap 12-bit I/Q | `sample_q`, `sample_i` |
| `gain` | LNA/VGA 增益位 | `lna`, `vga` |

---

## 目录批量模式

- **输入为文件夹**：扫描该目录下 `*.csv`（默认不递归）
- **优先 `*_data.csv`**：若存在则只处理过滤后的 dump 文件
- **自动跳过产物**：`*_adcdump.csv`、`*_iq8.csv`、`*_iq_merged.csv`、`*_48bit_parse.csv`、`*_delim_report.csv` 等
- **默认输出**：每个输入生成同目录 `<stem>_adcdump.csv`
- **`-o out_dir`**：批量写入指定目录
- **`-r` / `--recursive`**：递归搜索子目录

---

## 配置区

| 变量 | 默认 | 含义 |
|------|------|------|
| `INPUT_FILE` | （见脚本） | 单个 `*_data.csv` **或目录** |
| `OUTPUT_FILE` | `""` | 空 → `<stem>_adcdump.csv` |
| `PRESET` | `gain` | `3tap10` / `2tap12` / `gain` |
| `VALUE_TYPE` | `unsigned` | `signed` / `unsigned`（无 CLI 覆盖时） |

---

## 命令行

```bash
# 单文件
python tx_adcdump_data_parse.py input_data.csv --preset 3tap10

# 有符号 / 无符号
python tx_adcdump_data_parse.py input_data.csv --signed
python tx_adcdump_data_parse.py input_data.csv --unsigned
python tx_adcdump_data_parse.py input_data.csv --value-type unsigned

# 目录批量（自动扫描 *_data.csv）
python tx_adcdump_data_parse.py D:\path\to\csv_folder --preset 3tap10

# 指定批量输出目录
python tx_adcdump_data_parse.py csv_folder -o D:\path\to\out_dir --preset 3tap10

# 递归子目录
python tx_adcdump_data_parse.py csv_folder -r -o D:\path\to\out_dir
```

| 参数 | 说明 |
|------|------|
| `input_csv` | `*_data.csv`、任意含 `#dump_data` 的 CSV，或目录 |
| `-o` | 单文件时输出路径；目录/批量时必须为输出目录 |
| `-r`, `--recursive` | 目录输入时递归搜索子文件夹 |
| `--preset` | bit 布局预设 |
| `--signed` / `--unsigned` / `--value-type` | 输出数值类型 |

---

## 数据流

```text
espwifi_modem_dump.bin
  → bin_to_64bit_csv.py → *_data.csv
  → tx_adcdump_data_parse.py (--preset 3tap10) → *_adcdump.csv
  → merge_dump_3data_iq.py → *_iq_merged.csv（可选）
```

---

## 依赖

Python 标准库（`csv`, `pathlib`）

---

## 版本历史

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| 1.2 | 2026-05-27 | 目录批量：自动扫描 `*_data.csv`、跳过产物、`-r` 递归、`-o` 输出目录 |
| 1.1 | 2026-05 | 增加 `--preset`、`--signed`/`--unsigned` CLI |
| 1.0 | 2026-04-16 | 初始版本，bit 字段转有符号数 |

---

## 元数据

- **脚本**: `tx_adcdump_data_parse.py`
- **标签**: adcdump, dump_data, bit_field, signed, unsigned, batch
