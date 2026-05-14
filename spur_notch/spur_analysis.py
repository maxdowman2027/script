import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import warnings
warnings.filterwarnings('ignore')

# 读取两个 CSV 文件
file1_path = r'D:\users\gxu\spur_scan\260309\scan_spur_data\normal\spur_scan_result_2G_coef.csv'
file2_path = r'D:\users\gxu\spur_scan\260309\scan_spur_data\xtal_duty_disable\spur_scan_result_2G_coef.csv'

df1 = pd.read_csv(file1_path)
df2 = pd.read_csv(file2_path)

print("=== 文件读取成功 ===")
print(f"normal 模式数据行数: {len(df1)}")
print(f"xtal_duty_disable 模式数据行数: {len(df2)}")

# 数据预处理
# 将'no_spur'和'invalid'等非数值类型替换为NaN
for col in ['phy_mode', 'channel', 'frequency', 'Used_Frequency', 'X_CoefFixed', 'Y_CoefFixed']:
    if col in df1.columns:
        df1[col] = df1[col].replace(['no_spur', 'invalid'], np.nan)
    if col in df2.columns:
        df2[col] = df2[col].replace(['no_spur', 'invalid'], np.nan)

# 将pwr列中的[]和#VALUE!替换为NaN
pwr_cols = [col for col in df1.columns if 'pwr' in col or 'avg' in col]
for col in pwr_cols:
    if col in df1.columns:
        df1[col] = df1[col].replace(['#VALUE!', '[', ']', '', ' ', 'no_spur'], np.nan)
        df1[col] = pd.to_numeric(df1[col], errors='coerce')
    if col in df2.columns:
        df2[col] = df2[col].replace(['#VALUE!', '[', ']', '', ' ', 'no_spur'], np.nan)
        df2[col] = pd.to_numeric(df2[col], errors='coerce')

# 创建合并键（使用所有配置列）
merge_columns = ['phy_mode', 'channel', 'frequency', 'Used_Frequency', 'X_CoefFixed', 'Y_CoefFixed']

# 合并两个数据框
merged_df = pd.merge(df1, df2, on=merge_columns, how='outer', suffixes=('_normal', '_xtal'))

print(f"\n合并后数据行数: {len(merged_df)}")
print(f"同时存在于两个文件中的配置数: {len(pd.merge(df1, df2, on=merge_columns, how='inner'))}")

# 计算差异
if 'avg pwr_normal' in merged_df.columns and 'avg pwr_xtal' in merged_df.columns:
    merged_df['avg_pwr_diff'] = merged_df['avg pwr_xtal'] - merged_df['avg pwr_normal']
else:
    print("警告：未找到平均功率列，无法计算差异")

# 标记异常数据（差异超过阈值）
threshold = 5  # 设定5dB为异常值阈值
merged_df['is_abnormal'] = np.abs(merged_df['avg_pwr_diff']) > threshold

# 保存结果到新文件
output_file = r'D:\users\gxu\spur_scan\260309\scan_spur_data\spur_comparison_analysis.xlsx'

