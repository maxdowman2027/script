#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：将 CSV 文件中的指定 bit 字段转换为有符号数，并允许用户自定义列名
"""

import csv
import os

def twos_complement(value, bits):
    """
    将无符号整数转换为二进制补码表示的有符号整数
    """
    if value & (1 << (bits - 1)):
        value -= (1 << bits)
    return value

def convert_csv_file():
    """
    转换 CSV 文件中的 bit 字段为有符号数
    """
    # ==================== 配置区域 ====================

    # 输入文件路径（请修改为您要处理的文件路径）
    input_file = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\dump_node_124\FPGA752_0x_20260428\dump__FPGA752_0x_20260428_195309.csv"

    # 输出文件路径（可选，留空则自动生成）
    output_file = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\dump_node_124\FPGA752_0x_20260428\vht_5180_pwr0_mcs8_bcc_bw20m_dacdata.csv"

    # 要转换的字段列表，格式为 [high:low]
    bit_fields = [
        "[11:0]",
        "[27:16]"
    ]

    # 新列名列表（可选，留空则自动生成）
    column_names = [
        "sample_i",
        "sample_q"
    ]

    # ==================== 处理区域 ====================

    print(f"正在处理文件: {input_file}")

    # 验证输出文件名
    if not output_file:
        input_name, input_ext = os.path.splitext(input_file)
        output_file = f"{input_name}_converted{input_ext}"

    # 处理字段名
    if not column_names or len(column_names) != len(bit_fields):
        column_names = [f"{field}_signed" for field in bit_fields]

    # 读取输入文件
    with open(input_file, mode='r', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)

        # 获取实际的列名（可能包含空格）
        actual_column_name = list(reader.fieldnames)[0]

        # 添加新列名到字段列表
        fieldnames = [actual_column_name] + column_names

        # 创建输出文件并写入
        with open(output_file, mode='w', newline='', encoding='utf-8') as out_file:
            writer = csv.DictWriter(out_file, fieldnames=fieldnames)
            writer.writeheader()

            row_count = 0
            for row in reader:
                # 处理每一行数据
                new_row = {actual_column_name: row[actual_column_name]}

                try:
                    # 解析 #dump_data 列的十六进制数据
                    hex_value = row[actual_column_name].strip().rstrip(',')  # 去除可能的逗号
                    value = int(hex_value, 16)

                    for i, field in enumerate(bit_fields):
                        # 解析字段定义，如 [11:0]
                        if field.startswith('[') and field.endswith(']'):
                            field_str = field[1:-1]
                            high_bit, low_bit = map(int, field_str.split(':'))

                            # 提取指定范围的 bits
                            mask = (1 << (high_bit - low_bit + 1)) - 1
                            extracted = (value >> low_bit) & mask

                            # 转换为有符号数
                            signed_value = twos_complement(extracted, high_bit - low_bit + 1)

                            # 添加到新列
                            new_row[column_names[i]] = signed_value

                except ValueError as e:
                    print(f"警告：无法解析 #dump_data 的值 '{row['#dump_data']}': {e}")
                    # 为无法解析的行添加空值
                    for col_name in column_names:
                        new_row[col_name] = ''

                writer.writerow(new_row)
                row_count += 1

            print(f"处理完成，共处理 {row_count} 行数据")

    print(f"结果已保存到: {output_file}")
    return output_file

def main():
    try:
        output_file = convert_csv_file()
        print("\n成功完成！")

    except Exception as e:
        print(f"\n错误：{e}")
        import traceback
        print(traceback.format_exc())

if __name__ == '__main__':
    main()