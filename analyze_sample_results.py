#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析示例结果文件的结构，了解输出格式
"""

import pandas as pd
import os

def analyze_sample_files():
    sample_dir = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx\20260407\vht_ht_hesu\rls4_wifi7_hesu_evm_comparison"

    # 列出目录中的所有文件
    print("Directory contents:")
    for filename in os.listdir(sample_dir):
        file_path = os.path.join(sample_dir, filename)
        print(f"  {filename} ({os.path.getsize(file_path)} bytes)")

    # 分析summary文件
    print("\n=== Analyzing summary files ===")
    for filename in os.listdir(sample_dir):
        if filename.endswith("_summary.xlsx"):
            file_path = os.path.join(sample_dir, filename)
            print(f"\nReading {filename}")

            try:
                df = pd.read_excel(file_path)
                print(f"Number of rows: {len(df)}")
                print(f"Number of columns: {len(df.columns)}")
                print(f"Columns: {list(df.columns)}")

                if len(df) > 0:
                    print(f"\nFirst 5 rows:")
                    print(df.head())
            except Exception as e:
                print(f"Error reading {filename}: {e}")

    # 分析detailed文件
    print("\n=== Analyzing detailed files ===")
    for filename in os.listdir(sample_dir):
        if filename.endswith("_detailed.xlsx"):
            file_path = os.path.join(sample_dir, filename)
            print(f"\nReading {filename}")

            try:
                df = pd.read_excel(file_path)
                print(f"Number of rows: {len(df)}")
                print(f"Number of columns: {len(df.columns)}")
                print(f"Columns: {list(df.columns)}")

                if len(df) > 0:
                    print(f"\nFirst 5 rows:")
                    print(df.head())
            except Exception as e:
                print(f"Error reading {filename}: {e}")

    # 分析报告文件
    report_file = os.path.join(sample_dir, "evm_comparison_report.html")
    if os.path.exists(report_file):
        print(f"\n=== Analyzing {os.path.basename(report_file)} ===")
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"File size: {len(content)} characters")
            print(f"First 200 characters:\n{content[:200]}")

if __name__ == "__main__":
    analyze_sample_files()