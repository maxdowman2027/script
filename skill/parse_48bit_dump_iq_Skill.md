# parse_48bit_dump_iq.py — 48-bit AXI dump I/Q 解析

## 脚本概述

`parse_48bit_dump_iq.py` 读取 **64-bit `#dump_data` CSV**（如 `bin_to_64bit_csv.py` 生成的 `*_data.csv`），按 **48-bit 位流** 从 64-bit word 中拆出采样，再将每个 48-bit word 解码为 **3 路 8-bit 有符号 I/Q**。

适用于 E22 **160M AXI dump** 等场景：硬件以 48-bit 容器打包 IQ，存储/传输时按 64-bit word 对齐。

典型输入：

`D:\test_data\E22_M2\260605\axi_dump_160M_data_parse\espwifi_modem_dump.20260605-065335-001_data.csv`

---

## 数据流位置

```text
espwifi_modem_dump .bin
  → bin_to_64bit_csv.py
  → <stem>_data.csv（64-bit #dump_data，已去 delimiter）
  → parse_48bit_dump_iq.py
  → <stem>_data_48bit_parse.csv（6 列 I/Q，每 48-bit 一行）
  → [可选 --merge-iq] <stem>_iq_merged.csv（sample_i / sample_q 连续流）
  → plot_psd_2462.py / 频谱分析
```

与 64-bit 三 tap 路径对比：

| 路径 | 64-bit 直接解析 | 48-bit 拆包路径 |
|------|-----------------|-----------------|
| 解析脚本 | `tx_adcdump_data_parse.py` | **`parse_48bit_dump_iq.py`** |
| 展平 I/Q | `merge_dump_3data_iq.py` | **`--merge-iq`** |
| 每 storage word 有效采样 | 1 x 64-bit（6 x 10/12-bit 等） | 3 x 64-bit → 4 x 48-bit → 12 x 8-bit I/Q |

---

## 64-bit → 48-bit 拆包规则

每 **3 个连续 uint64**（w0, w1, w2）生成 **4 个 uint48**（192 bit = 3×64 = 4×48）：

| 48-bit | 位域组成 | 说明 |
|--------|----------|------|
| s0 | `w0[47:0]` | 第一个 64-bit 的低 48 bit |
| s1 | `{w1[31:0], w0[63:48]}` | **w1[31:0] 为高位**，w0[63:48] 为低位 |
| s2 | `{w2[15:0], w1[63:48], w1[47:32]}` | 跨 w1/w2 拼接 |
| s3 | `{w2[63:48], w2[47:32], w2[31:16]}` | 取自 w2 高 48 bit（跳过 w2[15:0]） |

下一组从 w3 开始重复上述模式（s4 = w3[47:0]，s5 用 w3/w4，…）。

**尾部处理**：输入 64-bit word 数若不是 3 的整数倍，末尾 1–2 个 word 会被跳过并打印 `[WARN]`。

---

## 48-bit → I/Q 字段（8-bit 有符号）

每个 48-bit sample 含 **3 路 I/Q**，每路 **8-bit 二进制补码**：

| 位域 | 输出列 | 宽度 |
|------|--------|------|
| [7:0] | `sample_i_0` | 8-bit signed |
| [15:8] | `sample_q_0` | 8-bit signed |
| [23:16] | `sample_i_1` | 8-bit signed |
| [31:24] | `sample_q_1` | 8-bit signed |
| [39:32] | `sample_i_2` | 8-bit signed |
| [47:40] | `sample_q_2` | 8-bit signed |

---

## 输入 / 输出

### 输入

- CSV 首列 `#dump_data`（可含尾随空格；值形如 `0xXXXXXXXXXXXXXXXX,`）
- 每行一个 64-bit 十六进制 word

### 输出模式

| 模式 | 默认输出文件名 | 列 | 行数 |
|------|----------------|-----|------|
| 默认（6 列） | `<stem>_48bit_parse.csv` | **`dump_data_48`**, `sample_i_0` … `sample_q_2` | = 48-bit sample 数 |
| `--merge-iq` | `<stem>_iq_merged.csv` | **`dump_data_48`**, `sample_i`, `sample_q` | = 48-bit sample 数 × 3 |

可选列：

| 参数 | 增加列 |
|------|--------|
| `--keep-dump-data` | 源 64-bit `#dump_data`（所属 3-word 组的 w0） |

---

## 配置区（脚本顶部）

| 变量 | 含义 |
|------|------|
| `INPUT_CSV` | 默认输入 `*_data.csv` |
| `OUTPUT_CSV` | 输出路径；空 → 按模式自动命名 |
| `MERGE_IQ` | 默认 False；True 等同 `--merge-iq` |
| `KEEP_DUMP_DATA` | 保留源 64-bit `#dump_data` 列 |
| `DUMP_DATA_48_COL` | 固定为 `dump_data_48`，两种输出模式均写入 |

---

## 命令行

```bash
# 6 列 I/Q（每 48-bit 一行）
python parse_48bit_dump_iq.py

python parse_48bit_dump_iq.py D:\test_data\E22_M2\260605\axi_dump_160M_data_parse\espwifi_modem_dump.20260605-065335-001_data.csv

# 展平 I/Q 连续流（每 48-bit 拆 3 行，dump_data_48 三行相同）
python parse_48bit_dump_iq.py input_data.csv --merge-iq -o output_iq_merged.csv
```

| 参数 | 说明 |
|------|------|
| `input_csv` | 64-bit `#dump_data` CSV |
| `-o`, `--output` | 输出 CSV 路径 |
| `--merge-iq` | 输出 `dump_data_48` + `sample_i` / `sample_q` 连续流 |
| `--keep-dump-data` | 附带源 64-bit `#dump_data` 列 |

---

## Python API

```python
from parse_48bit_dump_iq import (
    parse_48bit_dump_iq,
    read_uint64_words,
    iter_48bit_from_uint64,
    decode_48bit_iq,
    unpack_group_to_48bit,
)

# 完整流程
n64, n_rows, skipped = parse_48bit_dump_iq(
    r"D:\path\to\input_data.csv",
    merge_iq=True,
)

# 低级：手动拆一组
w0, w1, w2 = 0x..., 0x..., 0x...
s0, s1, s2, s3 = unpack_group_to_48bit(w0, w1, w2)
iq = decode_48bit_iq(s0)  # dict: sample_i_0, sample_q_0, ...
```

---

## 示例统计（065335-001_data.csv）

| 项 | 值 |
|----|-----|
| 64-bit words | 56464（尾部 1 word 忽略） |
| 48-bit samples | 75284 |
| 6 列输出行 | 75284 |
| merge-iq 行 | 225852（75284 × 3 taps） |

---

## 依赖

- Python 3.6+，标准库 only

---

## Skill 元数据

- **描述**: 64-bit `#dump_data` CSV → 48-bit 拆包 → 3×8-bit I/Q；可选 merge 连续流  
- **标签**: 48bit, axi_dump, 160M, dump_data, sample_i, sample_q, iq, merge, espwifi_modem_dump
