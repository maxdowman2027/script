# compare_avg_pwr.py 脚本说明文档

## 脚本概述

compare_avg_pwr.py 是一个用于比较两个 CSV 文件中平均功率（avg pwr）数据的 Python 脚本。它提供了强大的数据比较功能，能够识别两个数据集之间的差异，并通过可视化图表展示这些差异。

## 主要功能

### 1. 数据读取与验证
- **文件读取**：读取两个 CSV 文件的内容
- **列名检查**：验证文件中是否包含所需的列（如 'avg pwr'、'phy_mode'、'channel'、'frequency'）
- **数据类型验证**：检查 'avg pwr' 列的数据类型是否为数值型
- **数据清洗**：过滤掉 'avg pwr' 列中的非数值数据

### 2. 数据合并与比较
- **配置列匹配**：使用 'phy_mode'、'channel'、'frequency' 等列作为配置匹配关键字
- **数据合并**：使用内连接合并两个数据集的相同配置行
- **差异计算**：计算两个数据集之间的平均功率差异（Δ avg pwr）
- **数据筛选**：过滤掉差异大于 2 dBm 的行

### 3. 可视化分析
- **直方图**：展示两个文件中平均功率的分布
- **箱线图**：展示两个文件中平均功率的分布和异常值
- **散点图**：展示两个文件中平均功率的散点图
- **差异图**：展示两个文件之间的平均功率差异

## 使用方法

### 基本使用

```python
# 导入模块
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 读取数据
file_path = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx_rls4\hesu_heersu_260402\merged_tx_result.xlsx"
df = pd.read_excel(file_path)

# 创建图表目录
output_dir = os.path.dirname(file_path)
chart_dir = os.path.join(output_dir, 'charts')
os.makedirs(chart_dir, exist_ok=True)

# 1. EVM分布直方图
plt.figure(figsize=(10, 6))
sns.histplot(df['evm'], kde=True, bins=30)
plt.title('EVM 分布直方图')
plt.xlabel('EVM (dB)')
plt.ylabel('频率')
plt.savefig(os.path.join(chart_dir, 'evm_distribution.png'), dpi=300, bbox_inches='tight')
plt.close()

# 2. Rate vs EVM 箱线图
plt.figure(figsize=(12, 6))
sns.boxplot(x='rate', y='evm', data=df.sort_values('rate'))
plt.title('不同 Rate 下的 EVM 分布')
plt.xlabel('Rate')
plt.ylabel('EVM (dB)')
plt.savefig(os.path.join(chart_dir, 'rate_vs_evm.png'), dpi=300, bbox_inches='tight')
plt.close()

# 3. TX Power Set vs EVM 散点图
plt.figure(figsize=(12, 6))
sns.scatterplot(x='tx_power_set(dBm)', y='evm', data=df, alpha=0.6)
plt.title('TX Power Set 与 EVM 的关系')
plt.xlabel('TX Power Set (dBm)')
plt.ylabel('EVM (dB)')

# 添加趋势线
z = df['tx_power_set(dBm)'].values
w = df['evm'].values
p = np.polyfit(z, w, 1)
plt.plot(z, np.polyval(p, z), "r--", label=f"趋势线: EVM = {p[0]:.2f} * Power + {p[1]:.2f}")
plt.legend()
```

### 高级使用

```python
# 导入模块
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 读取数据
file_path = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx_rls4\hesu_heersu_260402\merged_tx_result.xlsx"
df = pd.read_excel(file_path)

# 创建图表目录
output_dir = os.path.dirname(file_path)
chart_dir = os.path.join(output_dir, 'charts')
os.makedirs(chart_dir, exist_ok=True)

# 1. EVM分布直方图
plt.figure(figsize=(10, 6))
sns.histplot(df['evm'], kde=True, bins=30)
plt.title('EVM 分布直方图')
plt.xlabel('EVM (dB)')
plt.ylabel('频率')
plt.savefig(os.path.join(chart_dir, 'evm_distribution.png'), dpi=300, bbox_inches='tight')
plt.close()

# 2. Rate vs EVM 箱线图
plt.figure(figsize=(12, 6))
sns.boxplot(x='rate', y='evm', data=df.sort_values('rate'))
plt.title('不同 Rate 下的 EVM 分布')
plt.xlabel('Rate')
plt.ylabel('EVM (dB)')
plt.savefig(os.path.join(chart_dir, 'rate_vs_evm.png'), dpi=300, bbox_inches='tight')
plt.close()

# 3. TX Power Set vs EVM 散点图
plt.figure(figsize=(12, 6))
sns.scatterplot(x='tx_power_set(dBm)', y='evm', data=df, alpha=0.6)
plt.title('TX Power Set 与 EVM 的关系')
plt.xlabel('TX Power Set (dBm)')
plt.ylabel('EVM (dB)')

# 添加趋势线
z = df['tx_power_set(dBm)'].values
w = df['evm'].values
p = np.polyfit(z, w, 1)
plt.plot(z, np.polyval(p, z), "r--", label=f"趋势线: EVM = {p[0]:.2f} * Power + {p[1]:.2f}")
plt.legend()
```

