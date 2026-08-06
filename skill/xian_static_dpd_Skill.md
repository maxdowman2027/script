# xian_static_dpd — Xian 静态 DPD 训练流水线（MATLAB → Python）

## 概述

按 `dpd/20260804_3_data/xian_static_DPD_main1.m` **调用链 1:1** 移植，并增加 **包络互相关自动粗对齐**（解决默认 `rx_slice_start` 与抓数起点不一致的问题）。

入口：`dpd/xian_static_dpd_main1.py`。

## 数据流

```text
ILA CSV (adc_i/q, feedback_q/i, ref_i/q)
  → read_data：组复数 + 2抽1（hex 容错）
  → TX：--tx-source ref|adc|auto，切 tx_slice_start:+slice_len
  → RX：
       · txt/mat：load 全捕获 → 【全局】|TX| 包络相关找最佳起点 → 取 slice_len
       · feedback/csv：同 CSV 时间轴，±coarse-max-lag 搜 Δ 后对齐
  → residual 整数样点 refine → align_len
  → align_time_domain 图（可 --align-plot-start/end）
  → gain_compensation（|TX|<800）
  → CFO（cfo_*_before/after）→ DC → fractional delay
  → trim 1000:end → static_dpd_memory
  → lut_table.npz / lut_*.txt / lut_data_map.py（×128 取整）
  → amamplot
```

## 自动对齐（重要）

| 模式 | 行为 |
|------|------|
| iQxel（默认） | 在 RX 前 `--coarse-search-len`（默认 500000）点内做 **全局** `\|TX\|` 模板相关，选 score 最大起点；忽略错误的固定 `1596` hint |
| `--coarse-local-only` | 仅在 `--rx-slice-start` ± `--coarse-max-lag` 内搜 |
| `--rx feedback` | 相对 TX 同窗搜 ±`coarse-max-lag`，补偿 feedback 固定样点偏置（如 +11） |
| `--no-coarse-align` | 关闭；严格用 `--rx-slice-start` / 同窗 |

日志示例：

```text
[ALIGN] auto envelope (global search_len=500000): rx_slice → 234, score=0.9777  (hint was 1596)
[ALIGN] coarse envelope (feedback): Δ=+11 samples (search ±512)
```

典型失败原因（旧逻辑）：只在 hint±512 搜，真实起点在 234 等远处时对不齐 → 现已默认全局搜。

## 默认输入（`dpd/20260804_3_data/`）

| 文件 | 用途 |
|------|------|
| `feedback_ref_gain1_168_gain2_127_iladata2.csv` | ILA |
| `iqxel_2412_gain1_168_gain2_127_short.mat` | 仪表 RX（`rx_data` / `pa_data`） |

## 模块说明

| 模块 | 作用 |
|------|------|
| `read_data.py` | CSV + `load_iqxel_txt`（LitePoint 头 / 160Msps→stride 2） |
| `xian_static_dpd_main1.py` | 主流程、`find_best_rx_start_envelope`、`write_lut_data_map` |
| `gain_compensation.py` | `|TX|<800` RMS |
| `frequency_offset_estimation.py` | CFO + 存 before/after 图 |
| `dc_compensation.py` / `fractional_delay_estimation.py` | DC / 分数时延 |
| `static_dpd_memory.py` / `amamplot.py` | LUT / AM 图 |

## TX / RX 数据源

| 参数 | 取值 | 说明 |
|------|------|------|
| `--tx-source` | `ref` / `adc` / `auto` | CSV TX；ref 空时常回退 adc |
| `--rx` | `txt` / `mat` / `feedback`/`csv` / `auto` | 仪器或片上 feedback |

## 参考命令

仓库根：`cd D:\users\gxu\scripts`。

### 1) 默认仓库数据

```bash
python dpd/xian_static_dpd_main1.py
python dpd/xian_static_dpd_main1.py -o dpd/output/xian_static_dpd
```

### 2) iQxel + 全局自动对齐（推荐）

```powershell
python .\dpd\xian_static_dpd_main1.py `
  --csv "D:\test_data\AP\260806_dpd\chan5180\feedback_ref_iladata.csv" `
  --txt "D:\test_data\AP\260806_dpd\chan5180\iqxel_5180_gain1_128_gain2_127.txt" `
  --rx txt --tx-source ref `
  --align-plot-start 5700 --align-plot-end 6400 `
  -o "D:\users\gxu\scripts\dpd\output\260806\chan5180"
