# xian_static_dpd — Xian 静态 DPD 训练流水线（MATLAB → Python）

## 概述

按 `dpd/20260804_3_data/xian_static_DPD_main1.m` 调用链移植，并支持：

- **包络互相关自动粗对齐**（iQxel / `--dac-csv` **全局**搜起点；同 CSV feedback ±lag）
- **CW tone 模式**（`|TX|` 平坦时自动）：复数去直流对齐、估频、I/Q 与 `tone_spectrum` 图
- **多种 ILA CSV 布局**：`feedback/ref` 与 **`dac_iladata` / `pkt_out`（dac_i/q）**
- **双文件对比**：`--csv`（ref）+ `--dac-csv`（dac）→ `--rx dac`
- **OSR 速率匹配**：`--csv-osr` / `--dac-csv-osr` / `--work-osr`（真 2x vs 4x dump）
- `--tx-source ref|dac|adc|auto` 与仪器 / 片上 / DAC RX 对比
- **iQxel 相位噪声补偿**（CFO 之后、LUT 之前）：去掉仪器/LO 慢变公共相位，减轻对 AM-PM / LUT 的污染

入口：`dpd/xian_static_dpd_main1.py`。

## 数据流

```text
主 CSV（--csv）+ 可选 --dac-csv
  → read_data（decimate，或 OSR 模式下 decimate=1）
  → 可选 resample_iq_to_osr → 共同 work_osr
  → TX：--tx-source ref|dac|adc|auto
  → RX：txt/mat（全局）| feedback（±lag）| dac（--dac-csv → 全局包络）
  → align_time_domain → gain → CFO → (iQxel) PN → DC → frac delay
  → LUT / lut_data_map.py / amamplot
```

## iQxel 相位噪声补偿（PN）

仪器 dump（`--rx txt|mat`）相对片上 feedback 常带 **LO/相位噪声慢游走**。线性 CFO 只去掉一次项后，残差相位仍含公共 PN + PA AM-PM。估 LUT 前若把 PN 留在 RX 上，会污染 AM-PM 与记忆多项式系数。

### 算法（`dpd/phase_noise_compensation.py`）

1. 对齐且 CFO 后：`φ(n) = unwrap∠(TX · conj(RX))`
2. 在高幅度锚点（`|TX| ≥ pn_amp_ratio · peak`）上对 `|TX|` 拟合 AM-PM 多项式（默认 2 阶）并扣除
3. 对残差做滑动平均（`--pn-smooth-win`，默认 257 @ ~80 MHz ≈ 3.2 µs）→ `PN(n)`
4. `RX ← RX · exp(j · PN)`，再进入 DC / 分数时延 / `static_dpd_memory`

### 何时启用

| `--pn-comp` | 行为 |
|-------------|------|
| `auto`（默认） | 仅当 `rx_label` 为 iQxel（`txt`/`mat`/`iqxel`）时启用 |
| `on` | 强制启用（含 feedback/dac，一般不推荐） |
| `off` | 强制关闭 |

日志：`[PN] smooth_win=… anchors=… pn_rms=…`；关闭时 `[PN] skipped`。  
诊断图：`pn_iter*_phase.png/.pdf`（原始相位、AM-PM 拟合、PN 估计、补偿后残差）。

## CSV 布局

| layout | 列 | 典型用途 |
|--------|-----|----------|
| `feedback_ref` | `adc_i/q, feedback_q/i, ref_i/q` | ref/feedback 与 iQxel 或片上对比 |
| `dac` | `adc_i/q, dac_i/q` | `dac_iladata` / `pkt_out_iladata` 等 |

## TX / RX / 速率

| 参数 | 取值 | 说明 |
|------|------|------|
| `--tx-source` | `ref` / `dac` / `adc` / `auto` | 见上 |
| `--rx` | `txt` / `mat` / `feedback` / `dac` / … | `--dac-csv` 时用全局对齐 |
| `--dac-csv` | 路径 | 第二份 `dac_i/q` |
| `--csv-decimate` | 默认 `2` | 主 CSV 行抽稀（MATLAB `1:2:end`） |
| `--dac-csv-decimate` | 默认同主 CSV | 第二份抽稀 |
| `--csv-osr` / `--dac-csv-osr` | 如 `4` / `2` | dump 过采样标注；设置后先全采样再重采样 |
| `--work-osr` | 默认 `min(…)` | 对齐前共同速率 |

### 2x / 4x 说明（pkt_out vs ref）

模块上 `pkt_out` 常标 **2x**、`ref` 标 **4x**，但 Vivado ILA 对这两路 dump **多为同一采样钟**（两侧都 `decimate=2` 后包络相关 ≈0.95）。  
因此 **默认不要** 对 pkt_out 做 2→4 上采样；用默认抽稀 + `--dac-csv` 全局对齐即可。