## 输入文件要求

### 文件格式
- **CSV 文件**：必须是逗号分隔的文本文件
- **编码**：建议使用 UTF-8 编码
- **列名**：文件必须包含以下列：
  - 'phy_mode'：物理模式（如 'he', 'erp', '11b' 等）
  - 'channel'：信道号
  - 'frequency'：频率（MHz）
  - 'avg pwr'：平均功率（dBm）

### 文件命名
- 文件命名无特殊要求，但建议使用有意义的文件名
- 文件名应避免包含特殊字符

## 输出结果

### 1. 控制台输出
- 文件列名信息
- 合并后的数据形状
- 平均功率差异大于 2 dBm 的行数

### 2. 可视化图表
生成的图表保存到 'charts' 目录中：
- 'evm_distribution.png'：EVM 分布直方图
- 'rate_vs_evm.png'：不同 Rate 下的 EVM 分布箱线图
- 'tx_power_set_vs_evm.png'：TX Power Set 与 EVM 的关系散点图

## 使用场景

### 1. 测试数据比较
- **场景**：比较两个测试版本的平均功率数据
- **应用**：识别测试版本之间的功率差异
- **优势**：通过可视化图表直观展示差异

### 2. 数据分析
- **场景**：分析平均功率与其他参数之间的关系
- **应用**：识别功率变化的模式和趋势
- **优势**：提供多种可视化图表，便于分析

### 3. 报告生成
- **场景**：生成包含平均功率比较结果的报告
- **应用**：为测试团队提供详细的分析结果
- **优势**：自动化图表生成，节省时间

## 技术说明

### 依赖库
- **pandas**：数据处理
- **matplotlib**：图表绘制
- **seaborn**：统计可视化
- **numpy**：数值计算
- **os**：操作系统相关操作

### 执行流程
1. 读取两个 CSV 文件的内容
2. 验证文件中是否包含所需的列
3. 清洗数据，过滤掉非数值型数据
4. 合并两个数据集的相同配置行
5. 计算平均功率差异（Δ avg pwr）
6. 生成可视化图表
7. 保存图表到 'charts' 目录

## 注意事项

### 1. 文件路径
- 使用原始字符串（r 前缀）避免转义字符问题
- 确保路径使用正确的分隔符（Windows 系统使用 `\`，其他系统使用 `/`）

### 2. 数据验证
- 脚本会验证文件中是否包含所需的列
- 脚本会过滤掉 'avg pwr' 列中的非数值数据
- 如果缺少所需的列，脚本会抛出异常

### 3. 图表保存
- 图表会保存到输入文件所在目录的 'charts' 子目录中
- 如果 'charts' 目录不存在，脚本会自动创建

### 4. 性能考虑
- 对于大型文件，脚本可能需要较长时间运行
- 建议将文件大小限制在合理范围内（如不超过 100MB）

## 故障排除

### 常见问题

1. **文件找不到**
   - 检查文件路径是否正确
   - 确保文件路径使用正确的分隔符

2. **列名不匹配**
   - 检查文件中是否包含所需的列
   - 确保列名的大小写一致

3. **数据类型错误**
   - 检查 'avg pwr' 列的数据类型是否为数值型
   - 过滤掉非数值型数据

4. **图表生成失败**
   - 检查 'charts' 目录的权限
   - 确保磁盘空间充足

## 总结

compare_avg_pwr.py 是一个功能强大且易用的数据比较工具，提供了丰富的可视化功能，能够帮助测试团队快速识别两个数据集之间的差异。通过合理使用脚本，用户可以节省大量手动操作时间，提高数据分析效率。