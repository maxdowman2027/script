import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 读取分析结果
output_file = r'D:\users\gxu\spur_scan\260309\scan_spur_data\spur_comparison_analysis.xlsx'
merged_df = pd.read_excel(output_file, sheet_name='完整数据')
abnormal_df = pd.read_excel(output_file, sheet_name='异常数据')

# 创建可视化图表
fig, axes = plt.subplots(2, 2, figsize=(18, 14))
fig.suptitle('2.4G频段Spur扫描结果比较分析', fontsize=16, fontweight='bold')

# 1. 平均功率差异分布图
ax1 = axes[0, 0]
valid_diff = merged_df['avg_pwr_diff'].dropna()
n, bins, patches = ax1.hist(valid_diff, bins=20, color='blue', alpha=0.7, edgecolor='black')
# 为异常值着色
threshold = 5
for i in range(len(bins)-1):
    if bins[i] < -threshold or bins[i] > threshold:
        patches[i].set_facecolor('red')
ax1.axvline(x=-threshold, color='red', linestyle='--', label=f'-{threshold}dB阈值')
ax1.axvline(x=threshold, color='red', linestyle='--', label=f'{threshold}dB阈值')
ax1.set_xlabel('平均功率差异 (dB)')
ax1.set_ylabel('配置数量')
ax1.set_title('平均功率差异分布')
ax1.grid(True, alpha=0.3)
ax1.legend()
ax1.set_ylim(0, 10)

# 2. 所有配置的差异散点图
ax2 = axes[0, 1]
# 过滤有效数据
valid_data = merged_df.dropna(subset=['avg_pwr_diff', 'channel'])
valid_data = valid_data[valid_data['channel'].notna()]  # 确保channel列有效
# 非异常值
normal_points = valid_data[np.abs(valid_data['avg_pwr_diff']) <= threshold]
ax2.scatter(normal_points['channel'], normal_points['avg_pwr_diff'], color='blue', label='正常数据', s=60, alpha=0.7)
# 异常值
abnormal_points = valid_data[np.abs(valid_data['avg_pwr_diff']) > threshold]
ax2.scatter(abnormal_points['channel'], abnormal_points['avg_pwr_diff'], color='red', label='异常数据', s=80, alpha=0.9, edgecolors='black')
ax2.axhline(y=-threshold, color='red', linestyle='--', linewidth=1)
ax2.axhline(y=threshold, color='red', linestyle='--', linewidth=1)
ax2.set_xlabel('Channel (信道)')
ax2.set_ylabel('平均功率差异 (dB)')
ax2.set_title('不同信道的差异分析')
ax2.grid(True, alpha=0.3)
ax2.legend()
ax2.set_ylim(-10, 10)
ax2.set_xlim(valid_data['channel'].min()-1, valid_data['channel'].max()+1)

# 3. 按phy_mode分组的差异对比
ax3 = axes[1, 0]
phy_mode_groups = merged_df.groupby('phy_mode')['avg_pwr_diff'].apply(list)
for i, (phy_mode, diff_list) in enumerate(phy_mode_groups.items()):
    if np.isnan(phy_mode):
        continue
    diff_list = [x for x in diff_list if not np.isnan(x)]
    positions = np.full(len(diff_list), i) + np.random.normal(0, 0.05, len(diff_list))
    colors = ['red' if abs(x) > threshold else 'blue' for x in diff_list]
    ax3.scatter(positions, diff_list, color=colors, label=f'phy_mode={int(phy_mode)}', s=50)
ax3.axhline(y=-threshold, color='red', linestyle='--', linewidth=1)
ax3.axhline(y=threshold, color='red', linestyle='--', linewidth=1)
ax3.set_xlabel('PHY模式')
ax3.set_ylabel('平均功率差异 (dB)')
ax3.set_title('按PHY模式分组的差异对比')
ax3.grid(True, alpha=0.3)
ax3.set_xticks([0, 1])
ax3.set_xticklabels(['PHY 0', 'PHY 1'])
ax3.legend()
ax3.set_ylim(-10, 10)

# 4. 差异分布统计
ax4 = axes[1, 1]
# 计算统计信息
stats = []
total_configs = len(merged_df)
valid_configs = len(merged_df.dropna(subset=['avg pwr_normal', 'avg pwr_xtal']))
abnormal_configs = len(abnormal_df)
only_normal = len(merged_df[merged_df['avg pwr_normal'].notna() & merged_df['avg pwr_xtal'].isna()])
only_xtal = len(merged_df[merged_df['avg pwr_normal'].isna() & merged_df['avg pwr_xtal'].notna()])

categories = ['有效配置', '异常配置', '仅normal', '仅xtal']
values = [valid_configs, abnormal_configs, only_normal, only_xtal]
colors = ['blue', 'red', 'orange', 'green']

ax4.pie(values, labels=categories, colors=colors, autopct='%1.1f%%', startangle=90)
ax4.set_title('配置分布统计')

# 调整布局
plt.tight_layout()
plt.subplots_adjust(top=0.92)

# 保存图表
output_chart = r'D:\users\gxu\spur_scan\260309\scan_spur_data\spur_comparison_charts.png'
plt.savefig(output_chart, dpi=300, bbox_inches='tight')
plt.show()

print(f"图表已保存到: {output_chart}")

# 显示详细统计
print("\n=== 详细分布统计 ===")
print(f"有效配置数: {valid_configs} ({valid_configs/total_configs:.1%})")
print(f"异常配置数: {abnormal_configs} ({abnormal_configs/valid_configs:.1%} of 有效配置)")
print(f"仅normal配置数: {only_normal} ({only_normal/total_configs:.1%})")
print(f"仅xtal配置数: {only_xtal} ({only_xtal/total_configs:.1%})")

print("\n=== 按PHY模式统计 ===")
for i, (phy_mode, diff_list) in enumerate(phy_mode_groups.items()):
    if np.isnan(phy_mode):
        continue
    diff_list = [x for x in diff_list if not np.isnan(x)]
    abnormal_count = sum(1 for x in diff_list if abs(x) > threshold)
    print(f"\nphy_mode={int(phy_mode)}:")
    print(f"  配置数: {len(diff_list)}")
    print(f"  异常数: {abnormal_count} ({abnormal_count/len(diff_list):.1%})")
    if len(diff_list) > 0:
        print(f"  平均差异: {np.mean(diff_list):.2f}dB")
        print(f"  最大差异: {max(diff_list):.2f}dB")
        print(f"  最小差异: {min(diff_list):.2f}dB")
