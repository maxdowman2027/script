#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用于整理 RX IQ 测试数据的脚本。
将源路径下的文件根据其内容中的 bw、freqMhz 和 channel 列的数据重命名，并按照目的路径的目录结构存放。
"""

import os
import csv
import shutil
import re


# ================= 配置区域 =================
# 在这里修改配置
SOURCE_PATH = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\rx_iq_cal_pwr\FPGA752_FPGA761_20260417"  # 源路径
DESTINATION_PATH = r"D:\users\gxu\rx_iq\E22\regression_v3_260418"  # 目的路径
# ===========================================


def get_band(freq):
    """
    根据频率确定频段（2G/5G）

    Args:
        freq: 频率值（MHz）

    Returns:
        频段字符串（2G 或 5G）
    """
    if freq < 3000:
        return "2G"
    else:
        return "5G"


def get_bandwidth_str(bw):
    """
    根据带宽确定带宽字符串（20m/40m/80m/160m）

    Args:
        bw: 带宽值（MHz）

    Returns:
        带宽字符串（20m/40m/80m/160m）
    """
    return f"{bw}m"


def get_channel_str(channel):
    """
    根据通道信息确定通道字符串（ch0/ch1/mimo）

    Args:
        channel: 通道信息

    Returns:
        通道字符串（ch0/ch1/mimo）
    """
    if channel == "ch0":
        return "ch0"
    elif channel == "ch1":
        return "ch1"
    elif channel == "mimo":
        return "mimo"
    else:
        return "unknown"


def create_directories(path):
    """
    创建目录（如果不存在）

    Args:
        path: 目录路径
    """
    if not os.path.exists(path):
        os.makedirs(path)


def copy_and_rename_files():
    """
    复制并重命名文件
    """
    # 遍历源路径下的所有 CSV 文件
    for filename in os.listdir(SOURCE_PATH):
        if filename.endswith(".csv") and filename.startswith("rx_iq_cal_res_FPGA752_FPGA761"):
            source_file = os.path.join(SOURCE_PATH, filename)
            print(f"正在处理: {filename}")

            # 读取 CSV 文件的第一行数据，获取 bw、freqMhz 和 channel 信息
            try:
                with open(source_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    if reader.fieldnames:
                        # 检查是否包含所需的列（忽略大小写和空格）
                        required_fields = ["bw", "freqMhz", "channel"]
                        field_map = {}  # 用于存储列名映射
                        found_all = True
                        for req_field in required_fields:
                            found = False
                            for actual_field in reader.fieldnames:
                                if req_field.lower() == actual_field.strip().lower():
                                    field_map[req_field] = actual_field
                                    found = True
                                    break
                            if not found:
                                found_all = False
                                print(f"警告: 文件 {filename} 缺少列 '{req_field}'")
                                break

                        if found_all:
                            # 读取第一行数据
                            first_row = next(reader, None)
                            if first_row:
                                bw = int(float(first_row[field_map["bw"]]))
                                freqMhz = float(first_row[field_map["freqMhz"]])
                                channel = first_row[field_map["channel"]].strip()

                                # 确定频段、带宽和通道字符串
                                band = get_band(freqMhz)
                                bandwidth_str = get_bandwidth_str(bw)
                                channel_str = get_channel_str(channel)

                                # 生成新的文件名和存放路径
                                new_filename = filename.replace("rx_iq_cal_res_FPGA752_FPGA761", f"rx_iq_cal_res_{band}_{bandwidth_str}_{channel_str}")
                                new_path = os.path.join(DESTINATION_PATH, band)
                                create_directories(new_path)
                                if bandwidth_str:
                                    new_path = os.path.join(new_path, bandwidth_str)
                                    create_directories(new_path)
                                if channel_str:
                                    new_path = os.path.join(new_path, channel_str)
                                    create_directories(new_path)

                                # 复制并移动文件
                                dest_file = os.path.join(new_path, new_filename)
                                shutil.copy2(source_file, dest_file)
                                print(f"已复制到: {dest_file}")
                            else:
                                print(f"警告: 文件 {filename} 是空的")
                        else:
                            print(f"警告: 文件 {filename} 缺少所需的列")
            except Exception as e:
                print(f"错误: 无法读取文件 {filename} - {e}")


def main():
    print("开始整理 RX IQ 测试数据...")
    print(f"源路径: {SOURCE_PATH}")
    print(f"目的路径: {DESTINATION_PATH}")
    print()

    # 检查源路径是否存在
    if not os.path.exists(SOURCE_PATH):
        print(f"错误: 源路径 {SOURCE_PATH} 不存在")
        return

    # 创建目的路径
    create_directories(DESTINATION_PATH)

    # 复制并重命名文件
    copy_and_rename_files()

    print()
    print("整理完成!")


if __name__ == "__main__":
    main()