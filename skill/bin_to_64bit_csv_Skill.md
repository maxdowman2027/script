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
  → <stem>.csv（#dump_data 列，每行 0x + 16 位 hex）
  → tx_adcdump_data_parse.py（按 bit 字段提取 I/Q 等有符号数）
  → parse_64bit_data.py（可选：再拆低/高 32-bit 与 sample_i/q）
```

---

## 输入 / 输出

| 项目 | 说明 |
|------|------|
| 输入 | 任意 `.bin`；文件长度应为 8 的整数倍（余数 &lt; 8 字节会警告并丢弃） |
| 默认字节序 | **big-endian** uint64（适配 `espwifi_modem_dump` 类 dump） |
| 默认输出 | 与输入同目录、同 stem + `.csv` |

### 输出样式 `dump`（默认）

与现有 ADC dump CSV 兼容：

```csv
#dump_data 
0x7C3FF67DBFF20900,
0x7C8FF67EFFF10900,
...
```

- 表头行：`#dump_data `（末尾有空格，与历史 dump 一致）
- 每行：`0x` + **16 位大写十六进制** + 逗号

### 输出样式 `full`

标准 CSV 表头，含扩展列：

| 列 | 说明 |
|----|------|
| `index` | 从 0 开始的 word 序号 |
| `dump_data` | `0x` + 16 位 hex |
| `uint64_dec` | 十进制无符号 64 位值 |
| `uint64_hex` | 同上 hex |
| `low32_hex` | 低 32 位 hex |
| `high32_hex` | 高 32 位 hex |

---

## 配置区（脚本顶部）

| 变量 | 含义 |
|------|------|
| `INPUT_BIN` | 默认输入 `.bin` 路径 |
| `OUTPUT_CSV` | 输出 CSV；空 → `<input_stem>.csv` |
| `BYTEORDER` | `big` / `little`（默认 `big`） |
| `OUTPUT_STYLE` | `dump` / `full` |
| `CHUNK_WORDS` | 流式读写块大小（64-bit word 数，默认 8192） |

---

## 命令行

```bash
python bin_to_64bit_csv.py
python bin_to_64bit_csv.py "D:\test_data\E22_M2\260604\espwifi_modem_dump.20260604-033842-003.bin"
python bin_to_64bit_csv.py input.bin -o output.csv
python bin_to_64bit_csv.py input.bin --style full
python bin_to_64bit_csv.py input.bin --byteorder little
python bin_to_64bit_csv.py -h
```

| 参数 | 说明 |
|------|------|
| `input_bin` | 输入 `.bin`（可选，默认用配置区 `INPUT_BIN`） |
| `-o`, `--output` | 输出 CSV 路径 |
| `--byteorder` | `big` / `little` |
| `--style` | `dump` / `full` |
| `--chunk-words` | 流式块大小 |

---

## Python API

```python
from bin_to_64bit_csv import convert_bin_to_csv

n = convert_bin_to_csv(
    r"D:\path\to\dump.bin",
    r"D:\path\to\dump.csv",
    byteorder="big",
    output_style="dump",
)
print(n)  # 写入的 64-bit word 数
```

---

## 与相关脚本的关系

| 脚本 | 关系 |
|------|------|
| `tx_adcdump_data_parse.py` | **下游**：读 `#dump_data` 列，按 `[high:low]` 提取有符号 I/Q |
| `parse_64bit_data.py` | **可选下游**：读已含 hex 的文本 CSV，拆低/高 32-bit 与 12-bit sample |
| `process_ila_files.py` | 无关（ILA ZIP → waveform.csv） |

---

## 依赖

- Python 3.6+
- 标准库 only（`struct`, `csv`, `argparse`）

---

## 常见问题

**Q: 转换后 word 数不对？**  
A: 检查文件大小是否被 8 整除；若有 trailing bytes，脚本会 stderr 警告。

**Q: hex 与示波器 / 抓包工具不一致？**  
A: 尝试 `--byteorder little`；`espwifi_modem_dump` 默认用 **big**。

**Q: 下一步如何得到 I/Q？**  
A: 将生成的 CSV 设为 `tx_adcdump_data_parse.py` 的 `input_file`，配置 `bit_fields` / `column_names`。

---

## Skill 元数据

- **描述**: `.bin` → 64-bit `#dump_data` CSV；衔接 ADC dump 解析流水线  
- **标签**: bin, dump, 64-bit, espwifi_modem_dump, #dump_data, tx_adcdump, E22
