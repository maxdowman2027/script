import pandas as pd
import os

# 读取Excel文件
file_path = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx_rls4\hesu_heersu_260402\merged_tx_result.xlsx"
df = pd.read_excel(file_path)

# 显示数据的基本信息
print("=== 数据基本信息 ===")
print(df.info())
print("\n=== 数据前5行 ===")
print(df.head())

# 检查是否包含需要的列
required_columns = ['rate', 'tx_power_set(dBm)', 'evm']
for col in required_columns:
    if col not in df.columns:
        print(f"警告: 数据中缺少列 '{col}'")
        print(f"实际包含的列: {list(df.columns)}")

# 统计整体测试情况
print("\n=== 整体测试情况统计 ===")
print(f"总记录数: {len(df)}")
print(f"唯一Rate数量: {df['rate'].nunique()}")
print(f"唯一TX Power Set数量: {df['tx_power_set(dBm)'].nunique()}")

# Rate 分布
print("\n=== Rate 分布 ===")
rate_counts = df['rate'].value_counts().sort_index()
print(rate_counts)

# TX Power Set 分布
print("\n=== TX Power Set 分布 ===")
power_counts = df['tx_power_set(dBm)'].value_counts().sort_index()
print(power_counts)

# EVM 统计
print("\n=== EVM 统计 ===")
print(f"最小值: {df['evm'].min():.2f}")
print(f"最大值: {df['evm'].max():.2f}")
print(f"平均值: {df['evm'].mean():.2f}")
print(f"标准差: {df['evm'].std():.2f}")

# 按 Rate 分组的 EVM 统计
print("\n=== 按 Rate 分组的 EVM 统计 ===")
rate_evm = df.groupby('rate')['evm'].describe()
print(rate_evm)

# 按 TX Power Set 分组的 EVM 统计
print("\n=== 按 TX Power Set 分组的 EVM 统计 ===")
power_evm = df.groupby('tx_power_set(dBm)')['evm'].describe()
print(power_evm)

# 保存分析结果
output_file = os.path.splitext(file_path)[0] + "_analysis.xlsx"
with pd.ExcelWriter(output_file) as writer:
    df.to_excel(writer, sheet_name='原始数据', index=False)

    # 统计汇总表
    summary = pd.DataFrame({
        '指标': ['总记录数', 'Rate 种类数', 'TX Power Set 种类数',
                'EVM 最小值', 'EVM 最大值', 'EVM 平均值', 'EVM 标准差'],
        '数值': [len(df), df['rate'].nunique(), df['tx_power_set(dBm)'].nunique(),
                df['evm'].min(), df['evm'].max(), df['evm'].mean(), df['evm'].std()]
    })
    summary.to_excel(writer, sheet_name='统计汇总', index=False)

    # Rate 分布
    rate_counts.to_excel(writer, sheet_name='Rate 分布')

    # TX Power Set 分布
    power_counts.to_excel(writer, sheet_name='TX Power Set 分布')

    # 按 Rate 分组的 EVM 统计
    rate_evm.to_excel(writer, sheet_name='Rate-EVM 统计')

    # 按 TX Power Set 分组的 EVM 统计
    power_evm.to_excel(writer, sheet_name='TX Power-EVM 统计')

print(f"\n分析结果已保存到: {output_file}")
