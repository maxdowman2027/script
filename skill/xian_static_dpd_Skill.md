# xian_static_dpd — Xian 静态 DPD 训练流水线（MATLAB → Python）

## 概述

按 `dpd/20260804_3_data/xian_static_DPD_main1.m` **调用链 1:1** 移植。权威源为该目录下的 `.m`（`.m~` 为草稿：CFO 关闭、切片不同，仅作对照）。

入口脚本：`dpd/xian_static_dpd_main1.py`。

## 数据流

```text
ILA CSV (adc_i/q, feedback_q/i, ref_i/q)
  → read_data：组复数 + 2抽1（hex 单元格容错）
  → TX：--tx-source ref|adc|auto，再切 tx_slice_start : +slice_len
  → RX：
       · --rx txt/mat → iQxel（rx_slice_start 窗；txt 支持 LitePoint 头，stride 0=按 160Msps 自动 2抽1）
       · --rx feedback|csv → CSV feedback_i/q（与 TX 同窗，片上对比）
  → align_len 截齐 → align_time_domain 图（默认画 [5000,7000)）
  → gain_compensation（|TX|<800）
  → 迭代：CFO（出 before/after 图）→ DC → fractional delay
  → trim 1000:end → static_dpd_memory
  → lut_table.npz / lut_*.txt / lut_data_map.py（×128 取整，wifi_dpd_test_wifi7 字典格式）
  → amamplot
```

## 默认输入（`dpd/20260804_3_data/`）

| 文件 | 用途 |
|------|------|
| `feedback_ref_gain1_168_gain2_127_iladata2.csv` | ILA ref/feedback/adc |
| `iqxel_2412_gain1_168_gain2_127_short.mat` | 仪表 RX（变量 `rx_data`，兼容 `pa_data`） |

## 模块说明

| 模块 | 作用 |
|------|------|
| `read_data.py` | CSV 六列 + `load_iqxel_txt`（LitePoint / 无头 I,Q） |
| `gain_compensation.py` | 默认 `|TX|<800` RMS 对齐 |
| `frequency_offset_estimation.py` | `corr_len=5000`；可写 `cfo_*_before/after.png` |
| `dc_compensation.py` | 窗 mean 去 DC |
| `fractional_delay_estimation.py` | `|conv|` 抛物峰 + cubic 重采样 |
| `static_dpd_memory.py` | 多项式逆映射 → LUT |
| `amamplot.py` | AM-AM / AM-PM（空 TX 时跳过 polyfit） |
| `xian_static_dpd_main1.py` | 主流程 + CLI + `write_lut_data_map` |

## TX / RX 数据源

| 参数 | 取值 | 说明 |
|------|------|------|
| `--tx-source` | `ref` | CSV `ref_i + 1j*ref_q` |
| | `adc` | CSV `adc_i + 1j*adc_q`（ref 全 0 时常用） |
| | `auto` | ref 有能量用 ref；`--rx feedback` 时优先 ref；否则回退 adc |
| `--rx` | `txt` | LitePoint / 无头 I,Q txt |
| | `mat` | `*.mat` 的 `rx_data` / `pa_data` |
| | `feedback` / `csv` | ILA `feedback_i/q`，与 TX **同一切片窗**（片上对比） |
| | `auto` | 自定义 `--txt` 优先 txt；否则 mat→txt→csv |

## 参考命令

在仓库根目录执行：`cd D:\users\gxu\scripts`。

### 1) 默认数据（仓库内 20260804_3_data）

```bash
python dpd/xian_static_dpd_main1.py
python dpd/xian_static_dpd_main1.py -o dpd/output/xian_static_dpd
```

### 2) iQxel txt 作 RX，CSV ref 作 TX（仪器反馈）

```bash
python dpd/xian_static_dpd_main1.py ^
  --csv "D:\test_data\AP\260805_dpd\2\txpwr20_gain1_144_gain2_127_iladata.csv" ^
  --txt "D:\test_data\AP\260805_dpd\2\iqxel\iqxel_txpwr20_gain1_144_gain2_127.txt" ^
  --rx txt --tx-source ref ^
  -o dpd/output/xian_static_dpd
```

PowerShell：

```powershell
python .\dpd\xian_static_dpd_main1.py `
  --csv "D:\test_data\AP\260805_dpd\2\txpwr20_gain1_144_gain2_127_iladata.csv" `
  --txt "D:\test_data\AP\260805_dpd\2\iqxel\iqxel_txpwr20_gain1_144_gain2_127.txt" `
  --rx txt --tx-source ref `
  -o dpd/output/xian_static_dpd
```

### 3) ref 为空时用 ADC 作 TX + iQxel

```bash
python dpd/xian_static_dpd_main1.py --csv PATH\iladata.csv --txt PATH\iqxel.txt --rx txt --tx-source adc
```

### 4) ILA 片上对比：ref vs feedback_i/q

