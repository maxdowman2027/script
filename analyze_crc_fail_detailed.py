import pandas as pd
import os

# 读取Excel文件
file_path = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx_rls4\hesu_heersu_260402\tx_crc_fail_result.xlsx"
df = pd.read_excel(file_path)

print("=== CRC Fail 详细分析报告 ===")
print(f"总记录数: {len(df)}")
print(f"\nWiFi格式分布:")
print(df['wifi_format'].value_counts())

print(f"\n=== Rate 分布 ===")
print(df['rate'].value_counts())

print(f"\n=== TX Power Set 分布 ===")
print(df['tx_power_set(dBm)'].value_counts().sort_index())

print(f"\n=== EVM 统计 ===")
print(f"最小值: {df['evm'].min():.2f}")
print(f"最大值: {df['evm'].max():.2f}")
print(f"平均值: {df['evm'].mean():.2f}")
print(f"标准差: {df['evm'].std():.2f}")

# 创建数据透视表
print("\n=== 按 Rate 和 TX Power Set 分组的 Fail Count ===")
pivot = pd.pivot_table(df, values='wifi_format', index='rate', columns='tx_power_set(dBm)',
                       aggfunc='count', fill_value=0)
print(pivot)

# 保存详细分析结果
output_file = os.path.splitext(file_path)[0] + "_detailed_analysis.xlsx"
with pd.ExcelWriter(output_file) as writer:
    df.to_excel(writer, sheet_name='原始数据', index=False)
    pivot.to_excel(writer, sheet_name='数据透视表')

    # 统计汇总表
    summary = pd.DataFrame({
        '指标': ['总记录数', 'Rate 种类数', 'TX Power Set 种类数',
                'EVM 最小值', 'EVM 最大值', 'EVM 平均值', 'EVM 标准差'],
        '数值': [len(df), df['rate'].nunique(), df['tx_power_set(dBm)'].nunique(),
                df['evm'].min(), df['evm'].max(), df['evm'].mean(), df['evm'].std()]
    })
    summary.to_excel(writer, sheet_name='统计汇总', index=False)

print(f"\n详细分析结果已保存到: {output_file}")
