#!/usr/bin/env python3
import csv

def compare_data():
    # 读取原始数据
    original_data = []
    with open(r"D:\test_data\wifi7\260327_hesu_nss2\waveform.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i > 856 and i < 920:
                original_data.append({
                    'row': i,
                    'dac_i_ch0': row['dac_i_ch0[11:0]'],
                    'dac_q_ch0': row['dac_q_ch0[11:0]'],
                    'dac_vliad_ch0': row['dac_vliad_ch0[0:0]'],
                    'dac_i_ch1': row['dac_i_ch1[11:0]'],
                    'dac_q_ch1': row['dac_q_ch1[11:0]']
                })

    # 读取转换后的数据
    converted_data = []
    with open(r"D:\test_data\wifi7\260327_hesu_nss2\waveform_decimal.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i > 856 and i < 920:
                converted_data.append({
                    'row': i,
                    'dac_i_ch0': int(row['dac_i_ch0[11:0]']),
                    'dac_q_ch0': int(row['dac_q_ch0[11:0]']),
                    'dac_vliad_ch0': int(row['dac_vliad_ch0[0:0]']),
                    'dac_i_ch1': int(row['dac_i_ch1[11:0]']),
                    'dac_q_ch1': int(row['dac_q_ch1[11:0]'])
                })

    # 比较原始数据和转换后的数据
    print("行  | 原始dac_i_ch0 | 转换后dac_i_ch0 | 原始dac_q_ch0 | 转换后dac_q_ch0 | 原始dac_vliad_ch0 | 转换后dac_vliad_ch0 | 原始dac_i_ch1 | 转换后dac_i_ch1 | 原始dac_q_ch1 | 转换后dac_q_ch1")
    print("----|---------------|----------------|---------------|----------------|-------------------|--------------------|---------------|----------------|---------------|----------------")

    for orig, conv in zip(original_data, converted_data):
        print(f"{orig['row']:4} | {orig['dac_i_ch0']:13} | {conv['dac_i_ch0']:14} | {orig['dac_q_ch0']:13} | {conv['dac_q_ch0']:14} | {orig['dac_vliad_ch0']:17} | {conv['dac_vliad_ch0']:20} | {orig['dac_i_ch1']:13} | {conv['dac_i_ch1']:14} | {orig['dac_q_ch1']:13} | {conv['dac_q_ch1']:14}")

if __name__ == "__main__":
    compare_data()
