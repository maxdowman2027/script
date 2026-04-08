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
├── view_comparison_results.py      # 结果查看辅助脚本
└── EVM_Comparison_Scripts_Skill.md # 技能文档
```

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

```bash
cd evm_comparison_scripts
python compare_evm_rls4_wifi7_hesu.py
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

**文档版本**：1.0
**更新日期**：2026-04-08
**作者**：[gxu]
**联系邮箱**：[gxu@example.com]