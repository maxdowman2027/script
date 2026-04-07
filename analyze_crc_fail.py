import pandas as pd
import os

# 读取Excel文件
file_path = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx_rls4\hesu_heersu_260402\tx_crc_fail_result.xlsx"
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

# 如果存在这些列，进行分组统计
if all(col in df.columns for col in required_columns):
    print("\n=== 按 rate、tx_power_set、evm 分组的 CRC fail 统计 ===")
    grouped = df.groupby(['rate', 'tx_power_set(dBm)', 'evm']).size().reset_index(name='fail_count')
    print(grouped)

    # 保存统计结果到新的Excel文件
    output_file = os.path.splitext(file_path)[0] + "_summary.xlsx"
    grouped.to_excel(output_file, index=False)
    print(f"\n统计结果已保存到: {output_file}")
