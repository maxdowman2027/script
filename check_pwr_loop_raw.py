import pandas as pd
import numpy as np

# 读取文件
file1_path = r'D:\users\gxu\spur_scan\260309\scan_spur_data\normal\spur_scan_result_2G_coef.csv'
file2_path = r'D:\users\gxu\spur_scan\260309\scan_spur_data\xtal_duty_disable\spur_scan_result_2G_coef.csv'

df1 = pd.read_csv(file1_path)
df2 = pd.read_csv(file2_path)

# 数据预处理
for col in ['pwr 1', 'pwr 2', 'pwr 3']:
    if col in df1.columns:
        df1[col] = pd.to_numeric(df1[col], errors='coerce')

for col in ['pwr 4', 'pwr 5', 'pwr 6']:
    if col in df2.columns:
        df2[col] = pd.to_numeric(df2[col], errors='coerce')

# 计算循环pwr值的范围和标准差
print('=== normal 模式 ===')
df1['pwr_range'] = df1[['pwr 1', 'pwr 2', 'pwr 3']].max(axis=1) - df1[['pwr 1', 'pwr 2', 'pwr 3']].min(axis=1)
df1['pwr_std'] = df1[['pwr 1', 'pwr 2', 'pwr 3']].std(axis=1)
df1['pwr_count'] = df1[['pwr 1', 'pwr 2', 'pwr 3']].count(axis=1)

print(df1[['phy_mode', 'channel', 'frequency', 'pwr 1', 'pwr 2', 'pwr 3', 'pwr_range', 'pwr_std', 'pwr_count']])

print('\n=== xtal_duty_disable 模式 ===')
df2['pwr_range'] = df2[['pwr 4', 'pwr 5', 'pwr 6']].max(axis=1) - df2[['pwr 4', 'pwr 5', 'pwr 6']].min(axis=1)
df2['pwr_std'] = df2[['pwr 4', 'pwr 5', 'pwr 6']].std(axis=1)
df2['pwr_count'] = df2[['pwr 4', 'pwr 5', 'pwr 6']].count(axis=1)

print(df2[['phy_mode', 'channel', 'frequency', 'pwr 4', 'pwr 5', 'pwr 6', 'pwr_range', 'pwr_std', 'pwr_count']])

print('\n=== normal模式差异大于3dB的配置 ===')
high_var_normal = df1[df1['pwr_range'] > 3]
if len(high_var_normal) > 0:
    print(high_var_normal[['phy_mode', 'channel', 'frequency', 'pwr_range', 'pwr_std']])
else:
    print('无差异大于3dB的配置')

print('\n=== xtal模式差异大于3dB的配置 ===')
high_var_xtal = df2[df2['pwr_range'] > 3]
if len(high_var_xtal) > 0:
    print(high_var_xtal[['phy_mode', 'channel', 'frequency', 'pwr_range', 'pwr_std']])
else:
    print('无差异大于3dB的配置')

print(f'\nnormal模式平均pwr范围: {df1["pwr_range"].mean():.1f}dB')
print(f'xtal模式平均pwr范围: {df2["pwr_range"].mean():.1f}dB')