仅当确认 dump 真为半速率时再用：

`--csv-osr 4 --dac-csv-osr 2 --work-osr 2`

## 自动对齐

| 模式 | 行为 |
|------|------|
| iQxel / `--dac-csv` | **全局** `\|TX\|` 包络相关找起点 |
| `--signal-mode tone` / auto-CW | 复数去直流 + 估频；跳过包络残差整数时延 |
| 同 CSV `--rx feedback` / 同文件 dac | ±`--coarse-max-lag` |
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

### 1a) 发送 tone：DAC vs iQxel

CW 时 `|TX|` 近似恒定，包络对齐失效；`auto` 会切到 **tone**（复数去直流对齐、估频、I/Q 与频谱图）：

```powershell
python .\dpd\xian_static_dpd_main1.py `
  --csv "D:\test_data\AP\260807_dpd\tone\dac_iladata.csv" `
  --txt "D:\test_data\AP\260807_dpd\tone\iqxel_2412_tone.txt" `
  --tx-source dac --rx txt `
  --align-plot-start 5700 --align-plot-end 6400 `
  -o "D:\users\gxu\scripts\dpd\output\260807\tone\dac_iqxel"
```

可选：`--signal-mode tone` 强制；`--fs 80e6`（默认，ILA `decimate=2` 与 iQxel `stride=2` 后）。

### 1b) ref CSV vs dac CSV（双文件）

主 CSV 取 `ref_*` 作 TX；`--dac-csv` 取 `dac_*` 作 RX（**全局**包络对齐）：

```powershell
python .\dpd\xian_static_dpd_main1.py `
  --csv "D:\test_data\AP\260806_dpd\4\feedback_ref_iladata.csv" `
  --tx-source ref `
  --dac-csv "D:\test_data\AP\260806_dpd\4\dac_iladata.csv" `
  --rx dac `
  --align-plot-start 5700 --align-plot-end 6400 `
  -o "D:\users\gxu\scripts\dpd\output\260806\4_ref_vs_dac"
```

### 1c) ref vs pkt_out dac（2x 模块名 / 同 ILA 钟）

```powershell
python .\dpd\xian_static_dpd_main1.py `
  --csv "D:\test_data\AP\260806_dpd\4\feedback_ref_iladata.csv" `
  --tx-source ref `
  --dac-csv "D:\test_data\AP\260806_dpd\6\pkt_out_iladata.csv" `
  --rx dac `
  --align-plot-start 5700 --align-plot-end 6400 `
  -o "D:\users\gxu\scripts\dpd\output\260806\6_ref_vs_pkt_out"
