# organize_sensitivity_mld_diff.py 脚本说明文档

## 脚本概述

`organize_sensitivity_mld_diff.py` 用于整理 **RX 灵敏度汇总 CSV**（通常由 `find_csv_in_matched_folders.py` + `wifi_rx_sensitivity.py` 产出，或手工放入 `output/sensitivity_out/result/` 的 `*_result.csv`）。

在相同射频/转台配置下，将 **mld_en=0** 与 **mld_en=1** 的两行 **宽表合并为一行**，便于对比 MLD 开关对灵敏度的影响，并在 Excel 中对差值列着色。

---

## 数据流位置

```text
find_csv_in_matched_folders.py
  → sensitivity_summary_*.csv（长表，含 mld_en）
  → <同 stem>_mld_wide.csv/.xlsx（宽表，自动）
  → <同 stem>_radar/（mld_diff 雷达图，角度=cur_degree，半径=|diff|）

organize_sensitivity_mld_diff.py（离线）
  → 对已存在的 *_result.csv 做宽表；核心 API 在 wifi_rx_sensitivity.py
```

**说明**：宽表合并与 `plot_sensitivity_mld_diff_radar` 已整合进 `wifi_rx_sensitivity.py`；`find_csv` 默认在算完灵敏度后自动调用，无需再单独跑 organize（除非只整理历史 CSV）。

典型输入目录（脚本默认）：

`output/sensitivity_out/result/`

输入文件通配：`*_result.csv`（如 `2G_he_result.csv`、`5G_vht_result.csv`）。

---

## 合并规则

### 配对键（必须全部相同）

| 列 | 说明 |
|----|------|
| `bandwidth` | 带宽目录名，如 `160m`、`20m` |
| `coding` | `ldpc` / `bcc` 等 |
| `wifi_format` | 如 `he`、`vht` |
| `cur_degree` | 转台角度（°） |
| `rate` | 速率/MCS 标签 |
| `rx_chan` | 接收信道 |

仅当同一配对键下 **同时存在** `mld_en=0` 与 `mld_en=1` 各一条（或取 `pivot` 后两列均有值）时，才输出合并行；缺一侧的输入行不会出现在宽表中。

### 丢弃 / 保留列

**不写回宽表**（随 mld 变化或已展开）：

- `mld_en`
- `sensitivity_dbm`（拆为两列）
- `testcase_folder`
- `rx_session_dir`

**元数据**（`band`、`phymode`、`config_tag`、`testcase_label` 等）取自 **mld_en=0** 行（若无则取组内首行）。

---

## 输出列

| 列名 | 含义 |
|------|------|
| `sensitivity_dbm_mld_en0` | mld_en=0 的 `sensitivity_dbm` |
| `sensitivity_dbm_mld_en1` | mld_en=1 的 `sensitivity_dbm` |
| `sensitivity_dbm_mld_diff` | **`sensitivity_dbm_mld_en0 − sensitivity_dbm_mld_en1`**（dB） |

### 差值解读（灵敏度 dBm）

`sensitivity_dbm` 数值越负表示灵敏度越好。

- **差值为正**：mld_en=0 的数值 **大于** mld_en=1（相对更不敏感 / mld_en=1 更好）
- **差值为负**：mld_en=0 **优于** mld_en=1（mld_en=0 更负）

---

## 输出文件

默认每个输入 `{stem}_result.csv` 生成：

| 文件 | 说明 |
|------|------|
| `{stem}_mld_wide.csv` | 宽表，无填充色 |
| `{stem}_mld_wide.xlsx` | 同内容；**`sensitivity_dbm_mld_diff` 列按阈值填充色** |

默认输出目录：`<input_dir>/organized/`（与输入 `result/` 并列）。

`--inplace` 时：在输入文件同目录生成 `{原文件名去扩展名}_mld_wide.csv/.xlsx`。

可选 `--combined <path>`：将所有输入宽表纵向合并为一个 CSV。

---

## 差值列填充色（仅 xlsx）

阈值单位：**dB**（`sensitivity_dbm_mld_diff`）

| 差值 | 填充色 | 色值 |
|------|--------|------|
| ≥ 2 | 绿 | `#00FF00` |
| ≥ 1 | 浅绿 | `#90EE90` |
| ≥ −1 | 黄 | `#FFFF00` |
| ≥ −2 | 橙 | `#FFA500` |
| &lt; −2 | 红 | `#FF0000` |

**越大越绿，越负越红**，中间黄/橙过渡（与仓库内 EVM 差值着色习惯一致）。

---

## 命令行

```bash
# 默认：读 output/sensitivity_out/result/*_result.csv
#       写 output/sensitivity_out/result/organized/*_mld_wide.csv|.xlsx
python organize_sensitivity_mld_diff.py

python organize_sensitivity_mld_diff.py --input_dir "D:\path\to\result"
python organize_sensitivity_mld_diff.py --input_dir "D:\path\to\result" --output_dir "D:\path\to\out"
python organize_sensitivity_mld_diff.py --pattern "*_result.csv"
python organize_sensitivity_mld_diff.py --combined "D:\path\to\all_mld_wide.csv"
python organize_sensitivity_mld_diff.py --inplace
```

### 参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `--input_dir` | `output/sensitivity_out/result` | 输入 CSV 目录 |
| `--pattern` | `*_result.csv` | 输入通配 |
| `--output_dir` | `<input_dir>/organized` | 输出目录 |
| `--combined` | 无 | 合并所有宽表为一个 CSV |
| `--inplace` | 关 | 输出到输入文件同目录 |

---

## Python API

```python
import pandas as pd
from organize_sensitivity_mld_diff import (
    merge_mld_sensitivity_rows,
    write_mld_wide_outputs,
)

df = pd.read_csv("2G_he_result.csv")
wide = merge_mld_sensitivity_rows(df)
write_mld_wide_outputs(
    wide,
    "organized/2G_he_mld_wide.csv",
    "organized/2G_he_mld_wide.xlsx",
)
```

---

## 依赖

- `pandas`
- `openpyxl`（写 xlsx 与填充色）
- `numpy`

---

## 注意事项

1. 输入须含列：`mld_en`、`sensitivity_dbm` 及全部配对键列。
2. 若某配置只有 `mld_en=0` 或只有 `mld_en=1`，该测点不会出现在宽表中（控制台会提示约 `input_rows - 2*output_rows` 未配对行数）。
3. 着色仅存在于 **xlsx**；用 Excel 打开查看差值列颜色。
4. 与 `find_csv_in_matched_folders` 雷达图互补：雷达图按角度叠加曲线；本脚本按 **rate × 信道** 给出数值差表，便于筛异常 MCS/角度。

---

**文档版本**：1.0  
**更新日期**：2026-05-27
