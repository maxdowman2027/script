#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
View the comparison results from the generated Excel file.
"""

import pandas as pd

def view_comparison_results(file_path):
    """Read and display comparison results."""
    xls = pd.ExcelFile(file_path)

    print("Sheets in comparison file:")
    for sheet in xls.sheet_names:
        print(f"  - {sheet}")

    for sheet_name in xls.sheet_names:
        print(f"\n\n=== Sheet: {sheet_name} ===")

        try:
            df = pd.read_excel(xls, sheet_name)
            print(f"Number of rows: {len(df)}")

            if 'evm_diff' in df.columns:
                avg_diff = df['evm_diff'].mean()
                max_diff = df['evm_diff'].max()
                min_diff = df['evm_diff'].min()

                print(f"EVM Diff Statistics:")
                print(f"  Average difference: {avg_diff:.2f}")
                print(f"  Maximum difference: {max_diff:.2f}")
                print(f"  Minimum difference: {min_diff:.2f}")

                # Show rows with largest differences
                print("\nTop 10 largest EVM differences:")
                sorted_df = df.sort_values(by='evm_diff', ascending=False)
                for _, row in sorted_df.head(10).iterrows():
                    print(f"  {row['wifi_format']}, {row['rate']}, {row['tx_power_set(dBm)']}")
                    print(f"    WiFi7: {row['evm_wifi7']:.2f}, RLS4: {row['evm_rls4']:.2f}, Diff: {row['evm_diff']:.2f}")

        except Exception as e:
            print(f"Error reading sheet {sheet_name}: {e}")

if __name__ == "__main__":
    file_path = "wifi7_rls4_evm_comparison.xlsx"
    view_comparison_results(file_path)