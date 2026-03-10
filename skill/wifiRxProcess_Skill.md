# WiFi RX 数据处理与合并脚本技能说明

## 脚本名称
`wifiRxProcess.py`

## 功能概述
该脚本整合了 `wifiRxPlot.py` 和 `file_merge.py` 的功能，专门用于处理 WiFi 接收灵敏度测试数据，特别是针对 `notch_enable0` 和 `notch_enable1` 两种配置的测试结果。

## 主要功能

### 1. 数据处理功能（wifiRxPlot.py）
- **CSV 文件读取**：自动遍历指定文件夹下的子文件夹和 CSV 文件
- **PER 计算**：计算 Packet Error Rate（包错误率）
- **EVM 计算**：计算 Error Vector Magnitude（误差向量幅度）
- **灵敏度曲线绘制**：生成 PER 与功率/ACR 的对数坐标图
- **灵敏度指标计算**：通过插值法计算灵敏度值（PER=10%或8%时的功率）
- **结果保存**：
  - Excel 文件（包含各测试用例的灵敏度数据）
  - PDF 文件（包含灵敏度曲线图表）

### 2. 文件合并功能（file_merge.py）
- **文件搜索**：在指定路径下搜索符合条件的文件夹和 Excel 文件
- **最新文件筛选**：只处理最新的 `sens_*.xlsx` 文件，避免重复数据
- **工作表合并**：将多个 Excel 文件的所有工作表合并到一个输出文件的单个工作表中
- **源信息标注**：新增一列标注每条数据的原工作表名称
- **数据统计**：提供合并过程的详细统计信息

### 3. 数据合并与格式化功能（新增）
- **Spur 文件生成**：合并 `notch_enable0` 和 `notch_enable1` 的数据生成 `xxx_spur.xlsx`
- **数据可视化**：为不同配置的数据添加颜色区分：
  - `notch_enable0` 数据使用黄色填充（#FFFF99）
  - `notch_enable1` 数据使用绿色填充（#CCFFCC）
- **数据完整性验证**：确保合并后的文件数据准确无误

## 使用方法

### 1. 配置修改
在脚本的 `main()` 函数中修改以下参数：

```python
def main():
    # 请根据实际路径修改
    root_path = r"D:\users\gxu\spur_scan\260310\5G\160m\he"
```

### 2. 运行脚本
```bash
python wifiRxProcess.py
```

### 3. 输出结果
- 在 `notch_enable0` 和 `notch_enable1` 文件夹中会生成：
  - `sens_YYYYMMDD_HHMMSS.xlsx`：原始数据处理结果（每次运行生成新文件）
  - `*.pdf`：每个子文件夹的灵敏度曲线图表

- 在根路径下会生成：
  - `5G_160m_he_notch_enable0.xlsx`：合并后的 notch_enable0 数据
  - `5G_160m_he_notch_enable1.xlsx`：合并后的 notch_enable1 数据
  - `5G_160m_he_spur.xlsx`：合并了两个 notch 配置的数据，带有颜色区分的表格

- **Spur 文件格式特点**：
  - 包含所有合并后的测试数据
  - `notch_enable0` 数据使用黄色填充（第 2-5 行）
  - `notch_enable1` 数据使用绿色填充（第 6-9 行）
  - 表头保持默认白色背景
  - 数据来源通过「原工作表名称」列标注

## 技术实现细节

### 关键函数

#### `wifi_rx_plot(foldername)`
- **参数**：目标文件夹路径
- **功能**：执行完整的数据处理流程
- **返回**：生成的 Excel 文件路径

#### `merge_all_sheets_to_one()`
- **参数**：
  - `root_path`：搜索的根路径
  - `folder_pattern`：文件夹匹配模式
  - `output_file`：合并后的输出文件路径
  - `xlsx_pattern`：Excel 文件匹配模式
  - `use_regex_folder`：是否使用正则表达式匹配文件夹
  - `use_regex_xlsx`：是否使用正则表达式匹配 Excel 文件
  - `sheet_name_col`：标注原工作表名称的列名
- **功能优化**：只处理最新的 `sens_*.xlsx` 文件，避免重复数据

#### `merge_notch_files_to_spur()`
- **参数**：
  - `root_path`：根路径
  - `notch0_file`：`notch_enable0` 文件路径
  - `notch1_file`：`notch_enable1` 文件路径
  - `output_file`：合并后的输出文件路径
- **功能**：
  - 合并两个 notch 配置的数据文件
  - 为不同配置的数据设置颜色区分
  - 保存为 `xxx_spur.xlsx` 文件
- **颜色方案**：
  - `notch_enable0`（第 2-5 行）：黄色填充（#FFFF99）
  - `notch_enable1`（第 6-9 行）：绿色填充（#CCFFCC）

### 灵敏度计算方法
- 使用对数插值法计算 PER=10%（非11b）或 8%（11b）时的功率值
- 插值精度：0.01 dB（sens_accuracy=100）
- 数据包数量：1000个（PAK_NUM=1000）

### 图表定制
- 颜色方案：14种自定义颜色
- 图表尺寸：11x18英寸（高分辨率）
- 坐标轴：
  - 功率范围：-110 至 -5 dBm
  - PER范围：1e-4 至 1（对数坐标）
  - ACR范围：-16 至 50 dB
  - EVM范围：-60 至 0 dB

## 依赖库
```
pandas
matplotlib
openpyxl
glob
os
math
datetime
time
fnmatch
re
```

## 注意事项
1. 确保输入数据的文件夹结构符合预期：根文件夹 > notch_enableX > 子文件夹 > 测试用例 > CSV文件
2. 脚本会自动创建输出文件，无需手动创建
3. 处理大型数据集时可能需要较长时间
4. 确保有足够的磁盘空间存储输出文件

## 版本历史
- 2026-03-09：初始版本，整合wifiRxPlot.py和file_merge.py功能
- 支持同时处理notch_enable0和notch_enable1两种配置
- 自动生成合并后的Excel文件

- 2026-03-10：新增功能
- 添加 `merge_notch_files_to_spur()` 函数
- 支持合并生成带有颜色区分的 `xxx_spur.xlsx` 文件
- 优化 `merge_all_sheets_to_one()` 函数，只处理最新文件避免重复数据
- `notch_enable0` 数据使用黄色填充，`notch_enable1` 数据使用绿色填充
