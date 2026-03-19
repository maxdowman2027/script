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
SEARCH_DIRECTORY = r"D:\users\gxu\rx_iq\E22\mimo_train_mimo_apply"  # 要搜索的根目录
FILE_PATTERN = "rx_iq_cal_res_*.csv"  # 文件名匹配模式（支持通配符）
DIFF_PWR_THRESHOLD = 45  # diff_pwr列的阈值（值小于此数的行将被提取）
OUTPUT_FILE = r"D:\users\gxu\rx_iq\E22\mimo_train_mimo_apply\output\mimo_filtered_diff_pwr.csv"  # 输出文件路径
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
                # 读取CSV文件并去除列名的空格
                lines = [line.strip() for line in f if line.strip()]
                if not lines:
                    print(f"警告: 文件 {file_path} 是空文件，已跳过")
                    continue

                # 处理列名，去除每个列名的前后空格
                dialect = csv.Sniffer().sniff(lines[0])
                reader = csv.DictReader(lines, dialect=dialect)

                # 去除列名的前后空格
                cleaned_fieldnames = [field.strip() for field in reader.fieldnames]
                reader.fieldnames = cleaned_fieldnames

                if header is None:
                    header = cleaned_fieldnames

                # 检查是否包含diff_pwr列（忽略大小写和空格）
                has_diff_pwr = False
                diff_pwr_column = None
                for field in cleaned_fieldnames:
                    if field.strip().lower() == "diff_pwr":
                        has_diff_pwr = True
                        diff_pwr_column = field
                        break

                if not has_diff_pwr:
                    print(f"警告: 文件 {file_path} 不包含 diff_pwr 列，已跳过")
                    continue

                # 查找符合条件的行
                for row in reader:
                    try:
                        # 去除值的空格后转换为浮点数
                        diff_pwr_value = row[diff_pwr_column].strip()
                        diff_pwr = float(diff_pwr_value)

                        if diff_pwr < threshold:
                            # 去除所有值的前后空格
                            cleaned_row = {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}
                            # 添加文件名信息到行数据中，方便追踪来源
                            cleaned_row["source_file"] = os.path.basename(file_path)
                            cleaned_row["full_path"] = file_path
                            all_matching_rows.append(cleaned_row)
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
            os.makedirs(output_dir, exist_ok=True)
            print(f"已创建输出目录: {output_dir}")

        # 添加来源文件列到表头（如果不存在）
        if header and "source_file" not in header:
            header.append("source_file")
        if header and "full_path" not in header:
            header.append("full_path")

        # 写入输出文件
        try:
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writeheader()
                writer.writerows(all_matching_rows)

            print(f"处理完成! 共找到 {len(all_matching_rows)} 行符合条件的数据")
            print(f"结果已保存到: {output_file}")
        except Exception as e:
            print(f"错误: 无法写入输出文件 {output_file}: {e}")
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
