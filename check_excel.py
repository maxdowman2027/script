
import pandas as pd

df = pd.read_excel(r'D:/users/gxu/spur_scan/260310/scan_spur_data/xtal_duty_disable/spur_scan_result_2G_coef_异常检测.xlsx')
print('文件内容前5行:')
print(df.head())
print('\n文件包含的列:')
print(df.columns.tolist())
print('\n异常列信息:')
print(df['异常列'].head(20))
