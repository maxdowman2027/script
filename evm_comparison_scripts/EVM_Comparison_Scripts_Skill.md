# EVM对比脚本技能文档

## 概述

这些Python脚本用于比较不同版本的WiFi芯片（如WiFi7和RLS4.0）在相同测试条件下的EVM（误差向量幅度）性能差异。它们提供了详细的数据分析、可视化图表和报告功能，帮助工程师识别和定位性能问题。

## 脚本功能

### 1. 核心对比脚本

#### `compare_evm_rls4_wifi7_hesu.py`
**功能**：比较RLS4.0版本和WiFi7版本在hesu格式下的EVM性能差异
**特点**：
- 支持多Sheet Excel文件比较
- 自动匹配相同的测试条件（wifi_format、rate、tx_pwr）
- 计算EVM差异和统计信息
- 为EVM值和差值添加填充色以提高可读性
- 生成详细的对比结果和统计摘要
- 可视化差异分布和趋势
- 生成HTML报告

**使用方法**：
```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np
from datetime import datetime
```

#### `compare_evm.py`
**功能**：通用的EVM对比脚本，适用于不同版本和格式的比较

#### `compare_evm_by_tx_pwr.py`
**功能**：按发射功率分组比较EVM性能

#### `compare_evm_old_new.py`
**功能**：比较旧版本和新版本的EVM性能

#### `compare_evm_rls4_wifi7.py`
**功能**：专门用于比较RLS4.0和WiFi7版本的EVM性能

#### `compare_evm_wifi7_rls4.py`
**功能**：与`compare_evm_rls4_wifi7.py`类似，但可能有不同的实现细节

#### `compare_evm_rls3_rls4.py`
**功能**：比较RLS3.0和RLS4.0版本的EVM性能差异
**特点**：
- 支持比较RLS3.0和RLS4.0版本的测试结果
- 自动匹配相同的测试条件（wifi_format、rate、tx_pwr）
- 计算EVM差异和统计信息
- 为EVM值和差值添加填充色以提高可读性
- 生成详细的对比结果和统计摘要
- 可视化差异分布和趋势
- 生成HTML报告

#### `compare_evm_by_wifi_format.py`
**功能**：比较不同wifi_format之间，相同tx_power_set(dBm)和rate情况下的EVM差异
**特点**：
- 分析单个版本中不同WiFi格式之间的EVM差异
- 支持相同测试条件下的格式间比较
- 识别显著差异（>2dB）的测试条件
- 生成详细的Excel报告和可视化图表
- 提供针对格式间比较的建议

#### `compare_evm_generic.py`
**功能**：通用的 EVM 对比脚本，支持比较任意两个版本的 WiFi 芯片测试结果（典型输入为 `merge_csv_to_xlsx.py` 产出的 `merged_tx_result.xlsx`）。

**特点**：
- 完全参数化：在脚本顶部 `main()` 内修改 `file1` / `file2` / `version1` / `version2` / `output_dir` 后直接运行
- 支持比较任意两个 Excel 文件的 EVM 测试结果
- **Sheet 配对（v1.4）**：优先大小写不敏感的全名匹配；否则按 `merge_csv_to_xlsx` 命名规则解析 `(channel, BCC|LDPC, NSS1|NSS2|STBC)` 三元组匹配，避免旧版子串规则误配（如 NSS1 对上 NSS2、或无关 sheet 因含 `ht` 被配对）
- 自动匹配相同的测试条件（`wifi_format`、`rate`、`tx_power_set(dBm)`）
- **额外参数列一致性**：合并时还要求两侧共有的参数列一致，包括 `giltf`, `heltf`, `short_gi`, `cbw`, `ht_dup`, `suer_dcm`, `afactor`, `pe`
- **单流 EVM 列解析（v1.4）**：两侧分别用 `_resolve_evm_column()` 选取列（优先级：`evm` → `evm_aver(dB)` → `aver_evmAll` → `evm_nss0` → `evm_nss1`）；版本 2 不再硬编码只读 `evm` 列
- **NSS2 双流对比（v1.4）**：当 sheet 名含 `NSS2`（或解析后缀为 NSS2）且两侧均有 `evm_nss0` + `evm_nss1` 时，进入 `_compare_dataframes_nss2_dual`：
  - 分别计算 `evm_diff_nss0`、`evm_diff_nss1`（版本2 − 版本1）
  - 汇总列：`evm_diff` = 两链 signed diff 的均值；`abs_diff` = 两链 |diff| 的最大值（最差链）
  - detailed / summary xlsx、openpyxl 着色、散点/直方图均覆盖两条空间流
  - `comparison_result` 中 `nss2_dual_stream: True`，EVM 列记为 `evm_nss0+evm_nss1`
