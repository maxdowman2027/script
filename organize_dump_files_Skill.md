# organize_dump_files.py 脚本说明

## 功能概述

该脚本用于将源路径下的文件按照文件名的配置格式复制到目的路径下的对应层级目录中。主要功能包括：

1. 解析文件名格式 `dump_phymdxx_chanxxx_xxxx`，提取 phymd 和 chan 信息
2. 根据 phymd 值确定带宽（20m/40m/80m/160m）
3. 根据 chan 值确定频段（2G/5G/6G，其中大于等于 5985 的视为 6G）
4. 按照目的路径格式组织文件：
   - phymd160 的文件与 2G、5G、6G 等文件夹同一层级，创建 160m 文件夹放入
   - 其余带宽的文件按照 2G/5G/6G -> 20m/40m/80m 层级放入

## 配置区域

脚本顶部有以下可配置参数：

```python
SOURCE_PATH = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\dump_iqcomb_0x240\FPGA752_FPGA761_20260417"  # 源路径
DESTINATION_PATH = r"D:\users\gxu\rx_iq\E22\regression_v3_260418\ch0"  # 目的路径
```

## 使用方法

### 1. 修改配置

根据需要修改配置区域中的参数：

- `SOURCE_PATH`：指定要处理的源路径
- `DESTINATION_PATH`：指定要复制到的目的路径

### 2. 运行脚本

直接运行脚本：

```bash
python organize_dump_files.py
```

## 输出目录结构

处理后的文件将按照以下目录结构组织：

```
目的路径/
├── 2G/
│   ├── 20m/
│   ├── 40m/
│   └── 80m/
├── 5G/
│   ├── 20m/
│   ├── 40m/
│   └── 80m/
├── 6G/
│   ├── 20m/
│   ├── 40m/
│   └── 80m/
└── 160m/
```

## 技术实现

### 使用的库

- `os`：用于文件路径处理和目录创建
- `shutil`：用于文件复制
- `re`：用于正则表达式解析文件名

### 核心功能

1. **文件名解析**：使用正则表达式匹配文件名格式 `dump_phymdxx_chanxxx_xxxx`，提取 phymd 和 chan 信息
2. **带宽确定**：根据 phymd 值确定带宽（20m/40m/80m/160m）
3. **频段确定**：根据 chan 值确定频段（2G/5G/6G，其中大于等于 5985 的视为 6G）
4. **目录创建**：根据解析结果创建对应的目录结构
5. **文件复制**：使用 shutil 库复制文件到目标路径

## 注意事项

- 脚本只会处理文件名以 `dump_phymd` 开头且以 `.csv` 结尾的文件
- 如果文件名格式不符合要求，会显示警告信息并跳过该文件
- 脚本会自动创建不存在的目录
- 原文件会被保留在源路径中，不会被删除

## 示例

### 源路径文件

原始源路径下的文件格式为：
`dump_phymd20_chan2400_20260417_153333.csv`

### 处理过程

脚本将解析该文件名，获取：
- phymd：20（带宽为 20m）
- chan：2400（频段为 2G）

然后将文件复制到：
`D:\users\gxu\rx_iq\E22\regression_v3_260418\ch0\2G\20m\dump_phymd20_chan2400_20260417_153333.csv`