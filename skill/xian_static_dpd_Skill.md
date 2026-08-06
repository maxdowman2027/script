# xian_static_dpd — Xian 静态 DPD 训练流水线（MATLAB → Python）

## 概述

按 `dpd/20260804_3_data/xian_static_DPD_main1.m` 调用链移植，并支持：

- **包络互相关自动粗对齐**（iQxel 全局搜起点；feedback 补偿样点偏置）
- **多种 ILA CSV 布局**：`feedback/ref` 与 **`dac_iladata`（dac_i/q）**
- `--tx-source ref|dac|adc|auto` 与仪器 / 片上 RX 对比

入口：`dpd/xian_static_dpd_main1.py`。

## 数据流

```text
ILA CSV（表头自动识别）
  · feedback_ref: adc_*, feedback_*, ref_*
  · dac:          adc_*, dac_*
  → read_data：组复数 + 2抽1
  → TX：--tx-source ref|dac|adc|auto
  → RX：txt/mat（全局包络找起点）或 feedback（±lag 对齐）
  → align_time_domain → gain → CFO → DC → frac delay
  → LUT / lut_data_map.py / amamplot
```

## CSV 布局

| layout | 列 | 典型用途 |
|--------|-----|----------|
| `feedback_ref` | `adc_i/q, feedback_q/i, ref_i/q` | ref/feedback 与 iQxel 或片上对比 |
| `dac` | `adc_i/q, dac_i/q` | **DAC 数字基带** vs iQxel |

日志：`[CSV] layout=dac  cols=[...]`

## TX / RX

| 参数 | 取值 | 说明 |
|------|------|------|
| `--tx-source` | `ref` | `ref_i+j*ref_q` |
| | `dac` | `dac_i+j*dac_q`（`dac_iladata.csv`） |
| | `adc` | `adc_i+j*adc_q` |
| | `auto` | 按能量：ref → dac → adc |
| `--rx` | `txt` / `mat` | iQxel |
| | `feedback` / `csv` | 同 CSV 的 feedback |
| | `auto` | 自定义 `--txt` 优先 txt |

## 自动对齐

| 模式 | 行为 |
|------|------|
| iQxel（默认） | 前 `--coarse-search-len`（默认 5e5）点 **全局** `\|TX\|` 相关 |
| `--rx feedback` | ±`--coarse-max-lag` 补偿相对 TX 的整数时延 |
| `--coarse-local-only` | 仅 hint±lag |
| `--no-coarse-align` | 关闭 |

## 参考命令

仓库根：`cd D:\users\gxu\scripts`。

### 1) DAC vs iQxel（推荐）

```powershell
python .\dpd\xian_static_dpd_main1.py `
  --csv "D:\test_data\AP\260806_dpd\4\dac_iladata.csv" `
  --txt "D:\test_data\AP\260806_dpd\4\iqxel_2412_gain1_128_gain2_127.txt" `
  --tx-source dac --rx txt `
  --align-plot-start 5700 --align-plot-end 6400 `
  -o "D:\users\gxu\scripts\dpd\output\260806\4_dac"
```

`auto` 在仅有 dac 能量时也会选 dac：

```powershell
python .\dpd\xian_static_dpd_main1.py --csv PATH\dac_iladata.csv --txt PATH\iqxel.txt --rx txt -o OUT
```

### 2) ref vs iQxel + 全局自动对齐

```powershell
python .\dpd\xian_static_dpd_main1.py `
  --csv "D:\test_data\AP\260806_dpd\chan5180\feedback_ref_iladata.csv" `
  --txt "D:\test_data\AP\260806_dpd\chan5180\iqxel_5180_gain1_128_gain2_127.txt" `
  --rx txt --tx-source ref `
  --align-plot-start 5700 --align-plot-end 6400 `
  -o "D:\users\gxu\scripts\dpd\output\260806\chan5180"
```

### 3) ref 空 → ADC + iQxel

```powershell
python .\dpd\xian_static_dpd_main1.py `
  --csv "PATH\iladata.csv" --txt "PATH\iqxel.txt" `
  --rx txt --tx-source adc -o OUT
```

### 4) ILA 片上 ref vs feedback

```powershell
python .\dpd\xian_static_dpd_main1.py `
  --csv "D:\test_data\AP\260806_dpd\2\feedback_ref_iladata_tmp.csv" `
  --rx feedback --tx-source ref `
  --align-plot-start 5700 --align-plot-end 6400 `
  -o "D:\users\gxu\scripts\dpd\output\260806\2\adc"
```

### 5) 对齐 / CFO / LUT 开关

```bash
python dpd/xian_static_dpd_main1.py ... --coarse-search-len 800000
python dpd/xian_static_dpd_main1.py ... --coarse-local-only --rx-slice-start 1596
python dpd/xian_static_dpd_main1.py ... --no-coarse-align --rx-slice-start 287
python dpd/xian_static_dpd_main1.py ... --no-cfo --lut-map-scale 128 --txt-stride 0
```

### 6) 默认仓库数据 / 从 npz 写字典

```bash
python dpd/xian_static_dpd_main1.py -o dpd/output/xian_static_dpd
```

```python
from pathlib import Path
import numpy as np
from dpd.xian_static_dpd_main1 import write_lut_data_map
z = np.load(r"OUT/lut_table.npz")
write_lut_data_map(z["table_y"], Path(r"OUT/lut_data_map.py"), scale=128)
```

## CLI 速查

| 参数 | 默认 | 含义 |
|------|------|------|
| `--csv` / `--txt` / `--mat` | 仓库默认 | 输入 |
| `--rx` | `auto` | `txt`/`mat`/`feedback`/`csv`/`auto` |
| `--tx-source` | `auto` | `ref`/`dac`/`adc`/`auto` |
| `--tx-slice-start` | `313` | TX 起点（1-based） |
| `--rx-slice-start` | `1596` | hint（全局对齐时仅对照） |
| `--slice-len` / `--align-len` | `7001`/`7000` | 切片长度 |
| `--align-plot-start/end` | `5000`/`7000` | 时域图窗 |
| `--coarse-search-len` | `500000` | iQxel 全局搜索 |
| `--coarse-max-lag` | `512` | feedback / local 半径 |
| `--coarse-local-only` / `--no-coarse-align` | off | 对齐模式 |
| `--lut-map-scale` | `128` | 字典定点 |
| `--no-cfo` / `--no-plot` / `-o` | — | CFO / 少图 / 输出 |

## 产物（`-o`）

| 文件 | 说明 |
|------|------|
| `align_time_domain.png/.pdf` | 粗对齐时域 |
| `cfo_iter*_before/after.*` | CFO 相位 |
| `lut_table.npz` / `lut_*.txt` / `lut_data_map.py` | LUT |
| `PA-Rx_amam/ampm.*` | AM-AM / AM-PM |

## 模块

| 模块 | 作用 |
|------|------|
| `read_data.py` | 双布局 CSV + `load_iqxel_txt` |
| `xian_static_dpd_main1.py` | 主流程 / 自动对齐 / `write_lut_data_map` |
| `gain_compensation.py` 等 | 增益 / CFO / DC / 分数时延 / LUT / 绘图 |

## 注意点

1. DC 用的 TX 是切片后、未增益补偿的原始 TX。  
2. DPD 输入：`tx_gain` + 分数时延后 RX，再 `1000:end`。  
3. `dac` 布局无 ref/feedback 时不要用 `--rx feedback`。  
4. 自动对齐为 Python 增强；看 `align_time_domain` 确认包络是否重合。
