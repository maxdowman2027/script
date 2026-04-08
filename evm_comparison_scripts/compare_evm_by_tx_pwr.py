import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import os

def main():
    # File paths
    old_file = r"D:\chip_test\dev\chip_tx\eagletest\py_script_fpga_tx_wifi7\Log\wifi_tx\20260407\wifi7_fpga_old_merged_tx_result.xlsx"
    new_file = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx\20260407\vht_ht\wifi7_fpga_new_merged_tx_result.xlsx"

    # Output directory and file
    output_dir = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx\20260407\vht_ht"
    output_pdf = os.path.join(output_dir, "evm_comparison_by_tx_pwr.pdf")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Read Excel files
        print("Reading old version data...")
        old_xls = pd.ExcelFile(old_file)
        old_sheets = old_xls.sheet_names

        print("Reading new version data...")
        new_xls = pd.ExcelFile(new_file)
        new_sheets = new_xls.sheet_names

        # Create PDF file
        print("Creating PDF file...")
        with PdfPages(output_pdf) as pdf:
            # Iterate over each sheet for comparison
            for old_sheet in old_sheets:
                print(f"Processing Sheet: {old_sheet}")

                # Find matching new sheet
                matched_sheet = find_matching_sheet(old_sheet, new_sheets)
                if not matched_sheet:
                    print(f"No matching new sheet found for old sheet {old_sheet}")
                    continue

                # Read data
                old_df = pd.read_excel(old_xls, sheet_name=old_sheet)
                new_df = pd.read_excel(new_xls, sheet_name=matched_sheet)

                # Ensure required columns exist
                required_columns = ['rate', 'tx_power_set(dBm)', 'evm', 'wifi_format']
                missing_cols = []
                for col in required_columns:
                    if col not in old_df.columns or col not in new_df.columns:
                        missing_cols.append(col)
                if missing_cols:
                    print(f"Warning: Sheet {old_sheet} missing columns: {', '.join(missing_cols)}")
                    continue

                # Plot by wifi_format and rate
                wifi_formats = old_df['wifi_format'].unique()
                for wifi_format in wifi_formats:
                    print(f"Processing WiFi format: {wifi_format}")

                    # Filter data
                    old_sub = old_df[old_df['wifi_format'] == wifi_format]
                    new_sub = new_df[new_df['wifi_format'] == wifi_format]

                    rates = old_sub['rate'].unique()
                    for rate in rates:
                        print(f"Processing Rate: {rate}")

                        # 进一步筛选数据
                        old_rate_sub = old_sub[old_sub['rate'] == rate].sort_values('tx_power_set(dBm)')
                        new_rate_sub = new_sub[new_sub['rate'] == rate].sort_values('tx_power_set(dBm)')

                        # 创建图表
                        fig, ax = plt.subplots(figsize=(12, 8))

                        # Plot old version data
                        if not old_rate_sub.empty:
                            ax.plot(old_rate_sub['tx_power_set(dBm)'], old_rate_sub['evm'],
                                    marker='o', label=f'Old Version - {wifi_format}/{rate}')

                        # Plot new version data
                        if not new_rate_sub.empty:
                            ax.plot(new_rate_sub['tx_power_set(dBm)'], new_rate_sub['evm'],
                                    marker='s', label=f'New Version - {wifi_format}/{rate}')

                        # 设置图表属性
                        ax.set_title(f'EVM vs TX Power - {old_sheet} ({wifi_format}/{rate})', fontsize=14)
                        ax.set_xlabel('TX Power (dBm)', fontsize=12)
                        ax.set_ylabel('EVM (dB)', fontsize=12)
                        ax.grid(True, linestyle='--', alpha=0.7)
                        ax.legend(loc='best', fontsize=10)

                        # 调整布局
                        plt.tight_layout()

                        # 保存到PDF
                        pdf.savefig(fig)
                        plt.close()

        print(f"PDF file saved successfully to: {output_pdf}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        print(traceback.format_exc())

def find_matching_sheet(old_sheet, new_sheets):
    """
    找到与旧版本Sheet匹配的新版本Sheet
    """
    # 尝试直接匹配
    if old_sheet in new_sheets:
        return old_sheet

    # 尝试去掉可能的前缀或后缀
    old_sheet_lower = old_sheet.lower()
    for new_sheet in new_sheets:
        new_sheet_lower = new_sheet.lower()
        if old_sheet_lower in new_sheet_lower or new_sheet_lower in old_sheet_lower:
            return new_sheet

    # 尝试模糊匹配
    for new_sheet in new_sheets:
        if 'channel11' in old_sheet and 'channel11' in new_sheet:
            return new_sheet
        if 'channel5180' in old_sheet and 'channel5180' in new_sheet:
            return new_sheet

    return None

if __name__ == "__main__":
    main()
