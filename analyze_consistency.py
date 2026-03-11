
import pandas as pd
import numpy as np

df = pd.read_excel(r'D:/users/gxu/spur_scan/260310/scan_spur_data/xtal_duty_disable/spur_scan_result_2G_coef_异常检测.xlsx')

# 只选择包含数值的行
def has_numeric_values(row):
    try:
        float(row['pwr 4'])
        float(row['pwr 5'])
        float(row['pwr 6'])
        return True
    except:
        return False

numeric_rows = df[df.apply(has_numeric_values, axis=1)]

# 计算三次循环的统计量
numeric_rows['pwr 4'] = numeric_rows['pwr 4'].astype(float)
numeric_rows['pwr 5'] = numeric_rows['pwr 5'].astype(float)
numeric_rows['pwr 6'] = numeric_rows['pwr 6'].astype(float)

numeric_rows['pwr_range'] = numeric_rows[['pwr 4', 'pwr 5', 'pwr 6']].max(axis=1) - numeric_rows[['pwr 4', 'pwr 5', 'pwr 6']].min(axis=1)
numeric_rows['pwr_std'] = numeric_rows[['pwr 4', 'pwr 5', 'pwr 6']].std(axis=1)
numeric_rows['pwr_mean'] = numeric_rows[['pwr 4', 'pwr 5', 'pwr 6']].mean(axis=1)
numeric_rows['max_deviation'] = numeric_rows.apply(lambda row: max(abs(row['pwr 4'] - row['pwr_mean']),
                                                                   abs(row['pwr 5'] - row['pwr_mean']),
                                                                   abs(row['pwr 6'] - row['pwr_mean'])), axis=1)

print('数据一致性统计:')
print(f'行数: {len(numeric_rows)}')
print(f'最大偏差范围: {numeric_rows["pwr_range"].max():.3f} dB')
print(f'平均偏差范围: {numeric_rows["pwr_range"].mean():.3f} dB')
print(f'最大标准差: {numeric_rows["pwr_std"].max():.3f}')
print(f'平均标准差: {numeric_rows["pwr_std"].mean():.3f}')
print(f'最大绝对偏差: {numeric_rows["max_deviation"].max():.3f} dB')
print(f'平均绝对偏差: {numeric_rows["max_deviation"].mean():.3f} dB')

print('\n偏差最大的前5行:')
print(numeric_rows.sort_values('max_deviation', ascending=False)[['phy_mode', 'channel', 'pwr 4', 'pwr 5', 'pwr 6', 'pwr_range', 'pwr_std', 'pwr_mean', 'max_deviation']].head())
