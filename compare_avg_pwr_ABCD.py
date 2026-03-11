
import pandas as pd
import numpy as np

# 读取两个CSV文件
file1_path = r'D:/users/gxu/spur_scan/260310/scan_spur_data/xtal_duty_disable/spur_scan_result_2G_coef.csv'
file2_path = r'D:/users/gxu/spur_scan/260309/scan_spur_data/xtal_duty_disable/spur_scan_result_2G_coef.csv'

df1 = pd.read_csv(file1_path)
df2 = pd.read_csv(file2_path)

# 检查列名是否一致
print('文件1的列名:', list(df1.columns))
print('文件2的列名:', list(df2.columns))

# 检查是否有avg_pwr列（J列）
if 'avg pwr' not in df1.columns or 'avg pwr' not in df2.columns:
    raise ValueError("其中一个文件没有'J列 avg pwr'")

# 检查是否有足够的配置列（A:phy_mode, B:channel, C:frequency, D:Used_Frequency）
required_config_cols = ['phy_mode', 'channel', 'frequency', 'Used_Frequency']
for col in required_config_cols:
    if col not in df1.columns or col not in df2.columns:
        raise ValueError(f"其中一个文件没有配置列'{col}'")

# 选择需要的列
cols_to_compare = required_config_cols + ['avg pwr']
df1_compare = df1[cols_to_compare].copy()
df2_compare = df2[cols_to_compare].copy()

# 处理非数值数据
def is_numeric(x):
    try:
        float(x)
        return True
    except:
        return False

df1_compare = df1_compare[df1_compare['avg pwr'].apply(is_numeric)]
df2_compare = df2_compare[df2_compare['avg pwr'].apply(is_numeric)]

df1_compare['avg pwr'] = df1_compare['avg pwr'].astype(float)
df2_compare['avg pwr'] = df2_compare['avg pwr'].astype(float)

# 使用配置列进行合并
merged_df = pd.merge(df1_compare, df2_compare,
                     on=required_config_cols,
                     how='inner',
                     suffixes=('_260310', '_260309'))

# 计算差异
merged_df['power_diff'] = merged_df['avg pwr_260310'] - merged_df['avg pwr_260309']
merged_df['abs_diff'] = merged_df['power_diff'].abs()

# 保存为CSV格式
output_file = r'D:/users/gxu/spur_scan/260310/scan_spur_data/xtal_duty_disable/avg_pwr_comparison_ABCD.csv'
merged_df.to_csv(output_file, index=False, encoding='utf-8-sig')

# 统计差异大于0.5 dB的行数
large_diff_count = len(merged_df[merged_df['abs_diff'] > 0.5])

print('比较完成！')
print(f'总匹配行数: {len(merged_df)}')
print(f'差异大于0.5 dB的行数: {large_diff_count}')
print(f'结果已保存至: {output_file}')
