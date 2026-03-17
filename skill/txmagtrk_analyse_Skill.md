# txmagtrk_analyse.py 脚本说明文档

## 脚本概述

txmagtrk_analyse.py 是一个用于分析 Wi-Fi TX（发射）磁跟踪（Magnetic Tracking）测试数据的 Python 脚本。它提供了全面的测试结果分析功能，包括绘制图表、数据检查和结果保存。

## 主要功能

### 1. 数据处理功能
- **CSV文件读取**：读取指定路径的CSV文件
- **数据预处理**：处理数据类型转换和缺失值处理
- **数据分组**：按多个参数对测试数据进行分组分析
- **图表绘制**：生成包含EVM（误差向量幅度）对比图表的PDF报告
- **内存优化**：采用逐个图表写入PDF的方式，大幅降低内存占用

### 2. 数据分析功能
- **磁跟踪对比分析**：比较 `trk_en=0`（磁跟踪关闭）和 `trk_en=1`（磁跟踪打开）两种状态下的EVM性能
- **多参数分组**：支持按 `start_point`、`win_len`、`numsymbols`、`chn_ofst` 和 `ru_size` 五个参数进行分组分析
- **多EVM指标支持**：支持同时分析 `evm` 和 `evm_nss1` 两个EVM指标
- **自定义参数支持**：支持通过配置添加自定义参数列（如 `start_mode`）

### 3. 图表特点
- **横坐标**：测试功率（test_power）
- **纵坐标**：EVM（evm或evm_nss1，单位：dB）
- **曲线样式**：
  - trk_en=0, amplitude=0：实线圆 - 磁跟踪关闭
  - trk_en=0, amplitude=1：虚线三角 - 磁跟踪打开（仪表）
  - trk_en=1, amplitude=0：实线方 - 磁跟踪打开（E22芯片）
  - trk_en=1, amplitude=1：虚线菱形 - 磁跟踪打开（E22芯片和仪表）
- **颜色区分**：不同test_rate和自定义参数组合使用不同颜色

## 使用方法

### 1. 修改路径
在脚本的 `__main__` 函数中修改以下参数：

```python
if __name__ == "__main__":
    CSV_DIR = r"D:\users\gxu\txmagtrk\260317_fake_tb\2"
    SAVE_ROOT_DIR = r"D:\users\gxu\txmagtrk\260317_fake_tb\2\result"
    RECURSIVE_SEARCH = False
    CONFIG['CUSTOM_PARAM_COL'] = 'start_mode'
    CONFIG['REQUIRE_CUSTOM_PARAM'] = False
    CONFIG['REQUIRE_EVM_NSS1'] = False
```

### 2. 运行脚本
```bash
python txmagtrk_analyse.py
```

### 3. 输入文件格式
脚本需要输入格式为 `*.csv` 的文件，包含以下字段：
- `trk_en`：磁跟踪使能（0/1）
- `amplitude`：幅度（0/1）
- `test_rate`：测试速率（如 mcs0）
- `test_power`：测试功率（dBm）
- `evm`：EVM值（dB）
- `evm_nss1`：单空间流EVM值（dB）
- `start_point`：起始点参数
- `win_len`：窗口长度参数
- `numsymbols`：符号数量参数
- `chn_ofst`：通道偏移参数
- `ru_size`：资源单元（RU）大小参数（如 242, 484, 996, 1992等）

## 输出结果

### 1. PDF报告
会在结果路径下生成包含所有图表的PDF文件，图表标题会包含完整的参数信息。

### 2. 控制台输出
脚本会在控制台上打印：
- 正在分析的文件名
- 数据预处理进度
- 分组信息和图表生成进度
- 最终处理结果

## 技术实现细节

### 关键函数

#### `read_and_preprocess_csv(csv_file_path, encoding='utf-8')`
- **参数**：CSV文件路径，编码（默认utf-8）
- **功能**：读取并预处理CSV文件
- **返回**：trk_en=0和trk_en=1的数据Frame

#### `generate_and_save_figs(trk0_df, trk1_df, pdf_save_path)`
- **参数**：
  - `trk0_df`：trk_en=0的DataFrame
  - `trk1_df`：trk_en=1的DataFrame
  - `pdf_save_path`：PDF文件输出路径
- **功能**：生成并保存图表到PDF文件
- **返回**：成功/失败状态

#### `plot_single_evm_metric(ax, data, evm_col, test_rates, custom_params, custom_param_col, color_map, trk_en, style_map)`
- **参数**：
  - `ax`：图表坐标轴对象
  - `data`：要绘制的数据
  - `evm_col`：EVM列名（evm或evm_nss1）
  - `test_rates`：测试速率列表
  - `custom_params`：自定义参数值列表
  - `custom_param_col`：自定义参数列名
  - `color_map`：颜色映射字典
  - `trk_en`：磁跟踪使能值（0/1）
  - `style_map`：样式映射字典
- **功能**：在坐标轴上绘制单个EVM指标的曲线

### 配置参数

```python
CONFIG = {
    # 自定义参数列名
    'CUSTOM_PARAM_COL': 'dc_comp_en',
    # 是否强制要求自定义参数列
    'REQUIRE_CUSTOM_PARAM': False,
    # 基础颜色池
    'BASE_COLORS': [...],
    # EVM相关参数
    'EVM_COLS': ['evm', 'evm_nss1'],
    'REQUIRE_EVM_NSS1': False
}
```

### 分组和标题

**分组参数**：
- `start_point`：起始点
- `win_len`：窗口长度
- `numsymbols`：符号数量
- `chn_ofst`：通道偏移
- `ru_size`：RU（资源单元）大小

**图表标题格式**：
```
{evm_col.upper()}:trk_en=1 vs trk_en=0
start_point={sp} | win_len={wl} | numsymbols={ns} | chn_ofst={co} | ru_size={ru}
```

## 依赖库

```
pandas
matplotlib
numpy
re
os
traceback
gc
```

## 注意事项

1. 确保输入数据的CSV文件格式正确，包含所需的所有列
2. 脚本会自动处理缺失的可选列（如 evm_nss1）
3. 处理大型数据集时可能需要较长时间，脚本已对内存使用进行了优化
4. 确保有足够的磁盘空间存储输出文件
5. 图表会强制覆盖已存在的同名PDF文件

## 版本历史

- 2026-03-17：初始版本，实现EVM对比分析功能
- 优化内存占用，支持五参数分组（添加ru_size参数）