```

### 3) ref 为空 → ADC + iQxel

```powershell
python .\dpd\xian_static_dpd_main1.py `
  --csv "PATH\iladata.csv" --txt "PATH\iqxel.txt" `
  --rx txt --tx-source adc -o OUT
```

### 4) ILA 片上 ref vs feedback（自动 Δ）

```powershell
python .\dpd\xian_static_dpd_main1.py `
  --csv "D:\test_data\AP\260806_dpd\2\feedback_ref_iladata_tmp.csv" `
  --rx feedback --tx-source ref `
  --align-plot-start 5700 --align-plot-end 6400 `
  -o "D:\users\gxu\scripts\dpd\output\260806\2\adc"
```

### 5) 对齐相关开关

```bash
# 扩大/缩小全局搜索长度
python dpd/xian_static_dpd_main1.py ... --coarse-search-len 800000

# 仅在 hint 附近搜（旧行为）
python dpd/xian_static_dpd_main1.py ... --coarse-local-only --rx-slice-start 1596 --coarse-max-lag 512

# 关闭自动对齐，手写起点
python dpd/xian_static_dpd_main1.py ... --no-coarse-align --rx-slice-start 234

# 对齐图缩放窗
python dpd/xian_static_dpd_main1.py ... --align-plot-start 2200 --align-plot-end 2500
```

### 6) CFO / LUT

```bash
python dpd/xian_static_dpd_main1.py ... --no-cfo
python dpd/xian_static_dpd_main1.py ... --lut-map-scale 128 --num-lut 1 --est-delay 0 --order 3
python dpd/xian_static_dpd_main1.py ... --txt-stride 0   # 0=按 SamplingRate 自动
```

### 7) 从 npz 生成 wifi7 字典

```python
from pathlib import Path
import numpy as np
from dpd.xian_static_dpd_main1 import write_lut_data_map
z = np.load(r"OUT/lut_table.npz")
write_lut_data_map(z["table_y"], Path(r"OUT/lut_data_map.py"), scale=128)
```

## CLI 参数速查

| 参数 | 默认 | 含义 |
|------|------|------|
| `--csv` / `--txt` / `--mat` | 仓库默认 | 输入 |
| `--rx` | `auto` | `txt`/`mat`/`feedback`/`csv`/`auto` |
| `--tx-source` | `auto` | `ref`/`adc`/`auto` |
| `--tx-slice-start` | `313` | TX 起点（1-based，2抽1后） |
| `--rx-slice-start` | `1596` | hint；全局对齐时仅作日志对照 |
| `--slice-len` / `--align-len` | `7001` / `7000` | 切片 / 对齐长度 |
| `--align-plot-start/end` | `5000`/`7000` | 时域对齐图窗口 |
| `--coarse-search-len` | `500000` | iQxel 全局搜索长度 |
| `--coarse-max-lag` | `512` | feedback / local-only 半径 |
| `--coarse-local-only` | off | 禁用全局、只用 hint±lag |
| `--no-coarse-align` | off | 关闭自动对齐 |
| `--lut-map-scale` | `128` | 字典定点 |
| `--no-cfo` / `--no-plot` / `-o` | — | CFO / 少图 / 输出目录 |

## 产物（`-o`）

| 文件 | 说明 |
|------|------|
| `align_time_domain.png/.pdf` | 粗对齐后时域（调窗用） |
| `cfo_iter*_before/after.png/.pdf` | CFO 相位 |
| `lut_table.npz` / `lut_*.txt` | LUT |
| `lut_data_map.py` | `lut_data_map_lut{k}`，`round(LUT×scale)`，索引 0 为零点 |
| `PA-Rx_amam/ampm.*` | AM-AM / AM-PM |

```python
import numpy as np
z = np.load(r"OUT/lut_table.npz")
table_x, table_y = z["table_x"], z["table_y"]
```

## 与 MATLAB 对齐注意点

1. DC：`dc_compensation` 的 TX 为切片后未增益补偿的原始 TX。  
2. DPD：`tx_data_gain` + 分数时延后 RX，再 `1000:end`。  
3. mat：`rx_data`（新）/ `pa_data`（旧）。  
4. 自动对齐为 Python 增强：MATLAB 固定切片；跨抓数请依赖全局搜索或看 `align_time_domain`。  
5. 片上 feedback：`--rx feedback --tx-source ref`。