- 计算 EVM 差异和统计信息；Excel 中 EVM 字符串（如 `'--'`）会先 `to_numeric` 再作差
- 为 EVM 值和差值添加填充色；生成 HTML 报告
- **匹配率指标（HTML）**：「版本1 行匹配率」= 版本1 中连接键在版本2 至少出现一次的行数 ÷ 版本1 总行数（≤100%）。「Inner 配对行数」= inner merge 行数；连接键重复时可大于版本1 行数

**Sheet 命名规则（与 `merge_csv_to_xlsx` 一致）**：
```text
channel{num}_{BCC|LDPC}[_{NSS1|NSS2|STBC}]
示例：channel11_LDPC_NSS2、channel36_BCC
```

**使用方法**：
```python
# 修改 compare_evm_generic.py 顶部 main() 内变量后运行
file1 = r"D:\path\to\merged_tx_result_v1.xlsx"
file2 = r"D:\path\to\merged_tx_result_v2.xlsx"
version1 = "rls4_0424"
version2 = "rls4_0526"
output_dir = r"D:\path\to\evm_comparison_out"

python evm_comparison_scripts/compare_evm_generic.py
```

### 2. 辅助脚本

#### `view_comparison_results.py`
**功能**：查看比较结果的辅助脚本
**特点**：
- 读取比较结果Excel文件
- 显示每个Sheet的统计信息
- 显示EVM差异的平均值、最大值和最小值
- 显示前10个最大EVM差异的测试条件

**使用方法**：
```python
import pandas as pd

def view_comparison_results(file_path):
    xls = pd.ExcelFile(file_path)

    for sheet_name in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name)
            print(f"\n=== Sheet: {sheet_name} ===")
            print(f"Number of rows: {len(df)}")
            print(f"Columns: {list(df.columns)}")

            if 'evm_diff' in df.columns:
                avg_diff = df['evm_diff'].mean()
                max_diff = df['evm_diff'].max()
                min_diff = df['evm_diff'].min()
                print(f"EVM Diff: Avg={avg_diff:.2f}, Max={max_diff:.2f}, Min={min_diff:.2f}")
        except Exception as e:
            print(f"Error reading sheet {sheet_name}: {e}")
```

## 文件结构

```
evm_comparison_scripts/
├── compare_evm_rls4_wifi7_hesu.py   # RLS4.0 vs WiFi7 (hesu) 比较
├── compare_evm.py                  # 通用EVM比较
├── compare_evm_by_tx_pwr.py        # 按发射功率分组比较
├── compare_evm_old_new.py          # 旧版本vs新版本比较
├── compare_evm_rls4_wifi7.py       # RLS4.0 vs WiFi7比较
├── compare_evm_wifi7_rls4.py       # WiFi7 vs RLS4.0比较
├── compare_evm_rls3_rls4.py        # RLS3.0 vs RLS4.0比较
├── compare_evm_by_wifi_format.py   # 不同wifi_format之间EVM比较
├── compare_evm_generic.py          # 通用的EVM对比脚本（完全参数化）
├── view_comparison_results.py      # 结果查看辅助脚本
├── analyze_sample_results.py       # 示例结果分析脚本
└── EVM_Comparison_Scripts_Skill.md # 技能文档
```

## 版本提交记录

### v1.0 (2026-04-08)
- 初始版本，包含基础的EVM比较功能
- 创建了`compare_evm_rls4_wifi7_hesu.py`、`compare_evm_rls4_wifi7.py`等专门版本的比较脚本
- 支持hesu格式的EVM比较

### v1.1 (2026-04-08)
- 添加了`compare_evm_rls3_rls4.py`脚本，支持比较RLS3.0和RLS4.0版本
- 添加了`compare_evm_by_wifi_format.py`脚本，支持比较不同wifi_format之间的EVM差异
- 优化了脚本的输出格式和颜色填充功能

