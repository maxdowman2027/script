# xian_static_dpd — Xian 静态 DPD 训练流水线（MATLAB → Python）

## 概述

按 `dpd/20260804_3_data/xian_static_DPD_main1.m` **调用链 1:1** 移植。权威源为该目录下的 `.m`（`.m~` 为草稿：CFO 关闭、切片不同，仅作对照）。

## 数据流

```text
ILA CSV (ref / feedback / adc)
  → read_data / importfile20：组复数 + 2抽1（跳过 adc 语义；Python 仍可读 hex adc）
  → TX：313:313+7000（长度 7001）
  → RX：mat ``rx_data`` 的 1596:1596+7000
  → 双方再取 1:5500
  → gain_compensation（|TX|<800 区间 RMS 对齐）
  → 迭代(Niter=1)：
       frequency_offset_estimation（相关长度 5000，相位一次拟合 + 旋相）
       dc_compensation（窗 mean 去 DC；TX 用切片后原始 TX）
       fractional_delay_estimation（|conv| 抛物峰 + spline）
  → 再截 1000:end
  → static_dpd_memory（numLUT=1, estDelay=0, order=3）
  → amamplot（AM-AM / AM-PM）
```

## 默认输入（`dpd/20260804_3_data/`）

| 文件 | 用途 |
|------|------|
| `feedback_ref_gain1_168_gain2_127_iladata2.csv` | ILA ref/feedback |
| `iqxel_2412_gain1_168_gain2_127_short.mat` | 仪表 RX（变量 `rx_data`） |

## 模块说明

| 模块 | 作用 |
|------|------|
| `read_data.py` | 读 CSV 六列；hex 单元格容错；`tx=ref`，`rx=feedback`；`[::2]` |
| `gain_compensation.py` | 默认 `|TX|<800` 上匹配 RX RMS |
| `frequency_offset_estimation.py` | 默认 `corr_len=5000` |
| `dc_compensation.py` | 1-based `start=600`，`L=256` 去均值 |
| `fractional_delay_estimation.py` | STF 630 点 `|conv|` 抛物插值时延 |
| `static_dpd_memory.py` | 基 `y|y|^{m-1}` 最小二乘；LUT `Σ c_m x^m` |
| `amamplot.py` | AM-AM / AM-PM |
| `xian_static_dpd_main1.py` | 主流程 + CLI |

## 命令行

```bash
python dpd/xian_static_dpd_main1.py
python dpd/xian_static_dpd_main1.py --rx mat
python dpd/xian_static_dpd_main1.py --rx csv --no-cfo
python dpd/xian_static_dpd_main1.py -o dpd/output/xian_static_dpd --no-plot
```

## 产物（默认 `dpd/output/xian_static_dpd/`）

| 文件 | 说明 |
|------|------|
| `lut_table.npz` | `table_x`, `table_y` |
| `lut_x.txt` / `lut_real.txt` / `lut_imag.txt` | LUT 文本 |
| `PA-Rx_amam.pdf/.png` | AM-AM |
| `PA-Rx_ampm.pdf/.png` | AM-PM |
| `cfo_*.pdf` / `frac_delay_*.pdf` | 中间诊断图（未 `--no-plot`） |

## 与 MATLAB 对齐注意点

1. **DC 输入**：`dc_compensation(tx_data, pa_after_cfo)` 的 TX 是切片后**未做增益补偿**的原始 TX。
2. **DPD 输入**：`tx_data_gain` 与分数时延后的 RX，再截 `1000:end`。
3. **mat 变量**：新数据为 `rx_data`；旧数据 `pa_data` 仍兼容。
4. **`.m~` 差异**：草稿关闭 CFO、RX 窗 `1596:1596+8000`、再 `313:8000`；正式 `.m` 为准，可用 `--no-cfo` 近似草稿。
