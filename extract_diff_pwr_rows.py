#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
递归检索指定目录下的CSV文件，查找diff_pwr列中值小于指定阈值的行，并汇总到输出文件
"""

import os
import csv
import glob


# ================= 配置区域 =================
# 在这里修改配置
SEARCH_DIRECTORY = r"D:\users\gxu\rx_iq"  # 要搜索的根目录
FILE_PATTERN = "*.csv"  # 文件名匹配模式（支持通配符）
DIFF_PWR_THRESHOLD = 0.5  # diff_pwr列的阈值（值小于此数的行将被提取）
OUTPUT_FILE = r"D:\users\gxu\scripts\output\filtered_diff_pwr.csv"  # 输出文件路径
# ===========================================


def find_csv_files(directory: str, pattern: str = "*.csv") -> list:
    """
    递归查找指定目录下符合模式的CSV文件

    Args:
        directory: 要搜索的目录
        pattern: 文件名匹配模式，默认为"*.csv"

    Returns:
        符合条件的文件路径列表
    """
    csv_files = []
    # 使用glob递归查找符合模式的文件
    for file_path in glob.glob(os.path.join(directory, "**", pattern), recursive=True):
        if os.path.isfile(file_path):
            csv_files.append(file_path)
    return csv_files


def extract_rows_with_diff_pwr(csv_files: list, threshold: float, output_file: str):
    """
    从CSV文件中提取diff_pwr列值小于阈值的行，并保存到输出文件

    Args:
        csv_files: 要处理的CSV文件列表
        threshold: diff_pwr列的阈值
        output_file: 输出文件路径
    """
    all_matching_rows = []
    header = None

    print(f"开始处理 {len(csv_files)} 个CSV文件...")

    for file_path in csv_files:
        print(f"正在处理: {file_path}")
        try:
            with open(file_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if header is None:
                    header = reader.fieldnames

                # 检查是否包含diff_pwr列
                if "diff_pwr" not in reader.fieldnames:
                    print(f"警告: 文件 {file_path} 不包含 diff_pwr 列，已跳过")
                    continue

                # 查找符合条件的行
                for row in reader:
                    try:
                        diff_pwr = float(row["diff_pwr"])
                        if diff_pwr < threshold:
                            # 添加文件名信息到行数据中，方便追踪来源
                            row["source_file"] = os.path.basename(file_path)
                            row["full_path"] = file_path
                            all_matching_rows.append(row)
                    except (ValueError, KeyError) as e:
                        print(f"警告: 文件 {file_path} 中某行数据格式错误: {e}")
                        continue

        except Exception as e:
            print(f"错误: 无法读取文件 {file_path}: {e}")
            continue

    # 保存到输出文件
    if all_matching_rows:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 添加来源文件列到表头
        if header and "source_file" not in header:
            header.append("source_file")
        if header and "full_path" not in header:
            header.append("full_path")

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            writer.writerows(all_matching_rows)

        print(f"处理完成! 共找到 {len(all_matching_rows)} 行符合条件的数据")
        print(f"结果已保存到: {output_file}")
    else:
        print("未找到符合条件的数据")


def main():
    print("配置信息:")
    print(f"  搜索目录: {SEARCH_DIRECTORY}")
    print(f"  文件模式: {FILE_PATTERN}")
    print(f"  阈值: {DIFF_PWR_THRESHOLD}")
    print(f"  输出文件: {OUTPUT_FILE}")
    print()

    # 查找符合条件的CSV文件
    csv_files = find_csv_files(SEARCH_DIRECTORY, FILE_PATTERN)

    if not csv_files:
        print(f"在 {SEARCH_DIRECTORY} 中未找到符合模式 {FILE_PATTERN} 的CSV文件")
        return

    print(f"找到 {len(csv_files)} 个符合条件的CSV文件")

    # 提取符合条件的行
    extract_rows_with_diff_pwr(csv_files, DIFF_PWR_THRESHOLD, OUTPUT_FILE)


if __name__ == "__main__":
    main()