### v1.2 (2026-04-09)
- 添加了`compare_evm_generic.py`脚本，支持完全参数化的EVM比较
- 支持比较任意两个版本的WiFi芯片测试结果
- 通过命令行参数自定义版本名称和输出目录
- 代码结构重构，提高了脚本的通用性和可维护性

### v1.3 (2026-05-07)
- **`compare_evm_generic.py`**：修正 HTML「匹配率」语义。旧逻辑用 inner merge 行数 ÷ 版本1 行数，连接键重复时 inner 行数可因笛卡尔积大于版本1 行数，导致百分比大于 100%。现新增逐行统计：版本1 中 merge 键在版本2 至少存在一次的行数 ÷ 版本1 总行数（≤100%）；另单独展示 Inner 配对行数。HTML 整体与各 Sheet 增加对应列说明。

### v1.4 (2026-05-27)
- **`compare_evm_generic.py` — Sheet 配对**：移除 `'2g'/'5g'/'ht'/'vht'` 子串匹配；新增 `parse_merged_tx_sheet_name()` / `find_matching_sheet()`，按 `channel{N}_{BCC|LDPC}[_{NSS1|NSS2|STBC}]` 精确配对，防止 NSS1 与 NSS2 sheet 错配。
- **`compare_evm_generic.py` — 单流 EVM 列**：新增 `_resolve_evm_column()`；版本2 合并列由硬编码 `evm` 改为与版本1 对称解析（支持 `evm_nss0` 等）；统计与 openpyxl 着色使用动态 `col_v1` / `col_v2`。
- **`compare_evm_generic.py` — NSS2 双流**：新增 `_compare_dataframes_nss2_dual()`。NSS2 sheet 且两侧均有 `evm_nss0`、`evm_nss1` 时，分别输出 `evm_diff_nss0` / `evm_diff_nss1`；summary 含 `mean_diff_nss0`、`mean_diff_nss1` 及分链均值列；`plot_comparison(..., nss2_pair=...)` 直方图叠加两链、散点分链绘制。
- **`compare_evm_generic.py` — 结果元数据**：`comparison_result` 增加 `nss2_dual_stream`、`{version2}_evm_col` 字段，便于 HTML/后续脚本区分单流与 NSS2 对比。

## 输出格式

### 详细对比结果（单流 / NSS1）
- 文件命名：`{sheet1}_vs_{sheet2}_detailed.xlsx`
- 典型列：`wifi_format`, `rate`, `tx_power_set(dBm)`, `{evm_col}_{version1}`, `{evm_col}_{version2}`, `evm_diff`, `abs_diff`
- 特点：为 EVM 值与差值添加颜色填充

### 详细对比结果（NSS2 双流，`compare_evm_generic.py` v1.4+）
- 同上文件名；额外列：
  - `evm_nss0_{version1}`, `evm_nss0_{version2}`, `evm_nss1_{version1}`, `evm_nss1_{version2}`
  - `evm_diff_nss0`, `evm_diff_nss1`, `abs_diff_nss0`, `abs_diff_nss1`
  - `evm_diff`（两链 signed diff 均值）, `abs_diff`（两链 |diff| 最大值）
- openpyxl：四列 EVM + 三个 diff 列均按阈值着色

### 统计摘要（单流）
- 文件命名：`{sheet1}_vs_{sheet2}_summary.xlsx`
- 列名：
  - `wifi_format`, `rate`
  - `count`, `mean_diff`, `median_diff`, `std_diff`, `min_diff`, `max_diff`, `mean_abs_diff`
  - `version1_mean_evm`, `version1_median_evm`, `version1_std_evm`
  - `version2_mean_evm`, `version2_median_evm`, `version2_std_evm`

### 统计摘要（NSS2 双流）
- 在单流列基础上增加：`mean_diff_nss0`, `mean_diff_nss1`, `version1_mean_evm_nss0`, `version2_mean_evm_nss0`, `version1_mean_evm_nss1`, `version2_mean_evm_nss1`
- 热力图 / 箱线图的 `mean_diff` 基于合并 `evm_diff`（两链均值）

