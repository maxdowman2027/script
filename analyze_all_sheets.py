import pandas as pd
import os

# 读取Excel文件的所有sheet
file_path = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx_rls4\hesu_heersu_260402\tx_crc_fail_result.xlsx"
xls = pd.ExcelFile(file_path)
sheet_names = xls.sheet_names

print(f"Excel文件包含 {len(sheet_names)} 个sheet:")
for sheet in sheet_names:
    print(f"  - {sheet}")

all_data = []
for sheet in sheet_names:
    try:
        df = pd.read_excel(xls, sheet_name=sheet)
        print(f"\n=== 正在分析 '{sheet}' ===")
        print(f"数据行数: {len(df)}")
        print(f"列数: {len(df.columns)}")

        # 检查是否包含关键列
        required_columns = ['rate', 'tx_power_set(dBm)', 'evm']
        missing_cols = [col for col in required_columns if col not in df.columns]

        if missing_cols:
            print(f"警告: '{sheet}' 缺少关键列: {', '.join(missing_cols)}")
        else:
            print(f"所有关键列存在，已添加到总数据集")
            all_data.append(df)

    except Exception as e:
        print(f"读取 '{sheet}' 时出错: {e}")

# 合并所有有效数据
if all_data:
    merged_df = pd.concat(all_data, ignore_index=True)

    print(f"\n=== 合并后总数据集信息 ===")
    print(merged_df.info())

    # 分组统计
    print(f"\n=== 按 rate、tx_power_set、evm 分组的 CRC fail 统计 ===")
    grouped = merged_df.groupby(['rate', 'tx_power_set(dBm)', 'evm']).size().reset_index(name='fail_count')
    print(grouped)

    # 按 sheet 统计
    print(f"\n=== 各 sheet 的记录数 ===")
    sheet_counts = []
    for sheet in sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=sheet)
            count = len(df)
        except:
            count = 0
        sheet_counts.append({'sheet_name': sheet, 'record_count': count})
    sheet_stats = pd.DataFrame(sheet_counts)
    print(sheet_stats)

    # 保存分析结果
    output_file = os.path.splitext(file_path)[0] + "_all_sheets_analysis.xlsx"
    with pd.ExcelWriter(output_file) as writer:
        # 合并后的总数据
        merged_df.to_excel(writer, sheet_name='合并总数据', index=False)

        # 分组统计
        grouped.to_excel(writer, sheet_name='分组统计', index=False)

        # 各 sheet 记录数
        sheet_stats.to_excel(writer, sheet_name='Sheet记录数统计', index=False)

        # 每个 sheet 的原始数据
        for sheet in sheet_names:
            try:
                df = pd.read_excel(xls, sheet_name=sheet)
                df.to_excel(writer, sheet_name=f"{sheet}_原始数据", index=False)
            except:
                continue

    print(f"\n所有sheet的分析结果已保存到: {output_file}")
else:
    print("\n没有找到包含完整关键列的有效数据")
