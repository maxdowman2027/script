
import pandas as pd

def main():
    old_file = r'D:\chip_test\dev\chip_tx\eagletest\py_script_fpga_tx_wifi7\Log\wifi_tx\20260407\vht_ht_old\merged_tx_result.xlsx'
    new_file = r'D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx\20260407\vht_ht_2\merged_tx_result.xlsx'

    # 读取旧文件的列名
    try:
        old_xls = pd.ExcelFile(old_file)
        old_sheets = old_xls.sheet_names
        print('旧文件 Sheet 列表:', old_sheets)
        for sheet in old_sheets:
            old_df = pd.read_excel(old_xls, sheet_name=sheet)
            print(f'旧文件 {sheet} 列名:', list(old_df.columns))
            break  # 只查看第一个 Sheet 的列名
    except Exception as e:
        print(f'读取旧文件失败: {e}')

    # 读取新文件的列名
    try:
        new_xls = pd.ExcelFile(new_file)
        new_sheets = new_xls.sheet_names
        print('\n新文件 Sheet 列表:', new_sheets)
        for sheet in new_sheets:
            new_df = pd.read_excel(new_xls, sheet_name=sheet)
            print(f'新文件 {sheet} 列名:', list(new_df.columns))
            break  # 只查看第一个 Sheet 的列名
    except Exception as e:
        print(f'读取新文件失败: {e}')

if __name__ == "__main__":
    main()