### 可视化图表（`{sheet1}_vs_{sheet2}/` 子目录）
- `evm_diff_distribution.png`：单流为 ΔEVM 直方图；NSS2 为 nss0 / nss1 双直方图叠加
- `evm_diff_heatmap.png`：按 `wifi_format` × `rate` 的平均 ΔEVM
- `evm_comparison_scatter.png`：单流为版本1 vs 版本2 散点；NSS2 为 nss0 / nss1 分链散点 + 理想对角线
- `evm_diff_by_format.png`, `evm_diff_by_rate.png`：按格式 / 速率的箱线图

### HTML报告
- 包含整体对比统计
- Sheet级对比详情
- 主要发现
- 使用建议
- 文件描述
- **`compare_evm_generic.py` 专用**：整体统计区分「版本1 行匹配率」与「Inner 配对行数」；Sheet 表含 Inner 配对行数、V1 可匹配行数、V1 行匹配率，避免将 inner 行数误当作「匹配率」导致大于 100% 的误解

## 使用场景

1. **版本间性能比较**：比较不同版本的WiFi芯片在相同条件下的EVM性能
2. **硬件验证**：验证新硬件设计是否满足EVM规格要求
3. **问题定位**：识别特定测试条件下的性能问题
4. **批量数据分析**：处理大量测试数据，快速识别异常值

## 依赖库

```
pandas
openpyxl
matplotlib
seaborn
numpy
```

## 执行方式

### 1. 使用专门版本脚本（针对特定版本比较）
```bash
cd evm_comparison_scripts
# RLS4.0 vs WiFi7 (hesu格式)
python compare_evm_rls4_wifi7_hesu.py

# RLS3.0 vs RLS4.0
python compare_evm_rls3_rls4.py

# 按发射功率分组比较
python compare_evm_by_tx_pwr.py

# 比较不同wifi_format之间的EVM差异
python compare_evm_by_wifi_format.py
```

### 2. 使用通用脚本（`compare_evm_generic.py`）
```bash
# 在仓库根目录：先改脚本内 file1/file2/version1/version2/output_dir
python evm_comparison_scripts/compare_evm_generic.py
```

## 输入文件格式

Excel 文件（通常为多 Sheet 的 `merged_tx_result.xlsx`）应包含：

**连接键（必需）**
- `wifi_format`：WiFi 格式（如 hesu、ht、vht、eht 等）
- `rate`：速率（如 mcs0、mcs11 等）
- `tx_power_set(dBm)`：发射功率（dBm）

**EVM 列（至少一种）**
- 单流 / NSS1：`evm`，或 `evm_aver(dB)` / `aver_evmAll`
- NSS2：`evm_nss0` 与 `evm_nss1`（v1.4 起两侧同时存在时触发双流对比）

**Sheet 名（推荐，与 merge_csv_to_xlsx 一致）**
- `channel{N}_{BCC|LDPC}` 或 `channel{N}_{BCC|LDPC}_{NSS1|NSS2|STBC}`

**可选**
- `psdu_crc`：Fail 行在 detailed xlsx 中标红
- 参数列：`giltf`, `heltf`, `short_gi`, `cbw`, `ht_dup`, `suer_dcm`, `afactor`, `pe`（两侧共有则纳入 merge 键）

## 注意事项

1. 确保输入文件的列名与脚本期望一致；NSS2 数据需同时含 `evm_nss0` 和 `evm_nss1`
2. 多 Sheet 文件按 **全名或 channel/coding/NSS 后缀** 配对；NSS1 与 NSS2 不会因子串规则误配
3. 输出目录会自动创建；重复运行会覆盖同名 xlsx / png
4. NSS2 汇总 `evm_diff` 为两链均值，排查单链问题时请直接看 `evm_diff_nss0` / `evm_diff_nss1` 或 summary 中的 `mean_diff_nss0` / `mean_diff_nss1`
5. 脚本需要读写权限；依赖 `pandas`, `openpyxl`, `matplotlib`, `seaborn`, `numpy`

## 扩展建议

1. 添加更多的统计方法和可视化图表
2. 支持更多的输入格式（如CSV文件）
3. 添加参数化配置文件
4. 支持并行处理以提高大文件处理速度

---

**文档版本**：1.4  
**更新日期**：2026-05-27  
**作者**：[gxu]  
**联系邮箱**：[gxu@example.com]