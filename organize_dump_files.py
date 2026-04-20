#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将源路径下的文件按照文件名的配置格式copy到目的路径下的对应层级目录中
"""

import os
import shutil
import re

# ================= 配置区域 =================
# 在这里修改配置
SOURCE_PATH = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\dump_iqcomb_0x240\FPGA752_FPGA761_20260417"  # 源路径
DESTINATION_PATH = r"D:\users\gxu\rx_iq\E22\regression_v3_260418\ch0"  # 目的路径
# ===========================================


def get_band(freq):
    """
    根据频率确定频段（2G/5G/6G）

    Args:
        freq: 频率值（MHz）

    Returns:
        频段字符串（2G 或 5G 或 6G）
    """
    if freq < 3000:
        return "2G"
    elif freq < 5985:
        return "5G"
    else:
        return "6G"


def get_bandwidth(phymd):
    """
    根据phymd值确定带宽

    Args:
        phymd: phymd值

    Returns:
        带宽字符串（20m/40m/80m/160m）
    """
    if phymd == "20":
        return "20m"
    elif phymd == "40":
        return "40m"
    elif phymd == "80":
        return "80m"
    elif phymd == "160":
        return "160m"
    else:
        return "unknown"


def parse_filename(filename):
    """
    解析文件名，提取phymd和chan信息

    Args:
        filename: 文件名

    Returns:
        (phymd, chan) 元组
    """
    # 匹配文件名格式：dump_phymdxx_chanxxx_xxxx
    match = re.match(r"dump_phymd(\d+)_chan(\d+)_.*", filename)
    if match:
        phymd = match.group(1)
        chan = int(match.group(2))
        return (phymd, chan)
    else:
        return (None, None)


def create_directories(path):
    """
    创建目录（如果不存在）

    Args:
        path: 目录路径
    """
    if not os.path.exists(path):
        os.makedirs(path)


def copy_and_organize_files():
    """
    复制并组织文件
    """
    # 遍历源路径下的所有文件
    for filename in os.listdir(SOURCE_PATH):
        if filename.startswith("dump_phymd") and (filename.endswith(".csv") or filename.endswith(".pdf")):
            source_file = os.path.join(SOURCE_PATH, filename)
            print(f"正在处理: {filename}")

            # 解析文件名
            phymd, chan = parse_filename(filename)
            if phymd and chan:
                bandwidth = get_bandwidth(phymd)
                band = get_band(chan)

                # 根据带宽确定目标路径
                if bandwidth == "160m":
                    # phymd160 的文件与 2G、5G、6G 等文件夹同一层级，创建 160m 文件夹放入
                    dest_dir = os.path.join(DESTINATION_PATH, bandwidth)
                    create_directories(dest_dir)
                else:
                    # 其余带宽的文件按照 2G/5G/6G -> bandwidth 层级放入
                    dest_dir = os.path.join(DESTINATION_PATH, band, bandwidth)
                    create_directories(dest_dir)

                # 复制文件到目标路径
                dest_file = os.path.join(dest_dir, filename)
                shutil.copy2(source_file, dest_file)
                print(f"已复制到: {dest_file}")
            else:
                print(f"警告: 文件名格式不符合要求: {filename}")


def main():
    print("开始组织文件...")
    print(f"源路径: {SOURCE_PATH}")
    print(f"目的路径: {DESTINATION_PATH}")
    print()

    # 检查源路径是否存在
    if not os.path.exists(SOURCE_PATH):
        print(f"错误: 源路径 {SOURCE_PATH} 不存在")
        return

    # 创建目的路径
    create_directories(DESTINATION_PATH)

    # 复制并组织文件
    copy_and_organize_files()

    print()
    print("文件组织完成!")


if __name__ == "__main__":
    main()