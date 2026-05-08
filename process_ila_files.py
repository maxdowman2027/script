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
import pandas as pd
import sys

# ===========================================
# 配置参数 - 可根据需要修改
# ===========================================
# 输入目录：包含.ila文件的目录
INPUT_DIR = r"D:\test_data\temp"

# 输出目录：用于保存提取后的CSV文件（默认与输入目录相同）
# 如果需要保存到其他目录，请修改此处
OUTPUT_DIR = None  # 设为None表示与输入目录相同

# 是否递归处理子目录
RECURSIVE = False

# 是否保留原始ILA文件（处理后不删除）
KEEP_ORIGINAL = True

# 是否处理后删除原始ILA文件
DELETE_ORIGINAL = False

# 提取后的CSV保留列（None表示保留所有列）
# 示例：["Time", "sample_i", "sample_q"]
KEEP_COLUMNS = ["dac_i_ch0[11:0]" ,"dac_q_ch0[11:0]"]

# 提取后的CSV列重命名映射（None表示不重命名）
# 示例：{"sample_i": "i_data", "sample_q": "q_data"}
RENAME_COLUMNS =  ["dac_i_ch0" ,"dac_q_ch0"]

# ===========================================
# 核心处理函数
# ===========================================
RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"


def colorize_status_message(message: str) -> str:
    """Colorize log line by status tag."""
    if message.startswith("[ERROR]"):
        return f"{RED}{message}{RESET}"
    if message.startswith("[SUCCESS]"):
        return f"{GREEN}{message}{RESET}"
    return message


def log(message: str):
    """
    Print message with status color.
    Colors are enabled only for terminal output; redirected output stays plain text.
    """
    if sys.stdout and sys.stdout.isatty():
        print(colorize_status_message(message))
    else:
        print(message)


def process_ila_file(
    ila_path: Path,
    output_dir: Path,
    keep_original: bool = True,
    keep_columns=None,
    rename_columns=None,
) -> bool:
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
            log(f"[ERROR] 文件不存在: {ila_path}")
            return False

        # 检查是否是ZIP压缩包
        if not zipfile.is_zipfile(str(ila_path)):
            log(f"[ERROR] 不是有效的ZIP压缩包: {ila_path}")
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

        # 可选：只保留指定列，并可选重命名列
        if keep_columns or rename_columns:
            df = pd.read_csv(extracted_path)

            if keep_columns:
                missing_cols = [c for c in keep_columns if c not in df.columns]
                if missing_cols:
                    log(
                        f"[WARNING] 文件 {ila_path.name} 缺少列: {missing_cols}，"
                        "将仅保留存在的列"
                    )
                valid_keep_cols = [c for c in keep_columns if c in df.columns]
                if not valid_keep_cols:
                    log(
                        f"[ERROR] 文件 {ila_path.name} 不包含任何指定保留列，处理失败"
                    )
                    return False
                df = df[valid_keep_cols]

            if rename_columns:
                if not isinstance(rename_columns, dict):
                    log(
                        f"[ERROR] 文件 {ila_path.name} 的重命名配置格式无效，"
                        "应为字典映射"
                    )
                    return False
                valid_rename_map = {k: v for k, v in rename_columns.items() if k in df.columns}
                invalid_rename_cols = [k for k in rename_columns.keys() if k not in df.columns]
                if invalid_rename_cols:
                    log(
                        f"[WARNING] 文件 {ila_path.name} 中重命名源列不存在: {invalid_rename_cols}"
                    )
                if valid_rename_map:
                    df = df.rename(columns=valid_rename_map)

            df.to_csv(extracted_path, index=False)

        log(f"[SUCCESS] 处理完成: {ila_path.name} -> {extracted_path.name}")
        return True

    except Exception as e:
        log(f"[ERROR] 处理文件 {ila_path} 时出错: {str(e)}")
        return False


def normalize_keep_columns(value):
    """Normalize keep columns to list[str] or None."""
    if value is None:
        return None
    if isinstance(value, str):
        cols = [c.strip() for c in value.split(",") if c.strip()]
        return cols if cols else None
    if isinstance(value, (list, tuple)):
        cols = [str(c).strip() for c in value if str(c).strip()]
        return cols if cols else None
    return None


def normalize_rename_columns(value, keep_columns=None):
    """
    Normalize rename columns to dict[str, str] or None.
    Supported input:
      1) dict: {"old":"new"}
      2) string: "old1:new1,old2:new2"
      3) list/tuple:
         - ["old1:new1", "old2:new2"]
         - [("old1","new1"), ("old2","new2")]
         - ["new1", "new2"]  # when keep_columns is provided, zip map
    """
    if value is None:
        return None

    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            ks = str(k).strip()
            vs = str(v).strip()
            if ks and vs:
                out[ks] = vs
        return out if out else None

    # string mode: old:new pairs
    if isinstance(value, str):
        out = {}
        for pair in value.split(","):
            pair = pair.strip()
            if not pair:
                continue
            if ":" not in pair:
                return None
            old_name, new_name = pair.split(":", 1)
            old_name = old_name.strip()
            new_name = new_name.strip()
            if not old_name or not new_name:
                return None
            out[old_name] = new_name
        return out if out else None

    if isinstance(value, (list, tuple)):
        # 如果是 new-name 列表，且 keep_columns 等长，则按顺序映射
        if keep_columns and all(
            isinstance(x, str) and ":" not in x for x in value
        ) and len(value) == len(keep_columns):
            return {
                str(old).strip(): str(new).strip()
                for old, new in zip(keep_columns, value)
                if str(old).strip() and str(new).strip()
            }

        out = {}
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                old_name = str(item[0]).strip()
                new_name = str(item[1]).strip()
                if old_name and new_name:
                    out[old_name] = new_name
                continue
            if isinstance(item, str) and ":" in item:
                old_name, new_name = item.split(":", 1)
                old_name = old_name.strip()
                new_name = new_name.strip()
                if old_name and new_name:
                    out[old_name] = new_name
                continue
        return out if out else None

    return None


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
    parser.add_argument(
        "--keep_columns",
        help="提取后CSV仅保留的列，逗号分隔，例如: \"Time,sample_i,sample_q\""
    )
    parser.add_argument(
        "--rename_columns",
        help="提取后CSV列重命名映射，逗号分隔，格式 old:new，例如: \"sample_i:i_data,sample_q:q_data\""
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

    keep_columns = normalize_keep_columns(KEEP_COLUMNS)
    if args.keep_columns:
        keep_columns = normalize_keep_columns(args.keep_columns)

    rename_columns = normalize_rename_columns(RENAME_COLUMNS, keep_columns)
    if args.rename_columns:
        rename_columns = normalize_rename_columns(args.rename_columns, keep_columns)
        if rename_columns is None:
            log("[ERROR] --rename_columns 参数格式错误，请使用 old:new,old2:new2")
            return

    # 检查输入目录是否存在
    if not input_path.exists():
        log(f"[ERROR] 输入目录不存在: {input_path}")
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
        success = process_ila_file(
            ila_file,
            output_path,
            keep_original and not delete_original,
            keep_columns=keep_columns,
            rename_columns=rename_columns,
        )
        if success:
            success_count += 1
            # 如果需要删除原始文件
            if delete_original:
                try:
                    ila_file.unlink()
                except Exception as e:
                    log(f"[ERROR] 无法删除文件 {ila_file}: {str(e)}")
        else:
            failed_count += 1

    print(f"\n[INFO] 处理完成: 成功 {success_count} 个, 失败 {failed_count} 个")
    print(f"[INFO] 输出目录: {output_path}")


if __name__ == "__main__":
    main()
