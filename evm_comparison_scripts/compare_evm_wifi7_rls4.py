#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare EVM results between WiFi7 FPGA and RLS4.0 versions.
"""

import pandas as pd
import os
import sys

def read_excel_file(file_path):
    """Read Excel file and return all sheets as dictionary of DataFrames."""
    xls = pd.ExcelFile(file_path)
    sheets = {}
    for sheet_name in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name)
            sheets[sheet_name] = df
            print(f"Successfully read sheet: {sheet_name}")
        except Exception as e:
            print(f"Error reading sheet {sheet_name}: {e}")
    return sheets

def analyze_dataframes(df1, df2, sheet_name):
    """Analyze and compare two dataframes."""
    print(f"\nAnalyzing sheet: {sheet_name}")

    # Find common columns
    common_columns = list(set(df1.columns) & set(df2.columns))
    print(f"Common columns: {common_columns}")

    # Check if required columns exist
    required_columns = ['wifi_format', 'rate', 'tx_power_set(dBm)', 'evm']
    missing_cols1 = [col for col in required_columns if col not in df1.columns]
    missing_cols2 = [col for col in required_columns if col not in df2.columns]

    if missing_cols1 or missing_cols2:
        print("Warning: Missing required columns")
        if missing_cols1:
            print(f"File1 missing: {missing_cols1}")
        if missing_cols2:
            print(f"File2 missing: {missing_cols2}")
        return None

    # Create a unique key for each row using the three parameters
    df1['key'] = df1.apply(lambda x: f"{x['wifi_format']}_{x['rate']}_{x['tx_power_set(dBm)']}", axis=1)
    df2['key'] = df2.apply(lambda x: f"{x['wifi_format']}_{x['rate']}_{x['tx_power_set(dBm)']}", axis=1)

    # Find common keys
    common_keys = set(df1['key']) & set(df2['key'])
    print(f"Number of common test cases: {len(common_keys)}")

    # Find unique keys in each file
    unique1 = set(df1['key']) - common_keys
    unique2 = set(df2['key']) - common_keys

    if unique1:
        print(f"Unique to File1: {len(unique1)} test cases")
    if unique2:
        print(f"Unique to File2: {len(unique2)} test cases")

    # Create comparison dataframe
    comparison_data = []

    for key in common_keys:
        row1 = df1[df1['key'] == key].iloc[0]
        row2 = df2[df2['key'] == key].iloc[0]

        # Calculate EVM difference
        evm_diff = abs(row1['evm'] - row2['evm'])

        comparison_data.append({
            'wifi_format': row1['wifi_format'],
            'rate': row1['rate'],
            'tx_power_set(dBm)': row1['tx_power_set(dBm)'],
            'evm_wifi7': row1['evm'],
            'evm_rls4': row2['evm'],
            'evm_diff': evm_diff
        })

    comparison_df = pd.DataFrame(comparison_data)

    return comparison_df

def save_comparison_results(comparison_dfs, output_file):
    """Save comparison results to Excel file."""
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        for sheet_name, df in comparison_dfs.items():
            if df is not None:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        # Add summary sheet
        summary_data = []
        for sheet_name, df in comparison_dfs.items():
            if df is not None:
                avg_diff = df['evm_diff'].mean()
                max_diff = df['evm_diff'].max()
                min_diff = df['evm_diff'].min()

                summary_data.append({
                    'sheet': sheet_name,
                    'test_cases': len(df),
                    'avg_evm_diff': round(avg_diff, 2),
                    'max_evm_diff': round(max_diff, 2),
                    'min_evm_diff': round(min_diff, 2)
                })

        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

    print(f"\nComparison results saved to: {output_file}")

def main():
    file1 = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx\20260407\vht_ht_hesu\merged_tx_result.xlsx"
    file2 = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx_rls4\vht_ht_hesu_compare\merged_tx_result.xlsx"

    print("Reading Excel files...")
    sheets1 = read_excel_file(file1)
    sheets2 = read_excel_file(file2)

    print("\nFile 1 sheets:", list(sheets1.keys()))
    print("File 2 sheets:", list(sheets2.keys()))

    # Compare sheets
    comparison_dfs = {}
    all_sheets = set(list(sheets1.keys()) + list(sheets2.keys()))

    for sheet_name in all_sheets:
        if sheet_name in sheets1 and sheet_name in sheets2:
            comparison_dfs[sheet_name] = analyze_dataframes(
                sheets1[sheet_name],
                sheets2[sheet_name],
                sheet_name
            )
        elif sheet_name in sheets1:
            print(f"\nSheet '{sheet_name}' exists only in File 1")
        else:
            print(f"\nSheet '{sheet_name}' exists only in File 2")

    # Save results
    output_file = "wifi7_rls4_evm_comparison.xlsx"
    save_comparison_results(comparison_dfs, output_file)

if __name__ == "__main__":
    main()