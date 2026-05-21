# find_csv_in_matched_folders.py — 按文件夹名模式检索 CSV

## 脚本概述

`find_csv_in_matched_folders.py` 在指定根路径下**递归**查找**文件夹 basename** 符合通配符或正则的目录，再在这些目录内（含子目录）收集符合命名规则的 **CSV**。支持仅列出路径、导出列表文件，或将结果 **复制 / 移动** 到目标目录。

典型场景：在 `rftest_data\2G` 下找到 `wifi_txrx_test_RXSens_*_mld_en0_cur_degree0` 类灵敏度测试目录，汇总其中 `RX_*.csv` 供后续 `wifiRxProcess` / `merge_csv_to_xlsx` 等使用。

**日常用法**：优先改脚本顶部 **「配置区」** 三个路径/格式变量，再直接 `python find_csv_in_matched_folders.py`；不必每次写长命令行。

---

## 工作流程

```text
配置区 ROOT_SEARCH_PATH + FOLDER_PATTERN + MOVE_DIR/COPY_DIR
    → 递归 walk 根目录
        → 文件夹 basename 匹配 FOLDER_PATTERN
            → 其下（含子目录）匹配 CSV_PATTERN 的 .csv
                → 打印 / LIST_OUT_FILE
                → 可选复制到 COPY_DIR 或移动到 MOVE_DIR（扁平落盘）
```

---

## 脚本内配置（推荐，文件顶部「配置区」）

打开 `find_csv_in_matched_folders.py`，修改 `# =============================================================================` 与 `# =============================================================================` 之间的变量：

### 必改三项

| 变量 | 含义 | 示例 |
|------|------|------|
| `ROOT_SEARCH_PATH` | **递归检索根目录** | `r"D:\...\rftest_data\2G"` |
| `FOLDER_PATTERN` | **文件夹名匹配格式**（basename 通配符） | `wifi_txrx_test_RXSens_*_mld_en0_cur_degree0` |
| `MOVE_DIR` 或 `COPY_DIR` | **落盘目标**（二选一） | `MOVE_DIR = r"D:\...\collected_rx_csv"` |

- 仅检索、不复制/移动：`COPY_DIR = None` 且 `MOVE_DIR = None`
- 复制：`COPY_DIR = r"目标路径"`，`MOVE_DIR = None`
- 移动：`MOVE_DIR = r"目标路径"`，`COPY_DIR = None`
- **不可** 同时设置 `COPY_DIR` 与 `MOVE_DIR`（脚本会报错退出）

### 其它配置项

| 变量 | 默认 | 含义 |
|------|------|------|
| `CSV_PATTERN` | `*.csv` | 匹配文件夹内的 CSV 文件名 |
| `USE_REGEX_FOLDER` | `False` | `True` 时 `FOLDER_PATTERN` 按正则 |
| `USE_REGEX_CSV` | `False` | `True` 时 `CSV_PATTERN` 按正则 |
| `OVERWRITE` | `False` | 落盘时覆盖同名文件（否则自动 `_1`、`_2`…） |
| `USE_SUBPATH_PREFIX` | `False` | 目标文件名带「相对匹配文件夹」路径前缀（`_` 连接） |
| `LIST_OUT_FILE` | `None` | 写出路径列表的 txt；例如 `r"D:\out\list.txt"` |
| `VERBOSE` | `True` | 打印每个匹配文件夹下的 CSV |
| `PATHS_ONLY` | `False` | 仅打印 CSV 路径，无汇总 |

改配置后执行：

```bash
python find_csv_in_matched_folders.py
```

命令行参数（`-r`、`-f`、`--move-dir` 等）会**覆盖**配置区中的同名字段。

---

## 命令行（覆盖配置区时使用）

### 默认（读配置区）

```bash
python find_csv_in_matched_folders.py
python find_csv_in_matched_folders.py --paths-only
```

### 临时覆盖路径与格式

```bash
python find_csv_in_matched_folders.py ^
  --root "D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\2G" ^
  --folder-pattern "wifi_txrx_test_RXSens_*_mld_en0_cur_degree0" ^
  --csv-pattern "RX_*.csv" ^
  --move-dir "D:\users\gxu\collected_rx_csv"
```

### 仅导出路径列表

```bash
python find_csv_in_matched_folders.py -o "D:\users\gxu\out\matched_csv_list.txt"
```

或在配置区设 `LIST_OUT_FILE = r"D:\users\gxu\out\matched_csv_list.txt"`。

### 重名处理

| 情况 | 行为 |
|------|------|
| 默认 | 目标目录已有同名文件时自动追加 `_1`、`_2` … |
| `OVERWRITE=True` 或 `--overwrite` | 覆盖已有文件 |
| `USE_SUBPATH_PREFIX=True` 或 `--use-subpath-prefix` | 目标文件名含相对子路径，减少同名冲突 |

---

## 参数一览（CLI ↔ 配置区）

| CLI | 配置区变量 |
|-----|------------|
| `-r` / `--root` | `ROOT_SEARCH_PATH` |
| `-f` / `--folder-pattern` | `FOLDER_PATTERN` |
| `-c` / `--csv-pattern` | `CSV_PATTERN` |
| `--copy-dir` | `COPY_DIR` |
| `--move-dir` | `MOVE_DIR` |
| `--regex-folder` | `USE_REGEX_FOLDER` |
| `--regex-csv` | `USE_REGEX_CSV` |
| `-o` / `--list-out` | `LIST_OUT_FILE` |
| `-v` / `--verbose` | `VERBOSE` |
| `--paths-only` | `PATHS_ONLY` |
| `--overwrite` | `OVERWRITE` |
| `--use-subpath-prefix` | `USE_SUBPATH_PREFIX` |

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

stats = transfer_csv_hits(hits, r"D:\out\csv_flat", move=True, use_subpath_prefix=False)
print(stats.ok, stats.errors)
```

---

## 与 `spur_notch/move_spur_scan_result_csvs.py` 的区别

| 脚本 | 配置方式 | 侧重 |
|------|----------|------|
| `find_csv_in_matched_folders.py` | **文件顶部配置区** + 可选 CLI | RX/灵敏度目录检索；复制/移动；API 可编程 |
| `spur_notch/move_spur_scan_result_csvs.py` | `__main__` 块内变量 | 杂散扫描结果 CSV 整理 |

---

## 依赖

仅 Python 标准库：`os`、`fnmatch`、`re`、`shutil`、`argparse`。

---

## Skill 元数据（索引用）

- **名称**: find_csv_in_matched_folders  
- **描述**: 递归匹配文件夹名并收集 CSV；顶部配置区设置检索路径/格式与 MOVE_DIR 或 COPY_DIR；支持 list-out 与 CLI 覆盖。  
- **标签**: CSV, 文件检索, RX测试, rftest_data, 配置区  
