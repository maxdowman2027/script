import pandas as pd

def check_columns():
    file_path = "D:/chip_test/dev/xian_test/Xian-Esp-Test-Scripts/py_script_fpga_tx_wifi7/Log/wifi_tx_rls4/no_he/merged_result.xlsx"

    try:
        # 读取第一个Sheet
        sheet1 = "channel11_BCC"
        df1 = pd.read_excel(file_path, sheet_name=sheet1)
        print(f"{sheet1}列顺序:")
        for i, col in enumerate(df1.columns):
            print(f"{i+1}. {col}")

        print("\n" + "-"*50 + "\n")

        # 读取第二个Sheet
        sheet2 = "channel5180_LDPC"
        df2 = pd.read_excel(file_path, sheet_name=sheet2)
        print(f"{sheet2}列顺序:")
        for i, col in enumerate(df2.columns):
            print(f"{i+1}. {col}")

    except Exception as e:
        print(f"读取文件失败: {e}")

if __name__ == "__main__":
    check_columns()