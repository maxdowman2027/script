# rx_iq_imbalance_psd.py — myplot.psd_plot_rx_cal 1:1 移植

## 概述

本脚本将 Xian 测试库 `myplot.psd_plot_rx_cal` **原样移植**，仅两处改动：

1. **参数**：`bw` / `ch_freq` / `freqcw` 由脚本配置区或 CLI 传入（不再从 `fname` 正则解析）
2. **数据**：从指定 CSV 读取 `sample_i`/`sample_q`，并按 `adc_dump.py` 做 `÷ 2**11` 与 `2**floor(log2(N))` 截断

参考路径：
`D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rx_script\baselib\plot\myplot.py`

---

## 配置区

| 变量 | 含义 |
|------|------|
| `INPUT_CSV` | 输入 I/Q CSV |
| `OUTPUT_PDF` | PDF 路径 stem（无 `.pdf`）；空 → 输入文件 stem |
| `BW_MHZ` | phymd 带宽 |
| `CH_FREQ_MHZ` | chan 信道中心 MHz |
| `FREQCW_MHZ` | freqcw 单音 MHz |
| `ADC_BIT_WIDTH` | 有符号 ADC 位宽（默认 **12**） |
| `SAMPLE_FREQ_MHZ` | 名义 ADC 采样率 MHz；**有效 Welch Fs = 本值 / DECIMATE_FACTOR** |
| `DECIMATE_FACTOR` | 抽取倍率（默认 **2** = 2抽1 `[::2]`，去重复样点） |
| `MAX_ROWS` | 最大读取行数；0=全文件 |
| `IQ_MODE` | auto / single / 2ant |

---

## 数据流

```text
CSV (12-bit signed sample_i/q)
  → ÷ 2**(ADC_BIT_WIDTH-1)
  → 2抽1 [::2]（DECIMATE_FACTOR=2）
  → 截断 2^n 样点
  → Welch(Fs = SAMPLE_FREQ_MHZ / DECIMATE_FACTOR)   # 例：160/2=80MHz
  → tone bin: diff_freq / Fs * pwr_len
  → [ori_tone_pwr, mir_tone_pwr, sig_pwr] + PDF（±tone 竖线，标注 main/mirror pwr 及差值）
```

**频谱错位说明**：myplot 假设 RX dump 已按 bw 降到 Fs=40(20M)。ILA 全速率 dump 若仍用 40MHz，5MHz tone 会显示在 ~1.2MHz。请设 `SAMPLE_FREQ_MHZ=160`（或实测采样率）。

`sample_i` → `real_data`，`sample_q` → `image_data`（与 adc_dump 中 r_data/i_data 一致）。

---

## 核心函数

### `psd_plot_rx_cal(real_data, image_data, bw, ch_freq, freqcw, fname)`

与 myplot **相同计算逻辑**（参数显式传入），内部计算、打印、PDF、`return [ori_tone_pwr, mir_tone_pwr, sig_pwr]` 均一致。

### `load_real_image_from_csv(csv_file)`

读取 CSV 并完成 adc_dump 预处理。

### `run_from_csv(csv_file, bw, ch_freq, freqcw, fname=...)`

一键：读文件 + 调用 `psd_plot_rx_cal`。

---

## 命令行

```bash
python rx_iq_imbalance_psd.py
python rx_iq_imbalance_psd.py data.csv --bw 20 --chan 2462 --freqcw 2467
python rx_iq_imbalance_psd.py data.csv -o D:\out\myplot_stem
```

---

## 产物

| 文件 | 说明 |
|------|------|
| `<fname>.pdf` | Welch PSD；标题含 main/mirror pwr 及 **Δ(main−mirror)**；图例含 tone 频率与功率 |
| `<csv_stem>_iq_cal_result.csv` | ori/mir/iq_suppression/sig_pwr 汇总 |

---

## BW → Fs（myplot 内嵌逻辑）

| bw | sample_freq_mhz / all_freq |
|----|----------------------------|
| 20 | 40 |
| 40 | 80 |
| 80 | 160 |
| 其他 | 320 |
