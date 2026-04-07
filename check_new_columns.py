#!/usr/bin/env python3
import csv

def check_new_csv_columns():
    csv_file = r"D:\test_data\wifi7\260327_hesu_nss2\2462_hesu_mcs0_bcc_nss2.csv"

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            print("列名数量:", len(headers))
            print("列名列表:")
            for i, header in enumerate(headers):
                print(f"{i+1}: '{header}'")

        # 检查是否包含预期的列
        expected_columns = ['dac_i_ch0[11:0]', 'dac_q_ch0[11:0]', 'dac_i_ch1[11:0]', 'dac_q_ch1[11:0]']
        for col in expected_columns:
            found = any(col in header for header in headers)
            print(f"\n列 '{col}' 是否包含在文件中: {found}")
            if found:
                for header in headers:
                    if col in header:
                        print(f"  实际列名: '{header}'")

        return True

    except Exception as e:
        print(f"错误: {e}")
        return False

if __name__ == "__main__":
    check_new_csv_columns()
