# tx_adcdump_data_parse.py 脚本说明文档

## 1. 脚本概述

`tx_adcdump_data_parse.py` 是一个用于解析 ADC 采样数据的 Python 脚本，专门用于将 CSV 文件中 `#dump_data` 列的十六进制数据按照指定的 bit 字段转换为有符号数。它提供了一个直观的配置接口，用户可以直接在代码中修改参数，无需使用命令行参数。

## 2. 功能特性

- 将 CSV 文件中的指定 bit 字段转换为有符号数
- 支持自定义输入和输出文件路径
- 允许用户指定要转换的 bit 字段范围和新列名
- 使用二进制补码转换方法
- 自动处理输出文件命名
- 包含错误处理和警告信息
- 输出格式保持原 CSV 文件结构

## 3. 使用方法

### 3.1 基本使用

直接运行脚本即可处理默认配置的文件：

```bash
python D:\users\gxu\scripts\tx_adcdump_data_parse.py
```

### 3.2 自定义配置

在脚本的配置区域中修改以下变量：

#### 3.2.1 修改输入文件路径

```python
# ==================== 配置区域 ====================

# 输入文件路径（请修改为您要处理的文件路径）
input_file = r"您的文件路径"
```

#### 3.2.2 修改输出文件路径

```python
# 输出文件路径（可选，留空则自动生成）
output_file = r"您的输出文件路径"
```

如果留空，脚本会自动在输入文件名后添加 `_converted` 后缀作为输出文件名。

#### 3.2.3 修改要转换的字段

```python
# 要转换的字段列表，格式为 [high:low]
bit_fields = [
    "[11:0]",
    "[23:12]",
    "[32:24]",
    "[44:36]"  # 新增字段
]
```

#### 3.2.4 修改新列名

```python
# 新列名列表（可选，留空则自动生成）
column_names = [
    "hccfr_th_signed",
    "iccfr_th_signed",
    "dig_gain1_signed",
    "dig_gain2_signed"  # 新增列名
]
```

## 4. 配置示例

### 4.1 示例 1：处理默认文件

```python
input_file = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\dump_node_124\FPGA752_0x1097bdf7e5a8_20260416\dump_tx_vector_FPGA752_0x1097bdf7e5a8_20260416_152710.csv"
output_file = ""
bit_fields = [
    "[11:0]",
    "[23:12]",
    "[32:24]"
]
column_names = [
    "hccfr_th_signed",
    "iccfr_th_signed",
    "dig_gain1_signed"
]
```

### 4.2 示例 2：处理其他文件

```python
input_file = r"D:\data\test_data.csv"
output_file = r"D:\data\test_data_signed.csv"
bit_fields = [
    "[7:0]",
    "[15:8]"
]
column_names = [
    "value1_signed",
    "value2_signed"
]
```

## 5. 工作原理

脚本使用以下步骤处理数据：

1. 读取输入 CSV 文件
2. 解析配置的字段范围
3. 对每个字段进行位提取和有符号数转换
4. 将转换后的结果添加到新列
5. 保存到输出 CSV 文件

### 5.1 二进制补码转换

脚本使用以下函数实现有符号数转换：

```python
def twos_complement(value, bits):
    """
    将无符号整数转换为二进制补码表示的有符号整数
    """
    if value & (1 << (bits - 1)):
        value -= (1 << bits)
    return value
```

## 6. 错误处理

脚本包含完善的错误处理机制：

- 字段不存在时会发出警告
- 无法解析值时会发出警告
- 列名数量与字段数量不匹配时会抛出异常
- 字段格式不正确时会发出警告

## 7. 输出格式

输出文件保留原 CSV 文件的所有字段，并在末尾添加转换后的有符号数列。新列的命名方式可以是：

- 默认：字段名后添加 `_signed` 后缀
- 自定义：使用用户指定的列名

## 8. 依赖库

脚本只使用 Python 标准库，无需安装额外的依赖：

- `csv`：用于 CSV 文件的读取和写入
- `os`：用于文件路径处理

## 9. 技术规范

- 脚本编码：UTF-8
- 文件格式：Python 3.x
- 输出格式：CSV 文件
- 支持的 Python 版本：Python 3.6 及以上

## 10. 维护说明

### 10.1 修改配置

如果需要处理不同的文件或字段，只需修改配置区域的变量即可。

### 10.2 添加新功能

如果需要添加新功能，可以修改以下函数：

- `convert_csv_file()`：处理 CSV 文件的核心逻辑
- `twos_complement()`：二进制补码转换函数

### 10.3 问题排查

如果脚本运行出现问题，可以：

1. 检查输入文件路径是否正确
2. 检查字段格式是否正确（应为 [high:low] 格式）
3. 检查字段是否在输入文件中存在

## 11. 版本历史

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| 1.0 | 2026-04-16 | 初始版本，支持基本的 bit 字段转换为有符号数功能 |

---

**注意**：在使用脚本时，建议先备份输入文件，以防止数据丢失或损坏。