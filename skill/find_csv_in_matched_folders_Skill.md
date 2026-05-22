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

## 灵敏度雷达图（极坐标）

在灵敏度 CSV 写出后（`RUN_SENSITIVITY_RADAR=True`，默认开启）：

- **角度轴**：`cur_degree`（°），0° 在正北，顺时针增加（与天线转台角度一致）。  
- **径向**：`-sensitivity_dbm`（数值越大表示越灵敏，即 dBm 越负时半径越大）。  
- **分组**：每个 `(band, phymode, bandwidth, coding, wifi_format, rx_chan, rate)` 一张 PNG；**同一图上叠加**不同 `mld_en`（典型为 **mld_en=0 与 mld_en=1** 对比，图例区分）。  
- **文件名**：同时含 0/1 时为 `..._mld0v1_...png`。  
- **输出目录**：默认与灵敏度 CSV 同目录下的 `<csv_stem>_radar/`（可用 `SENSITIVITY_RADAR_DIR` 或 `--radar-dir` 指定）。

需至少 1 个有效点（含 `cur_degree` 且 `sensitivity_dbm ≠ 0`）；多角度时各 `mld_en` 曲线分别闭合显示。

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
| `RUN_SENSITIVITY_RADAR` | 是否生成雷达图（`True`） |
| `SENSITIVITY_RADAR_DIR` | 雷达图目录；`None` 为 `<csv_stem>_radar/` |
| `PAK_NUM` | PER 分母包数（默认 1000） |
| `SENS_ACCURACY` | 插值步数（默认 100） |

---

## 命令行

```bash
python find_csv_in_matched_folders.py
python find_csv_in_matched_folders.py --sensitivity-out D:\out\sens_summary.csv
python find_csv_in_matched_folders.py --radar-dir D:\out\radar
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
wrs.plot_sensitivity_radar(rows, r"D:\out\radar")
```

---

## 依赖

- `pandas`（灵敏度与 CSV 写出）
- `matplotlib`（雷达图 PNG）

---

## Skill 元数据

- **描述**: 检索 RX CSV、路径与 testcase 参数解析、灵敏度 CSV、按 cur_degree 的雷达图。  
- **标签**: CSV, RX, 灵敏度, 雷达图, cur_degree, mld_en, rftest_data, wifiRxPlot  
