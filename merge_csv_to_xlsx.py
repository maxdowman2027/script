#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并risc_wifitx格式的CSV文件到XLSX文件，按channel和编码方式（BCC/LDPC）划分Sheet
"""

import os
import glob
import pandas as pd
import re
import argparse


def merge_csv_to_xlsx(input_dir, output_file, crc_fail_file=None):
    """
    合并指定文件夹中的CSV文件到XLSX文件

    Args:
        input_dir: 包含CSV文件的文件夹路径
        output_file: 输出的XLSX文件路径
        crc_fail_file: 保存psdu_crc为Fail的情况的XLSX文件路径
    """
    # 查找所有risc_wifitx_*.csv文件
    csv_files = glob.glob(os.path.join(input_dir, 'risc_wifitx_*.csv'))

    if not csv_files:
        print(f"未找到符合条件的CSV文件: {input_dir}")
        return

    print(f"找到 {len(csv_files)} 个CSV文件")

    # 按channel和编码方式分组
    grouped_files = {}

    for csv_file in csv_files:
        filename = os.path.basename(csv_file)

        # 从文件名中提取channel和编码方式
        # 文件名格式示例: risc_wifitx_20m_['11b']_BCC_channel11_GILTF0_2026-0331-175943.csv
        channel_match = re.search(r'channel(\d+)', filename)
        coding_match = re.search(r'(BCC|LDPC)', filename)

        if channel_match and coding_match:
            channel = channel_match.group(1)
            coding = coding_match.group(1)
            sheet_name = f"channel{channel}_{coding}"

            if sheet_name not in grouped_files:
                grouped_files[sheet_name] = []

            grouped_files[sheet_name].append(csv_file)

    print(f"按Sheet分组后: {list(grouped_files.keys())}")

    # 创建Excel写入器
    writer = pd.ExcelWriter(output_file, engine='openpyxl')
    crc_writer = None
    if crc_fail_file:
        crc_writer = pd.ExcelWriter(crc_fail_file, engine='openpyxl')

    # 处理每个分组的文件
    for sheet_name, files in grouped_files.items():
        print(f"处理Sheet: {sheet_name} ({len(files)}个文件)")

        # 读取所有CSV文件
        dfs = []
        for f in files:
            try:
                df = pd.read_csv(f)
                dfs.append(df)
            except Exception as e:
                print(f"读取文件 {f} 失败: {e}")
                continue

        if dfs:
            # 合并数据
            merged_df = pd.concat(dfs, ignore_index=True)

            # 写入到Sheet
            merged_df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"成功写入 {len(merged_df)} 行数据到 {sheet_name}")

            # 检查是否需要保存crc失败的情况
            if crc_writer and 'psdu_crc' in merged_df.columns:
                crc_fail_df = merged_df[merged_df['psdu_crc'] == 'Fail']
                if not crc_fail_df.empty:
                    crc_fail_df.to_excel(crc_writer, sheet_name=sheet_name, index=False)
                    print(f"找到 {len(crc_fail_df)} 行psdu_crc为Fail的记录，已写入到 {crc_fail_file}")

    # 保存文件
    try:
        writer.close()
        print(f"合并完成！文件已保存到: {output_file}")

        if crc_writer:
            crc_writer.close()
            print(f"CRC失败记录已保存到: {crc_fail_file}")
    except Exception as e:
        print(f"保存文件失败: {e}")


def main():
    # 直接在代码中修改输入路径和输出文件路径
    input_dir = "D:/chip_test/dev/xian_test/Xian-Esp-Test-Scripts/py_script_fpga_tx_wifi7/Log/wifi_tx_rls4/no_he"
    output_file = "D:/chip_test/dev/xian_test/Xian-Esp-Test-Scripts/py_script_fpga_tx_wifi7/Log/wifi_tx_rls4/no_he/merged_result.xlsx"
    crc_fail_file = "D:/chip_test/dev/xian_test/Xian-Esp-Test-Scripts/py_script_fpga_tx_wifi7/Log/wifi_tx_rls4/no_he/crc_fail_result.xlsx"

    print(f"输入路径: {input_dir}")
    print(f"输出文件: {output_file}")
    print(f"CRC失败记录文件: {crc_fail_file}")

    merge_csv_to_xlsx(input_dir, output_file, crc_fail_file)


if __name__ == '__main__':
    main()
