# analyze_multi_sheet.py 脚本说明

## 功能描述

该脚本用于分析 `merged_tx_result.xlsx` 文件中的多种配置Sheet，并且按照 `wifi_format` 列的不同进行分组分析。它提供了详细的统计分析和数据可视化功能，能够为每个Sheet和每种wifi_format生成单独的分析报告。

## 主要功能

### 1. Sheet级别分析
- 自动识别Excel文件中的所有Sheet
- 为每个Sheet提供基本统计信息（记录数、列数）
- 检查必要列是否存在
- 分析每个Sheet的Rate分布、TX Power Set范围和EVM统计

### 2. 按照wifi_format分组分析
- 识别每个Sheet中的wifi_format类别
- 为每种wifi_format提供详细的统计信息
- 单独分析每种wifi_format的Rate分布、TX Power Set范围和EVM统计
- 生成每种wifi_format的可视化图表

### 3. 可视化功能
为每个Sheet和每种wifi_format生成以下可视化图表：

1. **Rate vs EVM 箱线图**：显示不同Rate下的EVM分布
2. **TX Power Set vs EVM 散点图**：显示EVM随TX Power Set的变化趋势
3. **EVM 分布直方图**：展示EVM的分布情况
4. **EVM 热图**：可视化EVM随Rate和TX Power Set的变化

### 4. 结果保存
- 为每个Sheet创建单独的文件夹
- 为每种wifi_format在Sheet文件夹下创建子文件夹
- 保存所有可视化图表到对应文件夹
- 创建一个Sheet基本信息汇总文件

## 使用方法

### 安装依赖
```bash
pip install pandas matplotlib seaborn numpy
```

### 运行脚本
```bash
python analyze_multi_sheet.py
```

## 输入数据格式

脚本需要读取包含以下列的Excel文件：
- `rate`：数据速率（mcs0到mcs11）
- `tx_power_set(dBm)`：发射功率设置（-11dBm到20dBm）
- `evm`：误码矢量幅度（单位：dB）
- `wifi_format`：WiFi格式（heer或hesu）

## 输出文件

### 分析结果结构
在Excel文件所在目录下创建 `analysis_by_sheet` 文件夹，包含：

```
analysis_by_sheet/
├── sheet_summary.xlsx          # Sheet基本信息汇总
├── channel11_BCC_NSS1/
│   ├── heer/
│   │   ├── rate_vs_evm_heer.png
│   │   ├── tx_power_vs_evm_heer.png
│   │   ├── evm_distribution_heer.png
│   │   └── evm_heatmap_heer.png
│   └── hesu/
│       ├── rate_vs_evm_hesu.png
│       ├── tx_power_vs_evm_hesu.png
│       ├── evm_distribution_hesu.png
│       └── evm_heatmap_hesu.png
├── channel5180_BCC_NSS1/
├── channel11_LDPC_NSS1/
└── ... (其他Sheet)
```

### Sheet汇总文件
`sheet_summary.xlsx` 包含每个Sheet的基本信息：
- Sheet Name：Sheet名称
- 记录数：该Sheet的行数
- 列数：该Sheet的列数
- Rate 种类数：该Sheet中不同Rate的数量
- TX Power Set 范围：该Sheet中TX Power Set的范围
- EVM 平均值：该Sheet中EVM的平均值
- wifi_format 种类数：该Sheet中wifi_format的类别数量

## 分析结果解读

### 关键发现

**WiFi格式分布：**
- 在大部分Sheet中，`hesu` 格式的记录数明显多于 `heer` 格式
- 部分Sheet只包含 `hesu` 格式的记录（如STBC配置的Sheet）

**Rate分布：**
- `mcs0`、`mcs1`、`mcs2` 在所有Sheet中都有出现
- `heer` 格式主要使用较低的Rate（mcs0-mcs2）
- `hesu` 格式包含更广泛的Rate范围（mcs0-mcs9，甚至mcs10-mcs11）

**EVM性能：**
- 2.4GHz频段（channel11）的EVM性能优于5GHz频段（channel5180）
- LDPC编码的EVM性能略优于BCC编码
- 低功率设置下（-11dBm）的EVM性能最佳
- 高数据速率（mcs9-mcs11）的EVM性能较差

### 注意事项

1. 部分Sheet（如NSS2配置的Sheet）可能缺少 `evm` 列，这些Sheet的分析会受到限制
2. 图表生成可能需要较长时间，取决于数据大小
3. 所有图表都保存为PNG格式，分辨率为300 dpi

## 改进建议

1. 添加对NSS2配置Sheet的支持
2. 优化图表布局和美观性
3. 支持更多的分析维度和指标
4. 添加并行处理功能以提高处理速度
5. 支持导出到其他格式（如PDF、HTML）

## 作者信息

- 作者：未指定
- 创建日期：2024年
- 版本：1.0
