# analyze_merged_tx_result.py 脚本说明

## 功能描述

该脚本用于分析 `merged_tx_result.xlsx` 文件中的测试结果，特别是EVM（Error Vector Magnitude）与Rate、TX Power Set之间的关系。它提供了详细的统计分析和数据可视化功能。

## 主要功能

### 1. 数据基本信息展示
- 显示数据框的结构和内存使用情况
- 展示数据的前5行
- 检查是否包含需要的列（rate、tx_power_set(dBm)、evm）

### 2. 整体测试情况统计
- 总记录数
- 唯一Rate数量
- 唯一TX Power Set数量

### 3. 关键参数分布分析
- **Rate分布**：统计不同Rate的记录数量
- **TX Power Set分布**：统计不同TX Power Set的记录数量
- **EVM统计**：计算EVM的最小值、最大值、平均值和标准差

### 4. 分组统计分析
- **按Rate分组的EVM统计**：计算每个Rate的EVM描述性统计
- **按TX Power Set分组的EVM统计**：计算每个TX Power Set的EVM描述性统计

### 5. 可视化功能
- **EVM分布直方图**：展示EVM的分布情况
- **Rate vs EVM箱线图**：显示不同Rate下的EVM分布
- **TX Power Set vs EVM散点图**：显示EVM随TX Power Set的变化趋势
- **EVM变化热图**：可视化EVM随Rate和TX Power Set的变化
- **WiFi Format分布饼图**：显示WiFi格式的分布
- **FEC Coding分布饼图**：显示FEC编码的分布

### 6. 结果保存
- 保存原始数据和统计分析结果到Excel文件
- 保存所有图表到charts目录

## 使用方法

### 安装依赖
```bash
pip install pandas matplotlib seaborn
```

### 运行脚本
```bash
python analyze_merged_tx_result.py
```

### 运行可视化脚本
```bash
python generate_report.py
```

## 输入数据格式

脚本需要读取包含以下列的Excel文件：
- `rate`：数据速率（mcs0到mcs9）
- `tx_power_set(dBm)`：发射功率设置（-11dBm到20dBm）
- `evm`：误码矢量幅度（单位：dB）

## 输出文件

### Excel文件
- `merged_tx_result_analysis.xlsx`：基础数据分析结果
- `merged_tx_result_visual_report.xlsx`：可视化报告

### 图表文件
- `charts/evm_distribution.png`：EVM分布直方图
- `charts/rate_vs_evm.png`：Rate vs EVM箱线图
- `charts/tx_power_vs_evm.png`：TX Power Set vs EVM散点图
- `charts/evm_heatmap.png`：EVM变化热图
- `charts/wifi_format_distribution.png`：WiFi Format分布饼图
- `charts/fec_coding_distribution.png`：FEC Coding分布饼图

## 分析结果解读

### EVM与Rate的关系
- 随着Rate从mcs0到mcs9增加，EVM平均值从-29.20dB改善到-32.08dB
- 高Rate（如mcs8和mcs9）的EVM性能更好

### EVM与TX Power Set的关系
- TX Power Set与EVM之间存在明显的负相关关系，功率越高，EVM值越差
- 低功率（如-11dBm）时EVM最佳，高功率（如20dBm）时EVM最差

### 整体性能
- 平均EVM值为-30.70dB，标准差为2.31dB
- 大多数记录的EVM值在-33dB到-28dB之间

## 注意事项

1. 脚本需要使用Python 3.7或更高版本
2. 确保Excel文件路径正确
3. 图表生成需要matplotlib和seaborn库支持
4. 运行脚本时可能会消耗较多内存，建议关闭其他大型应用程序

## 改进建议

1. 添加更多的统计方法，如回归分析
2. 优化图表的可读性和美观性
3. 支持更多的数据输入格式
4. 添加交互式分析功能

## 作者信息

- 作者：未指定
- 创建日期：2024年
- 版本：1.0
