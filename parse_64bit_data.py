#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析 64 位十六进制数据，拆分为两个 32 位数据行（低 32 位在前，高 32 位在后），
并从每个 32 位数据中提取 sample_q（[11:0]）和 sample_i（[23:12]）
"""

import csv

def parse_64bit_data(input_file, output_file):
    """
    解析 64 位数据并保存结果
    """
    # 存储解析结果
    results = []

    print(f"开始解析文件: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

        print(f"文件包含 {len(lines)} 行数据")

        # 跳过第一行标题
        for i, line in enumerate(lines[1:], start=1):
            line = line.strip()

            if line:
                # 去除逗号
                if line.endswith(','):
                    line = line[:-1]

                # 去除 0x 前缀
                if line.startswith('0x'):
                    line = line[2:]

                try:
                    # 转换为整数
                    value = int(line, 16)

                    # 拆分为低 32 位和高 32 位
                    low_32bit = value & 0xFFFFFFFF
                    high_32bit = (value >> 32) & 0xFFFFFFFF

                    # 解析低 32 位
                    sample_q_low = low_32bit & 0xFFF  # [11:0]
                    sample_i_low = (low_32bit >> 12) & 0xFFF  # [23:12]

                    # 解析高 32 位
                    sample_q_high = high_32bit & 0xFFF  # [11:0]
                    sample_i_high = (high_32bit >> 12) & 0xFFF  # [23:12]

                    # 转换为有符号整数 (12位)
                    def to_signed_12bit(x):
                        if x >= 2048:
                            return x - 4096
                        return x

                    sample_q_low = to_signed_12bit(sample_q_low)
                    sample_i_low = to_signed_12bit(sample_i_low)
                    sample_q_high = to_signed_12bit(sample_q_high)
                    sample_i_high = to_signed_12bit(sample_i_high)

                    # 保存低 32 位行
                    results.append({
                        'line_number': i,
                        'original_value': f'0x{line.zfill(16)}',
                        'data_32bit': f'0x{low_32bit:08X}',
                        'bit_range': 'low_32bit',
                        'sample_q': sample_q_low,
                        'sample_i': sample_i_low
                    })

                    # 保存高 32 位行
                    results.append({
                        'line_number': i,
                        'original_value': f'0x{line.zfill(16)}',
                        'data_32bit': f'0x{high_32bit:08X}',
                        'bit_range': 'high_32bit',
                        'sample_q': sample_q_high,
                        'sample_i': sample_i_high
                    })

                except Exception as e:
                    print(f"解析第 {i} 行数据失败: {e}")
                    continue

        print(f"成功解析 {len(lines) - 1} 条 64 位数据，生成 {len(results)} 条 32 位数据行")

        # 保存结果到 CSV 文件
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'line_number',
                'original_value',
                'data_32bit',
                'bit_range',
                'sample_q',
                'sample_i'
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(results)

            print(f"结果已保存到: {output_file}")

            return True

    return False

if __name__ == "__main__":
    # 输入文件路径
    input_file = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\dump_node_124\FPGA752_0x_20260428\dump__FPGA752_0x_20260428_104813.csv"

    # 输出文件路径
    output_file = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\dump_node_124\FPGA752_0x_20260428\parsed_data.csv"

    parse_64bit_data(input_file, output_file)