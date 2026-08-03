# xian_static_dpd — Xian 静态 DPD 训练流水线（MATLAB → Python）

## 概述

本目录将 `dpd/xian_static_DPD_main1.m` **按调用链 1:1 移植**为 Python。仅移植主脚本**实际调用**的函数；`static_DPD.m`、`psdPlot.m` 等未在主路径上的文件未移植。

源 MATLAB 目录：`D:\users\gxu\scripts\dpd\`

## 数据流

```text
ILA CSV (ref / feedback / adc)
  → read_data：组复数 + 2抽1
  → TX 从样点 89 起截断
  → RX/PA：优先 .mat(pa_data)，否则 .txt 或 CSV feedback
  → 双方截取 231:7000
  → gain_compensation（|TX|<1000 区间 RMS 对齐）
  → 迭代(Niter=1)：
       frequency_offset_estimation（相关相位一次拟合 + 旋相）
       dc_compensation（窗 mean 去 DC；TX 用切片后原始 TX）
       fractional_delay_estimation（|conv| 抛物峰 + spline）
  → 再截 1000:end
  → static_dpd_memory（多项式逆映射 → LUT）
  → amamplot（AM-AM / AM-PM）
```

物理地址类比：LUT 横轴为幅度 `delta…maxTableValue`，默认 `maxTableValue=1023`，`tableSize=32`。

## 模块说明

| 模块 | 作用 |
|------|------|
| `read_data.py` | 读 CSV 六列；`tx=ref_i+j*ref_q`，`rx=fb_i+j*fb_q`，`adc=adc_i+j*adc_q`；`[::2]` |
| `gain_compensation.py` | 低幅度 TX 样本上匹配 RX RMS |
| `frequency_offset_estimation.py` | `unwrap(angle(tx*conj(pa)))` 一次拟合，PA×e^{jφ̂} |
| `dc_compensation.py` | 1-based `start=600`，`L=256` 去均值 |
| `fractional_delay_estimation.py` | STF 630 点 `|conv|` 抛物插值时延，整段 cubic 重采样 |
| `static_dpd_memory.py` | 基 `y|y|^{m-1}` 最小二乘；LUT `Σ c_m x^m` |
| `amamplot.py` | AM-AM / AM-PM 散点 + LUT；可选存 PDF/PNG |
| `xian_static_dpd_main1.py` | 主流程 + CLI |

## 输入 CSV 列

```
adc_i, adc_q, feedback_q, feedback_i, ref_i, ref_q
```

默认文件：`dpd/gain168_test_data_3.csv`。

## RX/PA 来源

MATLAB 主脚本在读 CSV 后用 `gain168_iqxel_short_data.mat` 的 `pa_data` **覆盖** CSV feedback。仓库中可能没有该 `.mat`，Python 提供：

| `--rx` | 含义 |
|--------|------|
| `auto`（默认） | 有 mat 用 mat，否则 txt，再否则 CSV feedback |
| `mat` | 仅 `.mat` |
| `txt` | `gain168_iqxel_data.txt`，`--txt-stride` 默认 6 |
| `csv` | ILA feedback（无仪表数据时联调） |

## 命令行

```bash
# 无 mat 时用 CSV feedback 跑通流水线
python dpd/xian_static_dpd_main1.py --rx csv

# 与 MATLAB 一致：指定 mat
python dpd/xian_static_dpd_main1.py --rx mat --mat D:\path\to\gain168_iqxel_short_data.mat

# 大 txt + stride
python dpd/xian_static_dpd_main1.py --rx txt --txt-stride 6

# 输出目录、关闭中间图
python dpd/xian_static_dpd_main1.py --rx csv -o dpd/output/xian_static_dpd --no-plot
```

## 产物（默认 `dpd/output/xian_static_dpd/`）

| 文件 | 说明 |
|------|------|
| `lut_table.npz` | `table_x`, `table_y` |
| `lut_x.txt` / `lut_real.txt` / `lut_imag.txt` | LUT 文本 |
| `PA-Rx_amam.pdf/.png` | AM-AM |
| `PA-Rx_ampm.pdf/.png` | AM-PM |
| `cfo_*.pdf` / `frac_delay_*.pdf` | 中间诊断图（未 `--no-plot`） |

## 与 MATLAB 行为对齐的注意点

1. **DC 输入**：`dc_compensation(tx_data, pa_after_cfo)` 的 TX 是切片后**未做增益补偿**的原始 TX（与 .m 一致）。
2. **DPD 输入**：`tx_data_gain`（增益后、未 DC）与分数时延后的 RX，再截 `1000:end`。
3. **相位**：MATLAB `phase` ≈ `np.unwrap(np.angle(...))`。
4. **分数时延**：`interp1(...,'spline')` → `scipy.interpolate.interp1d(..., kind='cubic')` 分实部/虚部。
5. **未移植**：`psdPlot` / `static_DPD`（主脚本已注释）等旁路工具。

## API 示例

```python
from dpd.xian_static_dpd_main1 import run_pipeline

out = run_pipeline(rx_prefer="csv", plot=False)
table_x, table_y = out["table_x"], out["table_y"]
```
