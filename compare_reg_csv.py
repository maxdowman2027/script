#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
import os
import pandas as pd
import sys


def get_register_value(row):
    """获取寄存器的实际值，如果Modify为空或不存在则使用Default值"""
    if 'Modify' in row.index and pd.notna(row['Modify']):
        modify_value = str(row['Modify']).strip()
        if modify_value:
            return modify_value
    # 如果Modify不存在或为空，则返回Default值
    return str(row['Default']).strip() if pd.notna(row['Default']) else ''


def compare_csv_files(file1, file2, filename, reg_prefix=""):
    """比较两个CSV文件的差异"""
    print(f"\n{'='*80}")
    print(f"比较文件: {filename}")
    print('='*80)

    try:
        # 读取CSV文件
        df1 = pd.read_csv(file1, encoding='utf-8-sig', engine='python')
        df2 = pd.read_csv(file2, encoding='utf-8-sig', engine='python')

        # 检查是否包含必要的列 (Modify列可选)
        required_columns = ['Signal', 'Default']
        for col in required_columns:
            if col not in df1.columns or col not in df2.columns:
                print(f"错误: 文件缺少必要的列 '{col}'")
                return

        # 转换Signal列为字符串
        df1['Signal'] = df1['Signal'].astype(str)
        df2['Signal'] = df2['Signal'].astype(str)

        # 创建寄存器值的映射
        reg_map1 = {}
        for _, row in df1.iterrows():
            reg = row['Signal']
            value = get_register_value(row)
            reg_map1[reg] = value

        reg_map2 = {}
        for _, row in df2.iterrows():
            reg = row['Signal']
            value = get_register_value(row)
            reg_map2[reg] = value

        # 应用寄存器前缀过滤
        if reg_prefix:
            filtered_map1 = {k: v for k, v in reg_map1.items() if k.startswith(reg_prefix) or pd.isna(k)}
            filtered_map2 = {k: v for k, v in reg_map2.items() if k.startswith(reg_prefix) or pd.isna(k)}
        else:
            filtered_map1 = reg_map1
            filtered_map2 = reg_map2

        # 找到所有唯一的寄存器
        all_registers = set(filtered_map1.keys()).union(set(filtered_map2.keys()))

        # 分类寄存器
        common_registers = set(filtered_map1.keys()).intersection(set(filtered_map2.keys()))
        new_registers = set(filtered_map2.keys()) - set(filtered_map1.keys())
        removed_registers = set(filtered_map1.keys()) - set(filtered_map2.keys())

        # 比较相同寄存器的值差异
        different_registers = []
        for reg in common_registers:
            val1 = filtered_map1[reg]
            val2 = filtered_map2[reg]
            if val1 != val2:
                different_registers.append((reg, val1, val2))

        # 输出结果
        if new_registers:
            print(f"\n新增寄存器 ({len(new_registers)}个):")
            for reg in sorted(new_registers):
                print(f"  + {reg} = {filtered_map2[reg]}")

        if removed_registers:
            print(f"\n删减寄存器 ({len(removed_registers)}个):")
            for reg in sorted(removed_registers):
                print(f"  - {reg} = {filtered_map1[reg]}")

        if different_registers:
            print(f"\n值不同的信号 ({len(different_registers)}个):")
            print(f"  {'信号名称':<30} {'旧值':<15} {'新值':<15}")
            print(f"  {'-'*30} {'-'*15} {'-'*15}")
            for reg, val1, val2 in sorted(different_registers):
                print(f"  {reg:<30} {val1:<15} {val2:<15}")

        if not new_registers and not removed_registers and not different_registers:
            if reg_prefix:
                print(f"\n没有找到以 '{reg_prefix}' 为前缀的信号差异")
            else:
                print("\n两个文件的信号完全相同")

    except Exception as e:
        print(f"错误: 比较文件时出错: {e}")


def main():
    if len(sys.argv) < 3:
        print("使用方法: python compare_reg_csv.py <旧版本文件夹路径> <新版本文件夹路径> [输出文件名] [寄存器前缀]")
        print("示例1: 比较所有寄存器")
        print("       python compare_reg_csv.py D:\\reg\\WIFI7_old D:\\reg\\wifi7_new output.txt")
        print("示例2: 只比较reg_前缀的寄存器")
        print("       python compare_reg_csv.py D:\\reg\\WIFI7_old D:\\reg\\wifi7_new output.txt reg_")
        return

    old_dir = sys.argv[1]
    new_dir = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else "reg_diff.txt"
    reg_prefix = sys.argv[4] if len(sys.argv) > 4 else ""

    # 打开输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        # 重定向print函数
        original_print = __builtins__.print
        def new_print(*args, **kwargs):
            original_print(*args, **kwargs)
            original_print(*args, file=f, **kwargs)

        __builtins__.print = new_print

        # 检查文件夹是否存在
        if not os.path.isdir(old_dir):
            print(f"错误: 旧版本文件夹不存在: {old_dir}")
            return

        if not os.path.isdir(new_dir):
            print(f"错误: 新版本文件夹不存在: {new_dir}")
            return

        # 获取文件夹中的CSV文件
        old_files = [f for f in os.listdir(old_dir) if f.endswith('.csv')]
        new_files = [f for f in os.listdir(new_dir) if f.endswith('.csv')]

        # 找到共同的CSV文件
        common_files = set(old_files).intersection(set(new_files))

        if not common_files:
            print("错误: 两个文件夹中没有共同的CSV文件")
            return

        if reg_prefix:
            print(f"找到 {len(common_files)} 个共同的CSV文件进行比较")
            print(f"只比较以 '{reg_prefix}' 为前缀的寄存器")
        else:
            print(f"找到 {len(common_files)} 个共同的CSV文件进行比较")

        # 比较每个共同的CSV文件
        for filename in sorted(common_files):
            old_file = os.path.join(old_dir, filename)
            new_file = os.path.join(new_dir, filename)

            if os.path.isfile(old_file) and os.path.isfile(new_file):
                compare_csv_files(old_file, new_file, filename, reg_prefix)

        # 检查是否有新增或删减的文件
        new_files_only = set(new_files) - set(old_files)
        if new_files_only:
            print(f"\n{'='*80}")
            print(f"新增文件 ({len(new_files_only)}个):")
            for filename in sorted(new_files_only):
                print(f"  + {filename}")

        old_files_only = set(old_files) - set(new_files)
        if old_files_only:
            print(f"\n{'='*80}")
            print(f"删减文件 ({len(old_files_only)}个):")
            for filename in sorted(old_files_only):
                print(f"  - {filename}")

        print(f"\n{'='*80}")
        print(f"差异已保存到: {os.path.abspath(output_file)}")


if __name__ == "__main__":
    main()
