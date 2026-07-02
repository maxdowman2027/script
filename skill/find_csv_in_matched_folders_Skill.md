# find_csv_in_matched_folders.py — 按文件夹名模式检索 CSV

## 脚本概述

`find_csv_in_matched_folders.py` 在指定根路径下**递归**查找**文件夹 basename** 符合通配符的目录，收集 **CSV**，并从路径解析 **band / phymode(phymd) / 20m / ldpc / he** 等配置。  
从 **`testcase_folder`**（如 `wifi_txrx_test_RXSens_..._mld_en0_cur_degree45`）解析 **`mld_en`**、**`cur_degree`**（当前测试角度，单位：度）。  
可选：**复制/移动**、路径列表导出，按 **`wifiRxPlot.py` 相同算法** 计算 **RX 灵敏度** 汇总 **CSV**，并按角度绘制 **灵敏度雷达图（极坐标）**。

依赖模块：`wifi_rx_sensitivity.py`（PER 插值求灵敏度、雷达图、无 PDF）。

---

## 路径层级解析

根目录 `...\rftest_data\2G` 时，示例路径  
`...\2G\phymd20\20m\ldpc\he\wifi_txrx_test_RXSens_*_mld_en0_cur_degree45\FPGA...\rx_20260521\RX_*.csv`

| 字段 | 来源 |
|------|------|
| `band`, `phymode`, `bandwidth`, `coding`, `wifi_format` | 路径目录段 |
| `testcase_folder` | `wifi_txrx*` 目录名 |
| `mld_en` | `testcase_folder` 中 `mld_en(\d+)`，如 `mld_en0` → `0` |
| `cur_degree` | `testcase_folder` 中 `cur_degree(\d+)`，如 `cur_degree45` → `45`（当前角度 °） |

---

## 灵敏度计算（同 wifiRxPlot）

1. 将检索到的 CSV 按 **`rx_*` 会话目录**（CSV 所在文件夹）分组。  
2. 合并该目录下全部 `*.csv`。  
3. 按 `rx_chan`、按 `rate`：由 `rxnum` 算 PER，对 `rfpwr` 插值得 **灵敏度 (dBm)**（11b：8%，其它：10%）。  
4. 写入 **`SENSITIVITY_OUT_CSV`**（默认 `ROOT_SEARCH_PATH/sensitivity_summary_时间戳.csv`）。

### 灵敏度输出 CSV 列

| 列 | 说明 |
|----|------|
| `band`, `phymode`, `bandwidth`, `coding`, `wifi_format` | 路径解析 |
| `testcase_folder`, `mld_en`, `cur_degree`, `config_tag` | testcase 名及解析参数 |
| `rx_session_dir` | 合并计算的 RX 日志目录 |
| `rx_chan` | 信道 |
| `testcase_label` | 11b/其它 PER 门限推断 |
| `rate` | MCS / rate 名 |
| `sensitivity_dbm` | 灵敏度 (dBm) |

---

## mld_en 宽表与灵敏度雷达图（极坐标）

在灵敏度长表 CSV 写出后（`RUN_SENSITIVITY=True`）：

1. **宽表**（`RUN_MLD_WIDE_OUTPUT=True`，默认）：`wifi_rx_sensitivity.write_mld_wide_from_long_rows`  
   - 输出 `<sensitivity_csv_stem>_mld_wide.csv`、`_mld_wide.xlsx`  
   - 列：`sensitivity_dbm_mld_en0`、`sensitivity_dbm_mld_en1`、`sensitivity_dbm_mld_diff`（**mld_en0 − mld_en1**，dB）  
   - 仅保留同时有 mld_en=0/1 的测点（`bandwidth/coding/wifi_format/cur_degree/rate/rx_chan` 相同）

2. **雷达图**（`RUN_SENSITIVITY_RADAR=True`，默认）：`plot_sensitivity_mld_diff_radar`（基于宽表）  
   - **角度轴**：`cur_degree`（°），0° 正北、顺时针  
   - **零圈 `r0`**：`diff = 0`（mld_en0 − mld_en1）虚线参考圆  
   - **径向**：**`log1p(|diff|)`**；**diff &gt; 0** 在 `r0` **外**（绿色底色）；**diff &lt; 0** 在 `r0` **内**（红色底色）  
   - **点标注**：每个角度标注 **带符号 diff**（如 `+2.3` / `-1.5` dB）  
   - **参考圆环**：|diff|=0 及 min / median / max |diff|（内外对称 log 刻度）；`rticks` 为 `|diff|=X dB`  
   - **分组**：每个 `(band, phymode, bandwidth, coding, wifi_format, rx_chan, rate)` 一张 PNG；文件名 `radar_mld_diff_...png`  
   - **输出目录**：`<csv_stem>_radar/`（`SENSITIVITY_RADAR_DIR` / `--radar-dir`）

无宽表时不会出雷达图。`--no-mld-wide` 跳过宽表；`--no-radar` 跳过雷达图。

