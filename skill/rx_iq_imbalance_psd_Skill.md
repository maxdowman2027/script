# rx_iq_imbalance_psd.py — myplot.psd_plot_rx_cal 1:1 移植

## 概述

本脚本将 Xian 测试库 `myplot.psd_plot_rx_cal` **原样移植**，改动点：

1. **参数**：`bw` / `ch_freq` / `freqcw` 由脚本配置区或 CLI 传入（不再从 `fname` 正则解析）
2. **数据**：从指定 CSV 读取 I/Q 列（默认 `sample_i`/`sample_q`），并按 `adc_dump.py` 做 `÷ 2**11` 与 `2**floor(log2(N))` 截断
3. **批量**：`input` 可为**单文件**或**目录**；目录模式下自动检索 `*.csv` 逐个跑 PSD
4. **列名可配**：通过配置变量或 CLI 指定 I/Q（及 2ant）列名
5. **归一化可选**：`adc`（÷ ADC 满幅）或 `peak`（÷ 本段数据 `max(|I|,|Q|)`）

参考路径：
`D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rx_script\baselib\plot\myplot.py`

---

## 配置区

| 变量 | 含义 |
|------|------|
| `INPUT_CSV` | 输入 I/Q CSV **或目录** |
| `OUTPUT_PDF` | 单文件：PDF stem（无 `.pdf`）；空 → 输入文件 stem。目录模式：可选输出目录 |
| `BW_MHZ` | phymd 带宽 |
| `CH_FREQ_MHZ` | chan 信道中心 MHz |
| `FREQCW_MHZ` | freqcw 单音 MHz |
| `ADC_BIT_WIDTH` | 有符号 ADC 位宽（默认 **12**） |
| `SAMPLE_FREQ_MHZ` | 名义 ADC 采样率 MHz；**有效 Welch Fs = 本值 / DECIMATE_FACTOR** |
| `DECIMATE_FACTOR` | 抽取倍率（默认 **1**；`2` = 2抽1 `[::2]`） |
| `MAX_ROWS` | 最大读取行数；0=全文件 |
| `IQ_MODE` | auto / single / 2ant |
| `COL_I` / `COL_Q` | 单流 I/Q 列名（默认 `sample_i` / `sample_q`） |
| `COL_CH0_I` / `COL_CH0_Q` / `COL_CH1_I` / `COL_CH1_Q` | 2ant 列名 |
| `NORM_MODE` | `adc`（默认）或 `peak`（按数据峰值归一化） |

列名匹配**忽略大小写**与首尾空格。

---

## 数据流

```text
CSV (signed I/Q columns)
  → 归一化：
       adc  → ÷ 2**(ADC_BIT_WIDTH-1)
       peak → ÷ max(|I|,|Q|)
  → 可选 2抽1 [::2]（DECIMATE_FACTOR=2）
  → 截断 2^n 样点
  → Welch(Fs = SAMPLE_FREQ_MHZ / DECIMATE_FACTOR)
  → tone bin: diff_freq / Fs * pwr_len
  → [ori_tone_pwr, mir_tone_pwr, sig_pwr] + PDF
```

**频谱错位说明**：myplot 假设 RX dump 已按 bw 降到 Fs=40(20M)。ILA 全速率 dump 若仍用 40MHz，5MHz tone 会显示在 ~1.2MHz。请设 `SAMPLE_FREQ_MHZ=160`（或实测采样率）。

---

## 目录批量

| 行为 | 说明 |
|------|------|
| 输入为目录 | 检索该目录下 `*.csv`（默认**非递归**） |
| `--recursive` / `-r` | 递归子目录 `**/*.csv` |
| 跳过产物 | 自动跳过 `*_iq_cal_result.csv` |
| 单文件产物 | 每个 CSV 旁写 `<stem>.pdf`、`<stem>_iq_cal_result.csv` |
| `-o <dir>`（目录模式） | PDF/结果写到指定输出目录 |
| 批汇总 | 目录模式额外写 `iq_cal_batch_summary.csv` |

---

## 核心函数

### `psd_plot_rx_cal(...)` / `run_from_csv(...)` / `load_real_image_from_csv(...)`

`load_real_image_from_csv` / `run_from_csv` 支持 `col_i` / `col_q`（及 2ant 列名）与 `norm_mode`（`adc`|`peak`）。

### `collect_csv_inputs(input_path, recursive=False)`

将文件或目录解析为待处理 CSV 列表。

---

## 命令行示例

```bash
# 默认列 sample_i / sample_q
python rx_iq_imbalance_psd.py
python rx_iq_imbalance_psd.py data.csv --bw 20 --chan 2462 --freqcw 2467

# 指定 I/Q 列名（如 feedback / ref / adc 等）
python rx_iq_imbalance_psd.py data.csv --col-i feedback_i --col-q feedback_q --bw 20 --chan 2412 --freqcw 2417
python rx_iq_imbalance_psd.py data.csv --col-i ref_i --col-q ref_q --sample-freq-mhz 80

# 配置区也可改：
#   COL_I = "feedback_i"
#   COL_Q = "feedback_q"

# 目录批量 + 自定义列名
python rx_iq_imbalance_psd.py "D:\test_data\rls4\260722_dpd\tone" --col-i sample_i --col-q sample_q --bw 20 --chan 2412 --freqcw 2417
python rx_iq_imbalance_psd.py "D:\path\to\dump_dir" -r -o "D:\path\to\out" --col-i sample_i --col-q sample_q

# 2ant：指定双天线列并选通道
python rx_iq_imbalance_psd.py dual.csv --mode 2ant --ch 0 --col-ch0-i ch0_sample_i --col-ch0-q ch0_sample_q

# 归一化：默认 adc（÷2**(bit-1)）；可选 peak（÷本段 max(|I|,|Q|)）
python rx_iq_imbalance_psd.py data.csv --norm-mode adc --bit-width 12
python rx_iq_imbalance_psd.py data.csv --norm-mode peak --col-i sample_i_ch0 --col-q sample_q_ch0
# 配置区：NORM_MODE = "peak"
```

---

## 产物

| 文件 | 说明 |
|------|------|
| `<fname>.pdf` | Welch PSD；标题含 main/mirror pwr 及 **Δ(main−mirror)** |
| `<csv_stem>_iq_cal_result.csv` | 单文件 ori/mir/iq_suppression/sig_pwr 汇总 |
| `iq_cal_batch_summary.csv` | **仅目录模式**：批内全部 CSV 汇总表 |

---

## BW → Fs（myplot 内嵌逻辑）

| bw | sample_freq_mhz / all_freq |
|----|----------------------------|
| 20 | 40 |
| 40 | 80 |
| 80 | 160 |
| 其他 | 320 |
