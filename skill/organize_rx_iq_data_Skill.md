# organize_rx_iq_data.py 脚本说明文档

## 脚本概述

`organize_rx_iq_data.py` 是一个用于整理和分类 RX IQ 测试数据的 Python 脚本。它可以根据测试数据文件中的带宽（bw）、频率（freqMhz）和通道（channel）信息，将文件重新命名并移动到对应的目录中，以便更好地组织和管理测试数据。

## 主要功能

1. **文件重命名**：根据测试数据文件中的信息，将原始文件名重新命名为包含频段、带宽和通道信息的格式。
2. **目录分类**：将文件移动到对应的目录中，目录结构为：`目的路径/通道/频段/`。
3. **频段划分**：
   - 2G：频率小于 3000 MHz
   - 5G：频率大于等于 3000 MHz 且小于 5935 MHz
   - 6G：频率大于等于 5935 MHz
4. **通道识别**：
   - 识别包含 ch0 和 ch1 两种配置的文件（mimo 类型）
   - 识别仅包含 ch0 或 ch1 配置的文件（single 类型）

## 脚本使用方法

### 配置区域

在脚本的开始部分有一个配置区域，可以根据需要修改：

```python
# ================= 配置区域 =================
# 在这里修改配置
SOURCE_PATH = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\rx_iq_cal_pwr\FPGA752_FPGA761_20260419"  # 源路径
DESTINATION_PATH = r"D:\users\gxu\rx_iq\E22\regression_v3_260418"  # 目的路径
# ===========================================
```

### 运行脚本

直接运行脚本即可：

```bash
python organize_rx_iq_data.py
```

## 依赖库

脚本依赖于 Python 的标准库，不需要安装额外的依赖库。主要使用了以下模块：

1. `os`：用于处理文件和目录操作
2. `csv`：用于读取和解析 CSV 文件
3. `shutil`：用于复制文件
4. `re`：用于处理正则表达式（未在当前版本中使用，但预留了扩展功能）

## 目录结构

处理后的文件将按照以下目录结构进行组织：

```
目的路径/
├── ch0/
│   ├── 2G/
│   ├── 5G/
│   ├── 6G/
│   └── 160m 文件直接放在此目录下
├── ch1/
│   ├── 2G/
│   ├── 5G/
│   ├── 6G/
│   └── 160m 文件直接放在此目录下
└── mimo/
    ├── 2G/
    ├── 5G/
    ├── 6G/
    └── 160m 文件直接放在此目录下
```

## 文件命名格式

处理后的文件名格式为：

- **非 160m 带宽文件**：
  ```
  rx_iq_cal_res_<频段>_<带宽>_<通道>_<日期>_<时间>.csv
  ```
  例如：
  - `rx_iq_cal_res_2G_20m_ch0_20260418_153333.csv`
  - `rx_iq_cal_res_5G_40m_ch1_20260418_164444.csv`
  - `rx_iq_cal_res_6G_80m_mimo_20260418_175555.csv`

- **160m 带宽文件**：
  ```
  rx_iq_cal_res_<带宽>_<通道>_<日期>_<时间>.csv
  ```
  例如：
  - `rx_iq_cal_res_160m_ch0_20260418_153333.csv`
  - `rx_iq_cal_res_160m_ch1_20260418_164444.csv`
  - `rx_iq_cal_res_160m_mimo_20260418_175555.csv`

## 技术实现

### 频段划分函数

```python
def get_band(freq):
    """
    根据频率确定频段（2G/5G/6G）

    Args:
        freq: 频率值（MHz）

    Returns:
        频段字符串（2G 或 5G 或 6G）
    """
    if freq < 3000:
        return "2G"
    elif freq < 5935:
        return "5G"
    else:
        return "6G"
```

### 带宽字符串转换函数

```python
def get_bandwidth_str(bw):
    """
    根据带宽确定带宽字符串（20m/40m/80m/160m）

    Args:
        bw: 带宽值（MHz）

    Returns:
        带宽字符串（20m/40m/80m/160m）
    """
    return f"{bw}m"
```

### 通道识别函数

```python
def get_channel_str(has_ch0, has_ch1):
    """
    根据是否包含 ch0 和 ch1 配置确定通道字符串（ch0/ch1/mimo）

    Args:
        has_ch0: 是否包含 ch0 配置
        has_ch1: 是否包含 ch1 配置

    Returns:
        通道字符串（ch0/ch1/mimo）
    """
    if has_ch0 and has_ch1:
        return "mimo"
    elif has_ch0:
        return "ch0"
    elif has_ch1:
        return "ch1"
    else:
        return "unknown"
```

## 使用示例

### 源路径文件

原始源路径下的文件格式为：
`rx_iq_cal_res_FPGA752_FPGA761_20260418_153333.csv`

### 处理过程

脚本将读取该文件的内容，获取其带宽、频率和通道信息，然后将文件重新命名为：
`rx_iq_cal_res_5G_80m_ch0_20260418_153333.csv`

并将其移动到：
`D:\users\gxu\rx_iq\E22\regression_v3_260418\ch0\5G\`

## 注意事项

1. 脚本在处理过程中会保留源文件的副本，不会删除源文件。
2. 脚本会自动创建目的路径下的目录结构。
3. 如果目的路径下已经存在同名文件，脚本会覆盖已存在的文件。

## 未来改进

1. 可以添加对更多带宽类型的支持，如 160m、320m 等。
2. 可以添加对更多频段的支持。
3. 可以优化文件识别和分类算法，提高处理效率。
4. 可以添加对不同芯片型号的支持。