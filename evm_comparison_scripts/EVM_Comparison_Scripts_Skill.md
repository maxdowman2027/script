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
**功能**：通用的EVM对比脚本，支持比较任意两个版本的WiFi芯片测试结果
**特点**：
- 完全参数化的脚本，通过代码变量直接配置输入参数
- 支持比较任意两个Excel文件的EVM测试结果
- 自动匹配相同的测试条件（wifi_format、rate、tx_pwr）
- **新增功能**：在比较EVM时，还会考虑其他参数列的一致性
- 支持的额外参数列包括：giltf, heltf, short_gi, cbw, ht_dup, suer_dcm, afactor, pe
- 智能识别两个DataFrame共有的参数列进行合并
- 计算EVM差异和统计信息
- 为EVM值和差值添加填充色以提高可读性
- 生成详细的对比结果和统计摘要
- 可视化差异分布和趋势
- 生成HTML报告
- **匹配率指标（HTML）**：「版本1 行匹配率」= 版本1 中「连接键在版本2 至少出现一次」的行数 ÷ 版本1 总行数（每行最多计一次，**不会超过 100%**）。「Inner 配对行数」= `pd.merge(..., how='inner')` 的结果行数；当同一连接键在两侧有多行重复时会产生笛卡尔积，**可大于**版本1行数。详细数据仍以 `*_detailed.xlsx` 中的 inner 结果为准。
**使用方法**：
```python
# 修改脚本顶部的变量
file1 = r"D:\path\to\your\file1.xlsx"
file2 = r"D:\path\to\your\file2.xlsx"
version1 = "rls3"
version2 = "rls4"
output_dir = r"D:\path\to\your\output\directory"

# 直接运行脚本
python compare_evm_generic.py
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

## 输出格式

### 详细对比结果
- 文件命名：`{sheet1}_vs_{sheet2}_detailed.xlsx`
- 列名：wifi_format, rate, tx_power_set(dBm), evm_rls4, evm_wifi7, evm_diff, abs_diff
- 特点：为EVM值添加了颜色填充，便于快速识别问题

### 统计摘要
- 文件命名：`{sheet1}_vs_{sheet2}_summary.xlsx`
- 列名：
  - wifi_format, rate
  - count：匹配的测试数量
  - mean_diff, median_diff, std_diff：平均、中位数、标准差
  - min_diff, max_diff：最小、最大差值
  - mean_abs_diff：平均绝对差值
  - rls4_mean_evm, rls4_median_evm, rls4_std_evm：RLS4.0的统计信息
  - wifi7_mean_evm, wifi7_median_evm, wifi7_std_evm：WiFi7的统计信息

### 可视化图表
- EVM差异分布直方图
- 按格式和速率的平均差值热力图
- RLS4.0 vs WiFi7 EVM比较散点图
- 按格式的EVM差异箱线图
- 按速率的EVM差异箱线图

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

### 2. 使用通用脚本（支持任意版本比较）
```bash
cd evm_comparison_scripts

# 基本用法（自动命名为version1和version2）
python compare_evm_generic.py file1.xlsx file2.xlsx

# 自定义版本名称
python compare_evm_generic.py file1.xlsx file2.xlsx -v1 rls3 -v2 rls4

# 指定输出目录
python compare_evm_generic.py file1.xlsx file2.xlsx -o ./comparison_result

# 完整参数说明
python compare_evm_generic.py --help
```

## 输入文件格式

Excel文件应包含以下列：
- `wifi_format`：WiFi格式（如hesu、ht、vht等）
- `rate`：速率（如mcs0、mcs1等）
- `tx_power_set(dBm)`：发射功率（dBm）
- `evm`：EVM值（dB）

## 注意事项

1. 确保输入文件的列名与脚本期望的列名一致
2. 对于包含多个Sheet的Excel文件，脚本会自动比较匹配的Sheet
3. 输出目录会自动创建，如果已存在则会覆盖
4. 脚本需要适当的权限来读写文件

## 扩展建议

1. 添加更多的统计方法和可视化图表
2. 支持更多的输入格式（如CSV文件）
3. 添加参数化配置文件
4. 支持并行处理以提高大文件处理速度

---

**文档版本**：1.2
**更新日期**：2026-04-09
**作者**：[gxu]
**联系邮箱**：[gxu@example.com]