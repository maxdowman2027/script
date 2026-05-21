# find_csv_in_matched_folders.py — 按文件夹名模式检索 CSV

## 脚本概述

`find_csv_in_matched_folders.py` 在指定根路径下**递归**查找**文件夹 basename** 符合通配符或正则的目录，再在这些目录内（含子目录）收集符合命名规则的 **CSV**。支持仅列出路径、导出列表文件，或将结果 **复制 / 移动** 到目标目录。

典型场景：在 `rftest_data\2G` 下找到 `wifi_txrx_test_RXSens_*_mld_en0_cur_degree0` 类灵敏度测试目录，汇总其中 `RX_*.csv` 供后续 `wifiRxProcess` / `merge_csv_to_xlsx` 等使用。

---

## 工作流程

```text
--root（递归 walk）
    → 文件夹名匹配 --folder-pattern
        → 该文件夹内（可含子目录）匹配 --csv-pattern 的 .csv
            → 打印 / --list-out
            → 可选 --copy-dir 或 --move-dir（扁平落盘）
```

---

## 命令行

### 仅检索（默认示例路径）

```bash
python find_csv_in_matched_folders.py
python find_csv_in_matched_folders.py -v
python find_csv_in_matched_folders.py --paths-only
```

### 指定根路径与文件夹通配符

```bash
python find_csv_in_matched_folders.py ^
  --root "D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\2G" ^
  --folder-pattern "wifi_txrx_test_RXSens_*_mld_en0_cur_degree0" ^
  --csv-pattern "RX_*.csv"
```

### 导出路径列表

```bash
python find_csv_in_matched_folders.py ^
  -r "D:\...\rftest_data\2G" ^
  -f "wifi_txrx_test_RXSens_*_mld_en0_cur_degree0" ^
  -o "D:\users\gxu\out\matched_csv_list.txt"
```

### 复制到目标目录（扁平）

```bash
python find_csv_in_matched_folders.py ^
  -r "D:\...\rftest_data\2G" ^
  -f "wifi_txrx_test_RXSens_*_mld_en0_cur_degree0" ^
  --copy-dir "D:\users\gxu\collected_rx_csv"
```

### 移动到目标目录

```bash
python find_csv_in_matched_folders.py ^
  -r "D:\...\rftest_data\2G" ^
  -f "wifi_txrx_test_RXSens_*_mld_en0_cur_degree0" ^
  --move-dir "D:\users\gxu\collected_rx_csv"
```

### 重名处理

| 情况 | 行为 |
|------|------|
| 默认 | 目标目录已有同名文件时自动追加 `_1`、`_2` … |
| `--overwrite` | 覆盖已有文件 |
| `--use-subpath-prefix` | 目标文件名为「相对匹配文件夹的路径」，分隔符改为 `_`，减少不同子目录同名 CSV 冲突 |

`--copy-dir` 与 `--move-dir` **互斥**，不可同时使用。

---

## 参数一览

| 参数 | 说明 |
|------|------|
| `-r` / `--root` | 递归搜索根目录 |
| `-f` / `--folder-pattern` | 文件夹 basename 通配符（默认 `wifi_txrx_test_RXSens_*_mld_en0_cur_degree0`） |
| `-c` / `--csv-pattern` | CSV 文件名通配符（默认 `*.csv`） |
| `--regex-folder` | `--folder-pattern` 按正则（从头匹配 basename） |
| `--regex-csv` | `--csv-pattern` 按正则 |
| `-o` / `--list-out` | 将绝对路径逐行写入文件 |
| `-v` / `--verbose` | 按匹配文件夹分组打印全部 CSV |
| `--paths-only` | 仅输出 CSV 路径 |
| `--copy-dir DIR` | 复制到 DIR（扁平） |
| `--move-dir DIR` | 移动到 DIR（扁平） |
| `--overwrite` | 覆盖目标目录同名文件 |
| `--use-subpath-prefix` | 目标文件名带相对子路径前缀 |

---

## Python API

```python
from find_csv_in_matched_folders import (
    find_csv_in_matched_folders,
    transfer_csv_hits,
)

hits = find_csv_in_matched_folders(
    r"D:\...\rftest_data\2G",
    "wifi_txrx_test_RXSens_*_mld_en0_cur_degree0",
    "RX_*.csv",
)

stats = transfer_csv_hits(hits, r"D:\out\csv_flat", move=False, use_subpath_prefix=True)
print(stats.ok, stats.errors)
```

---

## 与 `spur_notch/move_spur_scan_result_csvs.py` 的区别

| 脚本 | 侧重 |
|------|------|
| `find_csv_in_matched_folders.py` | **查找 + 可选复制/移动**；CLI 参数化；默认 RX 灵敏度目录通配符 |
| `spur_notch/move_spur_scan_result_csvs.py` | 历史杂散结果整理；配置写在脚本 `__main__` 块 |

---

## 依赖

仅 Python 标准库：`os`、`fnmatch`、`re`、`shutil`、`argparse`。

---

## Skill 元数据（索引用）

- **名称**: find_csv_in_matched_folders  
- **描述**: 递归匹配文件夹名并收集 CSV；支持 list-out、copy-dir、move-dir。  
- **标签**: CSV, 文件检索, RX测试, rftest_data  
