# bin_to_64bit_csv.py — 二进制 dump 转 64-bit CSV

## 脚本概述

`bin_to_64bit_csv.py` 将原始二进制 dump 文件（如 `espwifi_modem_dump.*.bin`）按 **8 字节 / 64-bit word** 解析，输出 CSV。默认格式与 FPGA / modem 导出的 **`#dump_data`** 十六进制 CSV 一致，可直接作为 `tx_adcdump_data_parse.py` 的输入。

典型输入示例：

`D:\test_data\E22_M2\260604\espwifi_modem_dump.20260604-033842-003.bin`

---

## 数据流位置

```text
espwifi_modem_dump / FPGA 原始 .bin
  → bin_to_64bit_csv.py
  → <stem>.csv（完整 #dump_data）
  → <stem>_data.csv（去掉 4-word delimiter 块）
  → <stem>_delim_report.csv（帧头丢数 flag / 32B 计数）
  → tx_adcdump_data_parse.py（按 bit 字段提取 I/Q 等有符号数）
```

---

## 完整 delimiter（4 个连续 64-bit word）

仅当 **连续 4 个 word** 同时匹配下列模式时，才从 `_data.csv` 中整段剔除（支持两种顺序）：

**文档顺序**（从内向外）：

| 序号 | 64-bit word |
|------|-------------|
| 1–2 | `0x0000000000000000` |
| 3 | `0x00000000ABABABAB` |
| 4 | `0x55555555xxxxxxxx` |

**E22 dump 线上顺序**（数据中常见）：`0x55555555xx` → `ABABABAB` → `0` → `0`

### 第 4 word 帧头（`0x55555555xxxxxxxx`）

| 字段 | 位域 | 说明 |
|------|------|------|
| 高 32 bit | `[63:32]` | 固定 **`0x55555555`** |
| 丢数 flag | 低 32 bit **bit31** | `1` = 本间隔内曾发生数据丢失 |
| 丢失量 | 低 32 bit **bit30:0** | 丢失数据长度，单位 **32 Bytes** |

示例：`0x555555558000006F` → flag=1，lost_units=0x6F=111 → **3552 Bytes** 丢失。

单独的 `0x0` 或 `ABABABAB` **不会**被剔除（避免误删有效采样零值）。

---

## 输入 / 输出

| 文件 | 说明 |
|------|------|
| `<stem>.csv` | 完整原始 dump |
| `<stem>_data.csv` | 去掉 delimiter 块后的纯数据（默认生成） |
| `<stem>_delim_report.csv` | 每个 delimiter 块的帧头解析（默认生成） |

### `_delim_report.csv` 列

| 列 | 说明 |
|----|------|
| `block_index` | delimiter 块序号（从 0） |
| `start_word_index` | 在原始 word 流中的起始下标 |
| `frame_header_hex` | 第 4 word（`0x55555555xxxxxxxx`） |
| `data_lost_flag` | 0 / 1 |
| `lost_units_32B` | 丢失量（32-byte 单位） |
| `lost_bytes` | `lost_units_32B × 32` |

### 输出样式 `dump`（默认）

```csv
#dump_data 
0x7C3FF67DBFF20900,
...
```

### 输出样式 `full`

含 `index`、`dump_data`、`uint64_dec`、`low32_hex`、`high32_hex` 等列。

---

## 配置区（脚本顶部）

| 变量 | 含义 |
|------|------|
| `INPUT_BIN` | 默认输入 `.bin` |
| `OUTPUT_CSV` | 主 CSV；空 → `<input_stem>.csv` |
| `BYTEORDER` | `big` / `little` |
| `OUTPUT_STYLE` | `dump` / `full` |
| `WRITE_FILTERED_CSV` | 写 `_data.csv`（默认 True） |
| `WRITE_DELIM_REPORT` | 写 `_delim_report.csv`（默认 True） |

---

## 命令行

```bash
python bin_to_64bit_csv.py
python bin_to_64bit_csv.py input.bin -o output.csv
python bin_to_64bit_csv.py input.bin --no-filtered
python bin_to_64bit_csv.py input.bin --no-delim-report
python bin_to_64bit_csv.py input.bin --byteorder big
```

| 参数 | 说明 |
|------|------|
| `-o`, `--output` | 主 CSV 路径 |
| `--no-filtered` | 不写 `_data.csv` |
| `--no-delim-report` | 不写 `_delim_report.csv` |
| `--filtered-suffix` | 默认 `_data` |
| `--delim-report-suffix` | 默认 `_delim_report` |

---

## Python API

```python
from bin_to_64bit_csv import convert_bin_to_csv, find_delimiter_blocks, parse_frame_header_word

total, data, n_blocks = convert_bin_to_csv(
    r"D:\path\to\dump.bin",
    r"D:\path\to\dump.csv",
    byteorder="big",
)
```

---

## 依赖

- Python 3.6+，标准库 only

---

## Skill 元数据

- **描述**: `.bin` → 64-bit CSV；4-word delimiter 剔除与帧头丢数报告  
- **标签**: bin, dump, espwifi_modem_dump, delimiter, ABABABAB, 55555555, tx_adcdump