# 使用ExcelWriter保存到Excel文件
with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    # 保存完整数据
    merged_df.to_excel(writer, sheet_name='完整数据', index=False)

    # 保存异常数据
    abnormal_df = merged_df[merged_df['is_abnormal']]
    abnormal_df.to_excel(writer, sheet_name='异常数据', index=False)

    # 保存统计摘要
    stats = []

    # 整体统计
    stats.append(['总配置数', len(merged_df)])
    stats.append(['同时存在于两个文件的配置数', len(merged_df.dropna(subset=['avg pwr_normal', 'avg pwr_xtal']))])
    stats.append(['仅存在于normal模式的配置数', len(merged_df[merged_df['avg pwr_normal'].notna() & merged_df['avg pwr_xtal'].isna()])])
    stats.append(['仅存在于xtal模式的配置数', len(merged_df[merged_df['avg pwr_normal'].isna() & merged_df['avg pwr_xtal'].notna()])])
    stats.append(['异常配置数', len(abnormal_df)])
    stats.append(['异常率', f"{len(abnormal_df)/len(merged_df.dropna(subset=['avg_pwr_diff'])):.1%}"])

    # 差异统计
    if 'avg_pwr_diff' in merged_df.columns:
        valid_diff = merged_df['avg_pwr_diff'].dropna()
        stats.append(['平均差异', f"{valid_diff.mean():.2f} dB"])
        stats.append(['最大差异', f"{valid_diff.max():.2f} dB"])
        stats.append(['最小差异', f"{valid_diff.min():.2f} dB"])
        stats.append(['标准差', f"{valid_diff.std():.2f} dB"])

    pd.DataFrame(stats, columns=['指标', '值']).to_excel(writer, sheet_name='统计摘要', index=False)

    # 获取工作簿和工作表对象以设置格式
    workbook = writer.book

    # 为完整数据添加条件格式
    worksheet = writer.sheets['完整数据']

    # 设置列宽
    worksheet.set_column('A:A', 10)  # phy_mode
    worksheet.set_column('B:B', 8)   # channel
    worksheet.set_column('C:C', 30)  # frequency
    worksheet.set_column('D:D', 12)  # Used_Frequency
    worksheet.set_column('E:E', 30)  # X_CoefFixed
    worksheet.set_column('F:F', 30)  # Y_CoefFixed
    for i in range(7, 17):  # pwr列和差异列
        worksheet.set_column(f'{chr(64+i)}:{chr(64+i)}', 12)

    # 添加差异列的条件格式（正差异为红色，负差异为蓝色，异常为黄色填充）
    if 'avg_pwr_diff' in merged_df.columns:
        # 获取差异列的索引
        diff_col_idx = merged_df.columns.get_loc('avg_pwr_diff') + 1  # Excel是1-based

        # 创建格式
        format_red = workbook.add_format({'font_color': 'red'})
        format_blue = workbook.add_format({'font_color': 'blue'})
        format_yellow = workbook.add_format({'bg_color': 'yellow', 'bold': True})

        # 应用条件格式
        worksheet.conditional_format(f'{chr(64+diff_col_idx)}2:{chr(64+diff_col_idx)}{len(merged_df)+1}',
                                    {'type': 'cell', 'criteria': '>', 'value': 0, 'format': format_red})
        worksheet.conditional_format(f'{chr(64+diff_col_idx)}2:{chr(64+diff_col_idx)}{len(merged_df)+1}',
                                    {'type': 'cell', 'criteria': '<', 'value': 0, 'format': format_blue})

        # 为异常值添加黄色填充
        for i, (idx, row) in enumerate(merged_df.iterrows()):
            if row['is_abnormal']:
                worksheet.write_row(i+1, 0, list(row), format_yellow)

    # 为异常数据工作表设置格式
    if len(abnormal_df) > 0:
        worksheet_abnormal = writer.sheets['异常数据']
        worksheet_abnormal.set_column('A:A', 10)
        worksheet_abnormal.set_column('B:B', 8)
        worksheet_abnormal.set_column('C:C', 30)
        worksheet_abnormal.set_column('D:D', 12)
        worksheet_abnormal.set_column('E:E', 30)
        worksheet_abnormal.set_column('F:F', 30)
        for i in range(7, 17):
            worksheet_abnormal.set_column(f'{chr(64+i)}:{chr(64+i)}', 12)

        # 添加异常数据的黄色填充
        format_yellow = workbook.add_format({'bg_color': 'yellow', 'bold': True})
        for i, (idx, row) in enumerate(abnormal_df.iterrows()):
            worksheet_abnormal.write_row(i+1, 0, list(row), format_yellow)

    # 为统计摘要工作表设置格式
    worksheet_stats = writer.sheets['统计摘要']
    worksheet_stats.set_column('A:A', 20)
    worksheet_stats.set_column('B:B', 15)
    worksheet_stats.set_row(0, 20, workbook.add_format({'bold': True}))
    worksheet_stats.conditional_format('A2:B100', {'type': 'no_errors'})

print(f"\n=== 分析完成 ===")
print(f"结果已保存到: {output_file}")
print(f"异常数据（差异 > {threshold}dB）数: {len(abnormal_df)}")
print(f"异常配置列表:")
for i, row in abnormal_df.iterrows():
    print(f"phy_mode={row['phy_mode']}, channel={row['channel']}, frequency={row['frequency']}, 差异={row['avg_pwr_diff']:.2f}dB")

# 显示分析结果
print("\n=== 详细分析结果 ===")
print(f"配置总数: {len(merged_df)}")
print(f"有效配置数（有数据的）: {len(merged_df.dropna(subset=['avg pwr_normal', 'avg pwr_xtal']))}")

# 显示差异统计
if 'avg_pwr_diff' in merged_df.columns:
    valid_diff = merged_df['avg_pwr_diff'].dropna()
    print(f"平均差异: {valid_diff.mean():.2f} dB")
    print(f"最大差异: {valid_diff.max():.2f} dB（{threshold}dB以上被视为异常）")
    print(f"最小差异: {valid_diff.min():.2f} dB")
    print(f"差异标准差: {valid_diff.std():.2f} dB")

print(f"\n=== 异常数据详情 ===")
if len(abnormal_df) > 0:
    print(abnormal_df[merge_columns + ['avg pwr_normal', 'avg pwr_xtal', 'avg_pwr_diff']])
else:
    print("无异常数据")
