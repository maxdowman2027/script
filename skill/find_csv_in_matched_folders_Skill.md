# find_csv_in_matched_folders.py — 按文件夹名模式检索 CSV

## 脚本概述

`find_csv_in_matched_folders.py` 在指定根路径下**递归**查找**文件夹 basename** 符合通配符的目录，收集 **CSV**，并从路径解析 **band / phymode(phymd) / 20m / ldpc / he** 等配置。  
可选：**复制/移动**、路径列表导出，以及按 **`wifiRxPlot.py` 相同算法** 计算 **RX 灵敏度** 并输出汇总 **CSV**。

依赖模块：`wifi_rx_sensitivity.py`（PER 插值求灵敏度，无 PDF）。

---

## 路径层级解析

根目录 `...\rftest_data\2G` 时，示例路径  
`...\2G\phymd20\20m\ldpc\he\wifi_txrx_test_...\FPGA...\rx_20260521\RX_*.csv`  
解析为：`band=2G`, `phymode=phymd20`, `bandwidth=20m`, `coding=ldpc`, `wifi_format=he` 等。

---

## 灵敏度计算（同 wifiRxPlot）

1. 将检索到的 CSV 按 **`rx_*` 会话目录**（CSV 所在文件夹，如 `...\rx_20260521\`）分组。  
2. 合并该目录下全部 `*.csv`（与 wifiRxPlot 合并同一 testcase 目录一致）。  
3. 按 `rx_chan`、按 `rate` 列：由 `rxnum` 算 PER，对 `rfpwr` 扫描曲线插值得到 **灵敏度 (dBm)**（11b：PER 8%，其它：10%）。  
4. 写入 **`SENSITIVITY_OUT_CSV`**（默认 `ROOT_SEARCH_PATH/sensitivity_summary_时间戳.csv`）。

### 灵敏度输出 CSV 列

| 列 | 说明 |
|----|------|
| `band`, `phymode`, `bandwidth`, `coding`, `wifi_format` | 路径解析 |
| `testcase_folder`, `run_folder`, `rx_folder`, `config_tag` | 路径解析 |
| `rx_session_dir` | 合并计算的 RX 日志目录 |
| `rx_chan` | 信道 |
| `testcase_label` | 用于 11b/其它 PER 门限推断 |
| `rate` | MCS / rate 名 |
| `sensitivity_dbm` | 灵敏度 (dBm) |

---

## 配置区（脚本顶部）

| 变量 | 含义 |
|------|------|
| `ROOT_SEARCH_PATH` | 检索根目录 |
| `FOLDER_PATTERN` | 文件夹通配符 |
| `CSV_PATTERN` | CSV 文件名通配符 |
| `MOVE_DIR` / `COPY_DIR` | 复制/移动目标（二选一） |
| `RUN_SENSITIVITY` | 默认是否计算灵敏度（`True`） |
| `SENSITIVITY_OUT_CSV` | 灵敏度 CSV 路径；`None` 为自动命名 |
| `PAK_NUM` | PER 分母包数（默认 1000） |
| `SENS_ACCURACY` | 插值步数（默认 100） |

---

## 命令行

```bash
python find_csv_in_matched_folders.py
python find_csv_in_matched_folders.py --sensitivity-out D:\out\sens_summary.csv
python find_csv_in_matched_folders.py --no-sensitivity
python find_csv_in_matched_folders.py --pak-num 1000 --sens-accuracy 100
```

| 参数 | 配置区 |
|------|--------|
| `--sensitivity-out` | `SENSITIVITY_OUT_CSV` |
| `--no-sensitivity` | 关闭 `RUN_SENSITIVITY` |
| `--pak-num` | `PAK_NUM` |
| `--sens-accuracy` | `SENS_ACCURACY` |

---

## Python API

```python
from find_csv_in_matched_folders import find_csv_in_matched_folders, run_sensitivity_for_hits

hits = find_csv_in_matched_folders(root, folder_pattern, "*.csv")
run_sensitivity_for_hits(hits, r"D:\out\sens.csv", pak_num=1000, sens_accuracy=100)
```

```python
import wifi_rx_sensitivity as wrs
rows = wrs.sensitivity_rows_for_session(session_dir, path_config_dict)
wrs.write_sensitivity_csv(rows, out_csv)
```

---

## 依赖

- `pandas`（灵敏度与 CSV 写出）

---

## Skill 元数据

- **描述**: 检索 RX CSV、路径配置解析、wifiRxPlot 灵敏度汇总 CSV。  
- **标签**: CSV, RX, 灵敏度, rftest_data, wifiRxPlot  