```

真半速率时再加：`--csv-osr 4 --dac-csv-osr 2 --work-osr 2`。

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
python dpd/xian_static_dpd_main1.py ... --rx txt --pn-comp auto
python dpd/xian_static_dpd_main1.py ... --pn-comp off
python dpd/xian_static_dpd_main1.py ... --pn-comp on --pn-smooth-win 513 --pn-amp-ratio 0.3
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
| `--csv` / `--txt` / `--mat` / `--dac-csv` | 仓库默认 / 无 | 主 ILA CSV；iQxel；可选第二份 dac CSV |
| `--csv-decimate` / `--dac-csv-decimate` | `2` / 同主 | 行抽稀；与 `--*-osr` 互斥优先 OSR |
| `--csv-osr` / `--dac-csv-osr` / `--work-osr` | 无 | 过采样匹配（真 2x/4x dump） |
| `--signal-mode` | `auto` | `auto`/`ofdm`/`tone`（CW 自动切 tone） |
| `--fs` | `80e6` | 抽稀后采样率（tone 估频用） |
| `--rx` | `auto` | `txt`/`mat`/`feedback`/`dac`/`csv`/`auto` |
| `--tx-source` | `auto` | `ref`/`dac`/`adc`/`auto` |
| `--tx-slice-start` | `313` | TX 起点（1-based） |
| `--rx-slice-start` | `1596` | hint（全局对齐时仅对照） |
| `--slice-len` / `--align-len` | `7001`/`7000` | 切片长度 |
| `--align-plot-start/end` | `5000`/`7000` | 时域图窗 |
| `--coarse-search-len` | `500000` | iQxel 全局搜索 |
| `--coarse-max-lag` | `512` | feedback / local 半径 |
| `--coarse-local-only` / `--no-coarse-align` | off | 对齐模式 |
| `--lut-map-scale` | `128` | 字典定点 |
| `--pn-comp` | `auto` | 相位噪声补偿：`auto`=仅 iQxel / `on` / `off` |
| `--pn-smooth-win` | `257` | PN 滑动平均窗长（采样点） |
| `--pn-amp-ratio` | `0.25` | 高 \|TX\| 锚点阈值（相对峰值） |
| `--no-cfo` / `--no-plot` / `-o` | — | CFO / 少图 / 输出 |

## 产物（`-o`）

| 文件 | 说明 |
|------|------|
| `pre_gain_time_domain.png/.pdf` | 粗对齐后、**增益补偿前**时域（\|·\| / peak-norm / **I** / **Q**） |
| `align_time_domain.png/.pdf` | 与 `pre_gain_time_domain` **同一张图**（兼容旧文件名） |
| `tone_spectrum.*` | CW tone 模式：TX/RX \|FFT\| 叠画 |
| `cfo_iter*_before/after.*` | CFO 相位 |
| `pn_iter*_phase.*` | iQxel PN：相位 / AM-PM 拟合 / PN 估计 / 补偿后 |
| `lut_table.npz` / `lut_*.txt` / `lut_data_map.py` | LUT |
| `PA-Rx_amam/ampm.*` | AM-AM / AM-PM |

## 时域 I/Q 叠画相位对齐（`plot_aligned_time_domain`）

增益补偿前的 I/Q 图仅做**可视化**相位对齐（不改变后续 DPD 流水线数据）：

\[
a = \frac{\langle \mathrm{rx}, \mathrm{tx} \rangle}{\langle \mathrm{rx}, \mathrm{rx} \rangle},\quad
\mathrm{rx}\leftarrow \mathrm{rx}\cdot\frac{a}{|a|}
\]

再按 TX peak 对 RX 做幅度缩放便于叠画。

### 历史 bug（已修复）

旧实现用 `rx *= exp(-j∠g)`，`g` 取自 `vdot(rx,tx)/vdot(tx,tx)`，**旋转符号错误**。  
当窗内真实相位差接近 ±90° 时，残差约 ±180°，表现为 **I、Q 同时相对 TX「刚好取反」**，而 \|·\| 仍重合 —— 易误判为仪器/DAC 极性反了。

正确做法是对最小二乘复数增益 `a` 施加单位模 `a/|a|`（如上式）。

### 仍可能看到的 180°（非 bug）

DAC 数字基带 vs iQxel 下变频之间存在**未知载波相位**（混频差分极性、线缆、仪器 IF 约定），常为 ±180°（整体 ×(−1)）。  
这由后续 `gain_compensation` 吸收，**不影响**包络对齐与 LUT 拟合。  
区分：

| 现象 | 含义 |
|------|------|
| \|TX\| 与 \|RX\| 重合，I/Q 同翻 | 全局 180° 相位（或看旧图） |
| 仅 Q 反 / 频谱左右镜像 | 共轭或镜像混频，需另查 |
| \|·\| 都不齐 | 先查时延 / OSR / 是否 tone |

## 模块

| 模块 | 作用 |
|------|------|
| `read_data.py` | 双布局 CSV + `load_iqxel_txt` |
| `xian_static_dpd_main1.py` | 主流程 / 自动对齐 / 时域与 tone 图 / PN 开关 / `write_lut_data_map` |
| `phase_noise_compensation.py` | iQxel TX 参考 PN：扣 AM-PM 后滑窗估计并补偿 RX |
| `gain_compensation.py` 等 | 增益 / CFO / DC / 分数时延 / LUT / 绘图 |

## 注意点

1. DC 用的 TX 是切片后、未增益补偿的原始 TX。  
2. DPD 输入：`tx_gain` + 分数时延后 RX，再 `1000:end`。  
3. `dac` 布局无 ref/feedback 时不要用 `--rx feedback`。  
4. **双文件都是 dac 布局**时：`--csv` 取 TX 的 `dac_*`，`--dac-csv` 只作 RX；主文件名含 `ref` 时 TX 标签可为 `ref`。同文件勿让 TX/RX 抢同一份 dac。  
5. `pkt_out` 标 2x、`ref` 标 4x 时，先按**同 ILA 钟**默认抽稀对比；仅确认半速率 dump 再用 `--*-osr`。  
6. 看 `pre_gain_time_domain` / `align_time_domain` 与日志 `score=` 确认包络是否重合；I/Q 叠画已用正确 `a/|a|` 相位对齐。  
7. **iQxel 估 LUT 默认开 PN**（`--pn-comp auto`）；片上 feedback / dac 对比默认关。窗过短会抠掉部分 AM-PM，过长跟不上 PN；先看 `pn_iter*_phase` 与 `pn_rms`。
