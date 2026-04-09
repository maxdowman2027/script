#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
寄存器比较脚本
比较WIFI7版本和RLS4版本的寄存器文件差异
支持的文件类型: phy_common_reg2csv.csv, phy_txbf_reg2csv.csv, phy_txdfe_reg_reg2csv.csv, phy_txfreq_reg2csv.csv
"""

import pandas as pd
import os
import sys

def read_register_file(file_path):
    """
    读取寄存器CSV文件并解析
    """
    try:
        df = pd.read_csv(file_path)
        print(f"成功读取文件: {file_path}")
        return df
    except Exception as e:
        print(f"读取文件失败: {file_path}")
        print(f"错误信息: {e}")
        return None

def extract_register_info(df):
    """
    从DataFrame中提取寄存器信息
    """
    registers = {}

    for index, row in df.iterrows():
        signal = row.get('Signal', None)
        default = row.get('Default', None)
        modify = row.get('Modify', None)

        if signal:
            # 确定寄存器的实际值
            # 如果有Modify值，则使用Modify值，否则使用Default值
            if pd.notna(modify) and str(modify).strip() != '':
                value = str(modify).strip()
            elif pd.notna(default) and str(default).strip() != '':
                value = str(default).strip()
            else:
                value = None

            registers[signal] = {
                'default': str(default).strip() if pd.notna(default) else None,
                'modify': str(modify).strip() if pd.notna(modify) else None,
                'actual': value
            }

    return registers

def compare_registers(version1_regs, version2_regs, version1_name, version2_name):
    """
    比较两个版本的寄存器信息
    """
    # 获取所有寄存器名称
    all_signals = set(version1_regs.keys()).union(set(version2_regs.keys()))

    # 分类寄存器
    common_signals = set(version1_regs.keys()).intersection(set(version2_regs.keys()))
    version1_only_signals = set(version1_regs.keys()) - set(version2_regs.keys())
    version2_only_signals = set(version2_regs.keys()) - set(version1_regs.keys())

    # 查找值不同的寄存器
    differing_signals = []
    for signal in common_signals:
        v1_actual = version1_regs[signal]['actual']
        v2_actual = version2_regs[signal]['actual']

        if v1_actual != v2_actual:
            differing_signals.append(signal)

    return {
        'common_signals': common_signals,
        'version1_only_signals': version1_only_signals,
        'version2_only_signals': version2_only_signals,
        'differing_signals': differing_signals
    }

def generate_comparison_report(comparison_result, version1_regs, version2_regs, version1_name, version2_name, filename):
    """
    生成比较报告
    """
    output_file = f"register_comparison_report_{filename.replace('.csv', '')}.txt"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"========== {filename} 寄存器比较报告 ==========\n")
        f.write(f"{version1_name} 与 {version2_name} 版本比较\n")
        f.write("=" * 80 + "\n\n")

        # 1. 相同寄存器但值不同的情况
        if comparison_result['differing_signals']:
            f.write(f"1. 值不同的寄存器 ({len(comparison_result['differing_signals'])} 个):\n")
            f.write("-" * 60 + "\n")

            for signal in sorted(comparison_result['differing_signals']):
                v1 = version1_regs[signal]
                v2 = version2_regs[signal]

                f.write(f"\nSignal: {signal}\n")
                f.write(f"  {version1_name} - Default: {v1['default']}, Modify: {v1['modify']}, Actual: {v1['actual']}\n")
                f.write(f"  {version2_name} - Default: {v2['default']}, Modify: {v2['modify']}, Actual: {v2['actual']}\n")

        # 2. 仅在version1中存在的寄存器
        if comparison_result['version1_only_signals']:
            f.write(f"\n2. 仅在 {version1_name} 中存在的寄存器 ({len(comparison_result['version1_only_signals'])} 个):\n")
            f.write("-" * 60 + "\n")

            for signal in sorted(comparison_result['version1_only_signals']):
                reg = version1_regs[signal]
                f.write(f"\nSignal: {signal}\n")
                f.write(f"  Default: {reg['default']}, Modify: {reg['modify']}, Actual: {reg['actual']}\n")

        # 3. 仅在version2中存在的寄存器
        if comparison_result['version2_only_signals']:
            f.write(f"\n3. 仅在 {version2_name} 中存在的寄存器 ({len(comparison_result['version2_only_signals'])} 个):\n")
            f.write("-" * 60 + "\n")

            for signal in sorted(comparison_result['version2_only_signals']):
                reg = version2_regs[signal]
                f.write(f"\nSignal: {signal}\n")
                f.write(f"  Default: {reg['default']}, Modify: {reg['modify']}, Actual: {reg['actual']}\n")

        # 4. 统计信息
        f.write("\n" + "=" * 80 + "\n")
        f.write("统计信息:\n")
        f.write(f"- 总寄存器数: {len(comparison_result['common_signals'].union(comparison_result['version1_only_signals']).union(comparison_result['version2_only_signals']))}\n")
        f.write(f"- 相同寄存器数: {len(comparison_result['common_signals'])}\n")
        f.write(f"- 值不同的寄存器数: {len(comparison_result['differing_signals'])}\n")
        f.write(f"- 仅在 {version1_name} 中的寄存器数: {len(comparison_result['version1_only_signals'])}\n")
        f.write(f"- 仅在 {version2_name} 中的寄存器数: {len(comparison_result['version2_only_signals'])}\n")

    print(f"\n报告已生成: {output_file}")

def compare_register_files(version1_path, version2_path, version1_name, version2_name, filenames):
    """
    比较指定的寄存器文件
    """
    for filename in filenames:
        version1_file = os.path.join(version1_path, filename)
        version2_file = os.path.join(version2_path, filename)

        print(f"\n{'='*60}")
        print(f"比较文件: {filename}")
        print('='*60)

        # 读取文件
        df1 = read_register_file(version1_file)
        df2 = read_register_file(version2_file)

        if df1 is not None and df2 is not None:
            # 提取寄存器信息
            version1_regs = extract_register_info(df1)
            version2_regs = extract_register_info(df2)

            print(f"\n{version1_name} 寄存器数: {len(version1_regs)}")
            print(f"{version2_name} 寄存器数: {len(version2_regs)}")

            # 比较寄存器
            comparison_result = compare_registers(version1_regs, version2_regs, version1_name, version2_name)

            # 生成报告
            generate_comparison_report(comparison_result, version1_regs, version2_regs, version1_name, version2_name, filename)

            # 打印简要结果
            print(f"\n比较结果:")
            print(f"- 相同寄存器数: {len(comparison_result['common_signals'])}")
            print(f"- 值不同的寄存器数: {len(comparison_result['differing_signals'])}")
            print(f"- 仅在 {version1_name} 中的寄存器数: {len(comparison_result['version1_only_signals'])}")
            print(f"- 仅在 {version2_name} 中的寄存器数: {len(comparison_result['version2_only_signals'])}")
        else:
            print(f"无法比较文件: {filename}")

        print(f"\n{'='*60}")
        print()

def main():
    """
    主函数
    """
    # 配置路径
    version1_path = r"D:\reg\rls4"
    version2_path = r"D:\reg\wifi7_new"
    version1_name = "RLS4"
    version2_name = "WiFi7"

    # 要比较的寄存器文件
    filenames = [
        "phy_common_reg2csv.csv",
        "phy_txbf_reg2csv.csv",
        "phy_txdfe_reg_reg2csv.csv",
        "phy_txfreq_reg2csv.csv"
    ]

    print(f"比较 {version1_name} 版本 (路径: {version1_path}) 和 {version2_name} 版本 (路径: {version2_path})")
    print(f"要比较的文件: {filenames}")

    # 检查路径是否存在
    if not os.path.exists(version1_path):
        print(f"错误: 路径不存在: {version1_path}")
        return

    if not os.path.exists(version2_path):
        print(f"错误: 路径不存在: {version2_path}")
        return

    # 执行比较
    compare_register_files(version1_path, version2_path, version1_name, version2_name, filenames)

    print("\n比较完成!")

if __name__ == "__main__":
    main()
