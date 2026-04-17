# analyze_diff_pwr_with_color.py 脚本说明

## 功能概述

该脚本用于分析和比较 CSV 文件中 `diff_pwr` 列的数据，特别关注小于指定阈值的行，并在 Excel 输出中使用颜色标记。它包括两个主要功能：

1. **所有行分析**：汇总所有 CSV 文件中的数据，将 `diff_pwr` 列小于指定阈值的行标记为红色，大于等于阈值的行标记为绿色，并统计小于阈值的行数和占比。
2. **边缘点分析**：专门统计边缘点数据（如 `tone_freq` 为最大值和最小值的点），同样使用颜色标记，并统计小于阈值的行数和占比。

## 配置区域

脚本顶部有以下可配置参数：

```python
SEARCH_DIRECTORY = r"D:\users\gxu\rx_iq\E22\regression_v2_0414"  # 搜索目录
FILE_PATTERN = "rx_iq_cal_res_*.csv"  # 文件名匹配模式
DIFF_PWR_THRESHOLD = 45  # diff_pwr 列的阈值（小于此值的行将被标记为红色）
OUTPUT_FILE_ALL = r"D:\users\gxu\scripts\output\all_rows_analysis.xlsx"  # 所有行分析输出文件
OUTPUT_FILE_EDGE = r"D:\users\gxu\scripts\output\edge_points_analysis.xlsx"  # 边缘点分析输出文件
```

## 使用方法

### 1. 修改配置

根据需要修改配置区域中的参数：

- `SEARCH_DIRECTORY`：指定要搜索 CSV 文件的根目录（支持递归搜索）。
- `FILE_PATTERN`：使用通配符指定文件名匹配模式（如 `rx_iq_cal_res_*.csv`）。
- `DIFF_PWR_THRESHOLD`：设置 `diff_pwr` 列的阈值，小于此值的行将被标记为红色。
- `OUTPUT_FILE_ALL` 和 `OUTPUT_FILE_EDGE`：指定输出的 Excel 文件路径。

### 2. 运行脚本

直接运行脚本：

```bash
python analyze_diff_pwr_with_color.py
```

## 输出结果

### 1. all_rows_analysis.xlsx

包含所有行数据的分析结果，分为两个工作表：

- **AllData**：所有原始数据，`diff_pwr` 列小于阈值的单元格填充红色，大于等于阈值的填充绿色。
- **Statistics**：统计信息，包括：
  - 总行数
  - 有效行数
  - 无效行数
  - 小于阈值的行数
  - 小于阈值的占比

### 2. edge_points_analysis.xlsx

包含边缘点数据的分析结果，同样分为两个工作表：

- **EdgePoints**：边缘点数据，`diff_pwr` 列小于阈值的单元格填充红色，大于等于阈值的填充绿色。
- **Statistics**：统计信息，包括：
  - 总边缘点行数
  - 有效行数
  - 无效行数
  - 小于阈值的行数
  - 小于阈值的占比

## 技术实现

### 使用的库

- `pandas`：用于读取和处理 CSV 文件
- `openpyxl`：用于处理 Excel 文件并添加填充色
- `glob`：用于递归搜索文件
- `os`：用于文件路径处理

### 核心功能

1. **递归搜索文件**：使用 `glob` 库递归搜索指定目录下符合文件名模式的 CSV 文件。
2. **数据读取和处理**：使用 `pandas` 读取 CSV 文件，并处理列名中的大小写和空格。
3. **颜色标记**：使用 `openpyxl` 库在 Excel 文件中添加颜色填充。
4. **统计分析**：统计总行数、有效行数、小于阈值的行数和占比。

## 注意事项

- 脚本需要安装 `pandas` 和 `openpyxl` 库，可以使用以下命令安装：
  ```bash
  pip install pandas openpyxl
  ```

- 确保指定的输出目录存在，否则会自动创建。
- 如果 CSV 文件中不包含 `diff_pwr`、`bw` 或 `tone_freq` 列，会显示警告信息并跳过该文件。
- 如果 `diff_pwr` 列包含无效值（如非数字值），会显示警告信息并跳过该行。