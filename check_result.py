#!/usr/bin/env python3
import csv
import sys

def check_conversion():
    csv_file = r"D:\test_data\wifi7\260327_hesu_nss2\waveform_decimal.csv"

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data_found = False

            for i, row in enumerate(reader):
                if i > 2000:
                    break

                dac_i_ch0 = int(row['dac_i_ch0[11:0]'])
                dac_q_ch0 = int(row['dac_q_ch0[11:0]'])
                dac_vliad_ch0 = int(row['dac_vliad_ch0[0:0]'])
                dac_i_ch1 = int(row['dac_i_ch1[11:0]'])
                dac_q_ch1 = int(row['dac_q_ch1[11:0]'])

                if any([dac_i_ch0 != 0,
                        dac_q_ch0 != 0,
                        dac_vliad_ch0 != 0,
                        dac_i_ch1 != 0,
                        dac_q_ch1 != 0]):
                    print(f"行{i}: dac_i_ch0={dac_i_ch0}, dac_q_ch0={dac_q_ch0}, "
                          f"dac_vliad_ch0={dac_vliad_ch0}, dac_i_ch1={dac_i_ch1}, "
                          f"dac_q_ch1={dac_q_ch1}")
                    data_found = True

            if not data_found:
                print("在检查的范围内没有找到非零值的DAC数据")

            return True

    except Exception as e:
        print(f"错误: {e}")
        return False

if __name__ == "__main__":
    check_conversion()
