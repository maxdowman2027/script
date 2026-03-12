
# WiFi RX 灵敏度计算与对比图表脚本技能说明

## 脚本名称
`calculate_sensitivity_and_plot.py`

## 功能概述
该脚本专门用于处理WiFi接收灵敏度测试数据，计算并对比`notch_en=0`和`notch_en=1`两种配置下的灵敏度，以`cw_pow`为横坐标，灵敏度为纵坐标绘制对比图表。

## 主要功能

### 1. 数据处理功能
- **CSV文件读取**：读取指定路径的CSV文件
- **PER计算**：计算Packet Error Rate（包错误率）：`per = 1 - min(rxnum, 1000)/1000`
- **灵敏度计算**：使用对数插值法计算灵敏度值（PER=10%时的功率）
- **对比图表绘制**：生成`notch_en=0`和`notch_en=1`两种配置下的灵敏度对比图表

### 2. 对比图表特点
- **横坐标**：cw_pow（dBm）
- **纵坐标**：灵敏度（dBm）
- **数据点**：不同notch_en配置下的灵敏度值
- **颜色区分**：
  - `notch_en=0`数据使用红色（#FF0000）
  - `notch_en=1`数据使用蓝色（#0000FF）

## 使用方法

### 1. 配置修改
在脚本的`__main__`函数中修改以下参数：

```python
if __name__ == "__main__":
    # 输入参数
    csv_file_path = "D:/chip_test/dev/chip_rx/eagletest/rftest_data/wifi_notch_test_spur_test/FPGA752_FPGA761_20260312/rx_20260312/RX_mcs9vht_20260312_144821.csv"
    output_pdf_path = "D:/chip_test/dev/chip_rx/eagletest/rftest_data/wifi_notch_test_spur_test/FPGA752_FPGA761_20260312/rx_20260312/sensitivity_comparison.pdf"
```

### 2. 运行脚本
```bash
python calculate_sensitivity_and_plot.py
```

### 3. 输出结果
- `sensitivity_comparison.pdf`：包含`notch_en=0`和`notch_en=1`灵敏度对比图表的PDF文件

## 技术实现细节

### 关键函数

#### `calculate_sensitivity(per_values, pow_values, sens_accuracy=100)`
- **参数**：
  - `per_values`：PER值列表
  - `pow_values`：对应的功率值列表
  - `sens_accuracy`：灵敏度计算精度（默认100）
- **功能**：使用对数插值法计算灵敏度
- **返回**：灵敏度值（dBm）

#### `process_csv_file(file_path)`
- **参数**：CSV文件路径
- **功能**：处理CSV文件，计算不同notch_en条件下的灵敏度
- **返回**：包含cw_pow、notch_en=0灵敏度、notch_en=1灵敏度的DataFrame

#### `plot_sensitivity_comparison(results, output_pdf_path)`
- **参数**：
  - `results`：包含灵敏度数据的DataFrame
  - `output_pdf_path`：PDF文件输出路径
- **功能**：绘制灵敏度对比图表并保存为PDF文件

### 灵敏度计算方法
- 使用对数插值法计算PER=10%（log10(0.1) = -1）时的功率值
- 插值精度：0.01 dB（sens_accuracy=100）
- 数据包数量：1000个（PAK_NUM=1000）

### 图表定制
- 颜色方案：红色（#FF0000）用于notch_en=0，蓝色（#0000FF）用于notch_en=1
- 图表尺寸：11x8英寸（高分辨率）
- 坐标轴：
  - cw_pow范围：根据数据自动调整
  - 灵敏度范围：根据数据自动调整

## 依赖库
```
pandas
matplotlib
math
```

## 注意事项
1. 确保输入数据的CSV文件格式正确，包含以下列：rate, notch_en, rx_chan, cw_chan, ht40_index, tx_freq, rfpwr, cw_pow, rxnum, rssi, gain, err, fcs, freq, rssi_min, rssi_max, total_sync
2. 脚本会自动去除列名的前导空格
3. 处理大型数据集时可能需要较长时间
4. 确保有足够的磁盘空间存储输出文件

## 版本历史
- 2026-03-12：初始版本，实现灵敏度计算与对比图表功能

