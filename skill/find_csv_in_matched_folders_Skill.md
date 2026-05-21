# find_csv_in_matched_folders.py — 按文件夹名模式检索 CSV

## 脚本概述

`find_csv_in_matched_folders.py` 在指定根路径下**递归**查找**文件夹 basename** 符合通配符或正则的目录，再在这些目录内（含子目录）收集符合命名规则的 **CSV**。  
根据 CSV **相对 `ROOT_SEARCH_PATH` 的路径层级** 自动解析射频测试配置（如 `2G`、`phymd20`、`20m`、`ldpc`、`he`），用于打印、列表导出与复制/移动时的文件名前缀。

典型场景：在 `rftest_data\2G` 下找到 `wifi_txrx_test_RXSens_*_mld_en0_cur_degree0` 类目录，汇总 `RX_*.csv` 并带上路径配置标签。

**日常用法**：改脚本顶部 **「配置区」** 后执行 `python find_csv_in_matched_folders.py`。

---

## 路径层级解析（`extract_path_config`）

以检索根目录为 `...\rftest_data\2G` 为例，CSV 路径：

```text
...\2G\phymd20\20m\ldpc\he\wifi_txrx_test_RXSens_...\FPGA752_...\rx_20260521\RX_mcs0....csv
```

解析结果：

| 字段 | 示例值 | 识别规则 |
|------|--------|----------|
| `band` | `2G` | 检索根 basename 或路径中的 `2G`/`5G`/`6G` |
| `phymd` | `phymd20` | `phymd` + 数字 |
| `bandwidth` | `20m` | `20m`、`40m` 等 |
| `coding` | `ldpc` | `ldpc` / `bcc` |
| `wifi_format` | `he` | `he`、`vht`、`ax`、`be`、`hesu` 等 |
| `testcase_folder` | `wifi_txrx_test_...` | 以 `wifi_txrx` 开头 |
| `run_folder` | `FPGA752_FPGA761_20260521` | 以 `FPGA` 开头 |
| `rx_folder` | `rx_20260521` | 以 `rx_` 开头 |

- **`config_tag()`**：`2G_phymd20_20m_ldpc_he`（用于日志与文件名前缀）  
- **`summary()`**：`band=2G, phymd=phymd20, bandwidth=20m, ...`

---

## 工作流程

```text
配置区 ROOT_SEARCH_PATH + FOLDER_PATTERN + MOVE_DIR/COPY_DIR
    → 匹配文件夹 → 收集 CSV
        → extract_path_config（路径层级）
            → 打印 [config_tag] / 导出 TSV
            → 可选复制/移动（USE_CONFIG_PREFIX 时文件名加标签前缀）
```

---

## 脚本内配置（文件顶部「配置区」）

### 必改三项

| 变量 | 含义 |
|------|------|
| `ROOT_SEARCH_PATH` | 递归检索根目录（常为 `...\rftest_data\2G`） |
| `FOLDER_PATTERN` | 文件夹 basename 通配符 |
| `MOVE_DIR` / `COPY_DIR` | 落盘目标（二选一，`None` 仅检索） |

### 与路径解析相关

| 变量 | 默认 | 含义 |
|------|------|------|
| `USE_CONFIG_PREFIX` | `True` | 复制/移动时在文件名前加 `2G_phymd20_20m_ldpc_he_` |
| `LIST_OUT_WITH_CONFIG` | `True` | `--list-out` 写 **TSV**（含 config 列）；`--list-plain` 仅路径 |

其它：`CSV_PATTERN`、`VERBOSE`、`USE_SUBPATH_PREFIX`、`OVERWRITE` 等见脚本内注释。

---

## 命令行

```bash
python find_csv_in_matched_folders.py
python find_csv_in_matched_folders.py -v
python find_csv_in_matched_folders.py -o matched.tsv
python find_csv_in_matched_folders.py --list-plain -o paths_only.txt
python find_csv_in_matched_folders.py --move-dir "D:\out" --no-config-prefix
```

| 参数 | 配置区变量 |
|------|------------|
| `-r` / `--root` | `ROOT_SEARCH_PATH` |
| `-f` / `--folder-pattern` | `FOLDER_PATTERN` |
| `--move-dir` / `--copy-dir` | `MOVE_DIR` / `COPY_DIR` |
| `--use-config-prefix` / `--no-config-prefix` | `USE_CONFIG_PREFIX` |
| `--list-plain` | 关闭 TSV 配置列（配合 `-o`） |

---

## Python API

```python
from find_csv_in_matched_folders import (
    extract_path_config,
    find_csv_in_matched_folders,
    transfer_csv_hits,
)

cfg = extract_path_config(csv_path, root_search_path)
print(cfg.config_tag())   # 2G_phymd20_20m_ldpc_he

hits = find_csv_in_matched_folders(root, folder_pattern, "*.csv")
for h in hits:
    print(h.path_config.summary(), h.csv_path)

transfer_csv_hits(hits, dest_dir, move=False, use_config_prefix=True)
```

---

## 依赖

Python 标准库。

---

## Skill 元数据

- **名称**: find_csv_in_matched_folders  
- **描述**: 递归匹配文件夹收集 CSV；从 rftest_data 路径解析 band/phymd/bw/coding/format；支持配置区、TSV 导出与带标签落盘。  
- **标签**: CSV, 文件检索, RX测试, rftest_data, 路径解析  