旧版 `plot_sensitivity_radar`（长表叠加 mld_en0/1、半径=−sensitivity_dbm）仍保留在 `wifi_rx_sensitivity.py`，**find_csv 默认不再调用**。

---

## 配置区（脚本顶部）

| 变量 | 含义 |
|------|------|
| `ROOT_SEARCH_PATH` | 检索根目录 |
| `FOLDER_PATTERN` | 文件夹通配符（常含 `_mld_en*_cur_degree*`） |
| `CSV_PATTERN` | CSV 文件名通配符 |
| `MOVE_DIR` / `COPY_DIR` | 复制/移动目标（二选一） |
| `RUN_SENSITIVITY` | 默认是否计算灵敏度（`True`） |
| `SENSITIVITY_OUT_CSV` | 灵敏度 CSV 路径；`None` 为自动命名 |
| `RUN_MLD_WIDE_OUTPUT` | 是否写 mld 宽表 csv/xlsx（`True`） |
| `RUN_SENSITIVITY_RADAR` | 是否生成 mld-diff 雷达图（`True`） |
| `SENSITIVITY_RADAR_DIR` | 雷达图目录；`None` 为 `<csv_stem>_radar/` |
| `PAK_NUM` | PER 分母包数（默认 1000） |
| `SENS_ACCURACY` | 插值步数（默认 100） |

---

## 命令行

```bash
python find_csv_in_matched_folders.py
python find_csv_in_matched_folders.py --sensitivity-out D:\out\sens_summary.csv
python find_csv_in_matched_folders.py --radar-dir D:\out\radar
python find_csv_in_matched_folders.py --no-mld-wide
python find_csv_in_matched_folders.py --no-radar
python find_csv_in_matched_folders.py --no-radar
python find_csv_in_matched_folders.py --no-sensitivity
```

| 参数 | 配置区 |
|------|--------|
| `--sensitivity-out` | `SENSITIVITY_OUT_CSV` |
| `--no-sensitivity` | 关闭 `RUN_SENSITIVITY` |
| `--no-radar` | 关闭 `RUN_SENSITIVITY_RADAR` |
| `--radar-dir` | `SENSITIVITY_RADAR_DIR` |
| `--pak-num` | `PAK_NUM` |
| `--sens-accuracy` | `SENS_ACCURACY` |

---

## Python API

```python
from find_csv_in_matched_folders import find_csv_in_matched_folders, run_sensitivity_for_hits

hits = find_csv_in_matched_folders(root, folder_pattern, "*.csv")
run_sensitivity_for_hits(
    hits,
    r"D:\out\sens.csv",
    pak_num=1000,
    sens_accuracy=100,
    run_radar=True,
    radar_out_dir=r"D:\out\radar",
)
```

```python
import wifi_rx_sensitivity as wrs

mld, deg = wrs.parse_testcase_folder_params("wifi_txrx_test_RXSens_x_mld_en1_cur_degree90")
rows = wrs.sensitivity_rows_for_session(session_dir, path_config_dict)
wrs.write_sensitivity_csv(rows, out_csv)
# mld-diff 雷达（默认由 find_csv 调用 plot_sensitivity_mld_diff_radar）
wrs.plot_sensitivity_mld_diff_radar(wide_df, radar_dir)
# 旧版：长表叠加 mld_en0/1 曲线
wrs.plot_sensitivity_radar(rows, r"D:\out\radar")
```

---

## wifi_rx_sensitivity 雷达 API（mld-diff）

| 函数 | 说明 |
|------|------|
| `plot_sensitivity_mld_diff_radar` | 宽表 `sensitivity_dbm_mld_diff` vs `cur_degree`；**log1p(\|diff\|)** 径向；diff=0 虚线圈 `r0` |
| `_mld_diff_signed_log_polar_layout` | 计算 r0、内外 log 半径（diff≥0 外扩，diff&lt;0 内收） |
| `plot_sensitivity_radar` | 旧版长表雷达（半径=−sensitivity_dbm），find_csv 默认不调用 |

径向刻度标签为 `\|diff\|=X dB`；每个采样点标注 **带符号** diff（如 `+2.3` / `−1.5`）。

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.2 | 2026-05-27 | mld-diff 雷达：`log1p(\|diff\|)` 对称内外径向；点标注 signed diff；参考环 min/med/max \|diff\| |
| 1.1 | 2026-05 | 宽表 mld_en0/1、线性 `r0+diff` 雷达、find_csv 集成 |
| 1.0 | — | RX CSV 检索、灵敏度长表、cur_degree 解析 |

---

## 依赖

- `pandas`（灵敏度与 CSV 写出）
- `matplotlib`（雷达图 PNG）

---

## Skill 元数据

- **描述**: 检索 RX CSV、路径与 testcase 参数解析、灵敏度 CSV、按 cur_degree 的雷达图。  
- **标签**: CSV, RX, 灵敏度, 雷达图, cur_degree, mld_en, rftest_data, wifiRxPlot  