```bash
python dpd/xian_static_dpd_main1.py --csv PATH\iladata.csv --rx feedback --tx-source ref
# 等价：--rx csv
```

### 5) 调切片 / 对齐窗（看 align_time_domain）

```bash
python dpd/xian_static_dpd_main1.py --csv PATH\iladata.csv --txt PATH\iqxel.txt --rx txt --tx-source ref ^
  --tx-slice-start 313 --rx-slice-start 1596 --slice-len 7001 --align-len 7000 ^
  --align-plot-start 5000 --align-plot-end 7000
```

### 6) CFO / LUT / 其它开关

```bash
# 关闭 CFO（近似 .m~ 草稿）
python dpd/xian_static_dpd_main1.py --csv PATH --rx feedback --tx-source ref --no-cfo

# LUT 字典缩放（默认 ×128 取整 → lut_data_map.py）
python dpd/xian_static_dpd_main1.py --csv PATH --rx feedback --lut-map-scale 128

# iQxel 抽稀：0=按 SamplingRate 自动；2=160Msps→80M
python dpd/xian_static_dpd_main1.py --txt PATH\iqxel.txt --rx txt --txt-stride 0

# 关闭中间 frac 等图（align / CFO 图仍会写）
python dpd/xian_static_dpd_main1.py --no-plot -o dpd/output/xian_static_dpd

# LUT 阶数 / 记忆
python dpd/xian_static_dpd_main1.py --num-lut 1 --est-delay 0 --order 3
python dpd/xian_static_dpd_main1.py --num-lut 3 --est-delay 1 --order 3
```

### 7) 仅从已有 `table_y` 生成字典（Python API）

```python
from pathlib import Path
import numpy as np
from dpd.xian_static_dpd_main1 import write_lut_data_map

z = np.load(r"dpd/output/xian_static_dpd/lut_table.npz")
write_lut_data_map(z["table_y"], Path(r"dpd/output/xian_static_dpd/lut_data_map.py"), scale=128)
```

外部 MATLAB 风格 `lut0.txt`（`a+bi` 行）批量转字典时，可对目录内 `lut*.txt` 解析后调用同一 `write_lut_data_map`。

## CLI 参数速查

| 参数 | 默认（约） | 含义 |
|------|------------|------|
| `--csv` | `20260804_3_data/...iladata2.csv` | ILA CSV |
| `--rx` | `auto` | `mat`/`txt`/`feedback`/`csv`/`auto` |
| `--txt` / `--mat` | 仓库默认路径 | iQxel 文件 |
| `--txt-stride` | `0`（auto） | txt 抽稀 |
| `--tx-source` | `auto` | `ref`/`adc`/`auto` |
| `--tx-slice-start` | `313` | TX 起点（1-based，2抽1后） |
| `--rx-slice-start` | `1596` | iQxel 起点（feedback 模式忽略） |
| `--slice-len` | `7001` | 切片长度 |
| `--align-len` | `7000` | 对齐后保留长度 |
| `--align-plot-start/end` | `5000`/`7000` | 对齐时域图窗口 |
| `--lut-map-scale` | `128` | `lut_data_map` 定点缩放 |
| `--no-cfo` | off | 跳过 CFO |
| `--no-plot` | off | 少画中间图（align/CFO 仍保存） |
| `-o` | `dpd/output/xian_static_dpd` | 输出目录 |

## 产物（`-o` 目录）

| 文件 | 说明 |
|------|------|
| `lut_table.npz` | `table_x`, `table_y` |
| `lut_x.txt` / `lut_real.txt` / `lut_imag.txt` | LUT 浮点文本 |
| `lut_data_map.py` | `lut_data_map_lut{k}`，索引 0 为零点，1..32 为 `round(LUT×scale)` |
| `align_time_domain.png/.pdf` | 粗对齐时域（可缩放窗） |
| `cfo_iter*_before/after.png/.pdf` | CFO 补偿前后相位（启用 CFO 时） |
| `PA-Rx_amam/ampm.png/.pdf` | AM-AM / AM-PM |
| `frac_delay_*.pdf` | 分数时延诊断（未 `--no-plot`） |

打开 npz：

```python
import numpy as np
z = np.load(r"dpd/output/xian_static_dpd/lut_table.npz")
table_x, table_y = z["table_x"], z["table_y"]
```

## 与 MATLAB 对齐注意点

1. **DC 输入**：`dc_compensation(tx_data, pa_after_cfo)` 的 TX 是切片后**未做增益补偿**的原始 TX。
2. **DPD 输入**：`tx_data_gain` 与分数时延后的 RX，再截 `1000:end`。
3. **mat 变量**：新数据 `rx_data`；旧数据 `pa_data` 仍兼容。
4. **`.m~` 差异**：草稿关 CFO；正式 `.m` 为准，可用 `--no-cfo`。
5. **片上 feedback 对比**：`--rx feedback --tx-source ref`，两端同窗；勿再用独立 `--rx-slice-start`。
