import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

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

plt.savefig(os.path.join(chart_dir, 'tx_power_vs_evm.png'), dpi=300, bbox_inches='tight')
plt.close()

# 4. EVM随Rate和TX Power Set的热图
plt.figure(figsize=(12, 8))
pivot = df.pivot_table(values='evm', index='rate', columns='tx_power_set(dBm)', aggfunc='mean')
sns.heatmap(pivot, annot=True, cmap='coolwarm', fmt='.1f')
plt.title('EVM 随 Rate 和 TX Power Set 的变化热图')
plt.xlabel('TX Power Set (dBm)')
plt.ylabel('Rate')
plt.savefig(os.path.join(chart_dir, 'evm_heatmap.png'), dpi=300, bbox_inches='tight')
plt.close()

# 5. WiFi Format 分布
plt.figure(figsize=(10, 6))
df['wifi_format'].value_counts().plot.pie(autopct='%1.1f%%', startangle=90)
plt.title('WiFi Format 分布')
plt.ylabel('')
plt.savefig(os.path.join(chart_dir, 'wifi_format_distribution.png'), dpi=300, bbox_inches='tight')
plt.close()

# 6. FEC Coding 分布
plt.figure(figsize=(10, 6))
df['fec_coding'].value_counts().plot.pie(autopct='%1.1f%%', startangle=90)
plt.title('FEC Coding 分布')
plt.ylabel('')
plt.savefig(os.path.join(chart_dir, 'fec_coding_distribution.png'), dpi=300, bbox_inches='tight')
plt.close()

# 保存所有图表到Excel文件
output_file = os.path.join(output_dir, 'merged_tx_result_visual_report.xlsx')
with pd.ExcelWriter(output_file) as writer:
    # 写入原始数据
    df.to_excel(writer, sheet_name='原始数据', index=False)

    # 写入统计摘要
    summary = pd.DataFrame({
        '指标': ['总记录数', 'Rate种类数', 'TX Power Set种类数',
                'WiFi Format种类数', 'FEC Coding种类数',
                'EVM最小值', 'EVM最大值', 'EVM平均值', 'EVM标准差'],
        '数值': [
            len(df),
            df['rate'].nunique(),
            df['tx_power_set(dBm)'].nunique(),
            df['wifi_format'].nunique(),
            df['fec_coding'].nunique(),
            df['evm'].min(),
            df['evm'].max(),
            df['evm'].mean(),
            df['evm'].std()
        ]
    })
    summary.to_excel(writer, sheet_name='统计摘要', index=False)

    # 写入Rate分布
    df['rate'].value_counts().sort_index().to_excel(writer, sheet_name='Rate分布')

    # 写入TX Power Set分布
    df['tx_power_set(dBm)'].value_counts().sort_index().to_excel(writer, sheet_name='TX Power Set分布')

    # 写入按Rate分组的EVM统计
    rate_evm = df.groupby('rate')['evm'].describe()
    rate_evm.to_excel(writer, sheet_name='Rate-EVM统计')

    # 写入按TX Power Set分组的EVM统计
    power_evm = df.groupby('tx_power_set(dBm)')['evm'].describe()
    power_evm.to_excel(writer, sheet_name='TX Power-EVM统计')

print(f"可视化报告已生成")
print(f"Excel报告保存到: {output_file}")
print(f"图表保存到: {chart_dir}")
