# parse_60bit_40bit_2ant_iq.py — 双天线 10-bit I/Q（2×64→3×40）

## 脚本概述

`parse_60bit_40bit_2ant_iq.py` 解析 E22 modem **双天线 10-bit** dump：每个 64-bit word 去掉最高 4 bit `[63:60]`，每 **2 个 60-bit** 拼成 **120-bit**，再切出 **3 个 40-bit** 样本。接口与 `dump_64bit_to_iq8.py` 类似（流式、目录批量、默认输出原始 hex 列）。

适用于 phymode20/40/80 **2ant** 等场景；**不要**用 `dump_64bit_to_iq8.py` 的 single 模式代替本脚本处理 10-bit 组包数据。

---

## 64-bit → 40-bit 规则

### 步骤 1：去顶 4 bit

```text
uint64 [63:60] 丢弃，保留 [59:0] 作为 60-bit payload
```

### 步骤 2：2 × 60-bit → 3 × 40-bit

对连续两行 w0、w1（均已 to_60bit）：

| 样本 | 位域 | 说明 |
|------|------|------|
| s0 | `w0[39:0]` | 仅第一行 |
| s1 | `{w1[19:0], w0[59:40]}` | **上一行 w0 在低位** |
| s2 | `w1[59:20]` | 仅第二行 |

尾部余 1 个 64-bit word 会打印 `[WARN]` 并忽略。

### 步骤 3：40-bit → 四路 10-bit 有符号 I/Q

| 位域 | 列名 |
|------|------|
| [9:0] | `ch0_sample_q` |
| [19:10] | `ch0_sample_i` |
| [29:20] | `ch1_sample_q` |
| [39:30] | `ch1_sample_i` |

---

## 输入 / 输出

| 项 | 说明 |
|----|------|
| 输入 | `*_data.csv`（`#dump_data` 列） |
| 默认输出 | `<stem>_2ant_iq.csv` |
| 行数 | `floor(N_64bit / 2) × 3` |

输出列（默认）：

```text
dump_data_40, ch0_sample_q, ch0_sample_i, ch1_sample_q, ch1_sample_i
```

---

## 配置区

| 变量 | 默认 | 含义 |
|------|------|------|
| `KEEP_DUMP_DATA_40` | True | 输出 `dump_data_40` |
| `RUN_VERIFY` | False | 逐组 bitstream 校验 |
| `OUTPUT_SUFFIX` | `_2ant_iq` | 输出后缀 |

---

## 命令行

```bash
python parse_60bit_40bit_2ant_iq.py D:\path\to\*_data.csv

python parse_60bit_40bit_2ant_iq.py input_data.csv --verify

python parse_60bit_40bit_2ant_iq.py csv_folder -o D:\path\to\out

python parse_60bit_40bit_2ant_iq.py input.csv --no-dump-data-40
```

| 参数 | 说明 |
|------|------|
| `input_csv` | 文件或目录 |
| `-o` | 输出 CSV 或目录 |
| `--keep-dump-data-40` | 保留 40-bit hex（默认开） |
| `--no-dump-data-40` | 仅 I/Q 四列 |
| `--verify` | 开启 64→40 拆包校验 |

别名：`parse_64bit_to_2ant_iq10`（函数名）

---

## 数据流

```text
espwifi_modem_dump.bin
  → bin_to_64bit_csv.py → *_data.csv
  → parse_60bit_40bit_2ant_iq.py → *_2ant_iq.csv
  → plot_psd_2462.py --mode 2ant --bit-width 10 --fs 320e6 [--upsample 2]
```

与 8-bit 路径对比：

| 项目 | dump_64bit_to_iq8 (2ant) | parse_60bit_40bit_2ant_iq |
|------|--------------------------|---------------------------|
| 位宽 | 8-bit | 10-bit |
| 分组 | 1×64 → 2 样本 | 2×64 → 3 样本 |
| 去 [63:60] | 否 | 是 |
| 输出后缀 | `_iq8` | `_2ant_iq` |

---

## 依赖

标准库 + `csv`

---

## 元数据

- **脚本**: `parse_60bit_40bit_2ant_iq.py`
- **标签**: 2ant, 10bit, 40bit, 60bit, dual_antenna, modem_dump, ch0, ch1
