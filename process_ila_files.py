#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理FPGA导出的ILA信号文件脚本

功能：
1. 遍历指定目录下的所有.ila文件
2. 解压缩每个.ila文件（ZIP格式）
3. 提取其中的waveform.csv文件
4. 按照ILA文件名进行更名
5. 支持批量处理和进度显示
"""

import os
import zipfile
import argparse
from pathlib import Path
from tqdm import tqdm

# ===========================================
# 配置参数 - 可根据需要修改
# ===========================================
# 输入目录：包含.ila文件的目录
INPUT_DIR = r"D:\test_data\rls4\260428\tx_data2"

# 输出目录：用于保存提取后的CSV文件（默认与输入目录相同）
# 如果需要保存到其他目录，请修改此处
OUTPUT_DIR = None  # 设为None表示与输入目录相同

# 是否递归处理子目录
RECURSIVE = False

# 是否保留原始ILA文件（处理后不删除）
KEEP_ORIGINAL = True

# 是否处理后删除原始ILA文件
DELETE_ORIGINAL = False

# ===========================================
# 核心处理函数
# ===========================================
def process_ila_file(ila_path: Path, output_dir: Path, keep_original: bool = True) -> bool:
    """
    处理单个ILA文件

    Args:
        ila_path: ILA文件路径
        output_dir: 输出目录
        keep_original: 是否保留原始ILA文件

    Returns:
        处理是否成功
    """
    try:
        # 检查文件是否存在
        if not ila_path.exists():
            print(f"[ERROR] 文件不存在: {ila_path}")
            return False

        # 检查是否是ZIP压缩包
        if not zipfile.is_zipfile(str(ila_path)):
            print(f"[ERROR] 不是有效的ZIP压缩包: {ila_path}")
            return False

        # 创建输出目录
        output_dir.mkdir(parents=True, exist_ok=True)

        # 解压缩ILA文件
        with zipfile.ZipFile(str(ila_path), 'r') as zip_ref:
            # 检查是否包含waveform.csv
            file_list = zip_ref.namelist()
            waveform_files = [f for f in file_list if f.lower() == 'waveform.csv']

            if not waveform_files:
                print(f"[WARNING] 未找到waveform.csv文件: {ila_path}")
                return False

            # 提取waveform.csv文件
            waveform_file = waveform_files[0]
            extracted_path = output_dir / f"{ila_path.stem}.csv"

            with open(extracted_path, 'wb') as f:
                f.write(zip_ref.read(waveform_file))

        print(f"[SUCCESS] 处理完成: {ila_path.name} -> {extracted_path.name}")
        return True

    except Exception as e:
        print(f"[ERROR] 处理文件 {ila_path} 时出错: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="处理FPGA导出的ILA信号文件，提取并更名waveform.csv"
    )
    parser.add_argument(
        "input_dir",
        nargs='?',
        help="输入目录，包含.ila文件（默认使用代码中配置的INPUT_DIR）"
    )
    parser.add_argument(
        "-o", "--output_dir",
        help="输出目录，用于保存提取后的CSV文件（默认与输入目录相同，或使用代码中配置的OUTPUT_DIR）"
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="递归处理子目录（默认使用代码中配置的RECURSIVE）"
    )
    parser.add_argument(
        "-k", "--keep",
        action="store_true",
        help="保留原始ILA文件（默认使用代码中配置的KEEP_ORIGINAL）"
    )
    parser.add_argument(
        "-d", "--delete",
        action="store_true",
        help="处理后删除原始ILA文件（默认使用代码中配置的DELETE_ORIGINAL）"
    )

    args = parser.parse_args()

    # 使用命令行参数或代码中配置的参数
    input_path = Path(args.input_dir) if args.input_dir else Path(INPUT_DIR)
    output_path = Path(args.output_dir) if args.output_dir else (
        Path(OUTPUT_DIR) if OUTPUT_DIR else input_path
    )
    recursive = args.recursive if args.recursive is not None else RECURSIVE
    keep_original = args.keep if args.keep is not None else KEEP_ORIGINAL
    delete_original = args.delete if args.delete is not None else DELETE_ORIGINAL

    # 检查输入目录是否存在
    if not input_path.exists():
        print(f"[ERROR] 输入目录不存在: {input_path}")
        return

    # 查找所有.ila文件
    if recursive:
        ila_files = list(input_path.rglob("*.ila"))
    else:
        ila_files = list(input_path.glob("*.ila"))

    if not ila_files:
        print(f"[INFO] 未找到.ila文件: {input_path}")
        return

    print(f"[INFO] 找到 {len(ila_files)} 个.ila文件")

    # 处理所有ILA文件
    success_count = 0
    failed_count = 0

    for ila_file in tqdm(ila_files, desc="处理进度"):
        success = process_ila_file(ila_file, output_path, keep_original and not delete_original)
        if success:
            success_count += 1
            # 如果需要删除原始文件
            if delete_original:
                try:
                    ila_file.unlink()
                except Exception as e:
                    print(f"[ERROR] 无法删除文件 {ila_file}: {str(e)}")
        else:
            failed_count += 1

    print(f"\n[INFO] 处理完成: 成功 {success_count} 个, 失败 {failed_count} 个")
    print(f"[INFO] 输出目录: {output_path}")


if __name__ == "__main__":
    main()
