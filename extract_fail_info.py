#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
import re

def extract_fail_info(txt_file, csv_file):
    # 打开结果文件
    with open(txt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fail_records = []
    i = 0
    line_count = len(lines)

    while i < line_count:
        line = lines[i].strip()

        # 查找包含 Check FAIL 的行
        if 'Check' in line and 'FAIL' in line:
            # 提取测试项信息
            parts = line.split()
            check_index = parts.index('Check')
            test_item = ' '.join(parts[:check_index])

            # 跳过可能的空行，查找表头
            j = i + 1
            while j < line_count and lines[j].strip() == '':
                j += 1

            # 检查是否找到表头
            if j < line_count and 'rate' in lines[j].strip() and 'wifi_format' in lines[j].strip():
                j += 1  # 跳过表头
                # 读取数据行
                has_data = False
                while j < line_count and lines[j].strip() != '':
                    data_line = lines[j].strip()
                    data_parts = re.split(r'\s+', data_line)
                    if len(data_parts) >= 7:
                        rate = data_parts[1]
                        wifi_format = data_parts[2]
                        tx_power = data_parts[3]
                        fec_coding = data_parts[4]
                        rf_chan = data_parts[5]
                        short_gi = data_parts[6] if len(data_parts) > 6 else ''

                        # 直接添加记录，不进行去重
                        record = {
                            'test_item': test_item,
                            'rate': rate,
                            'wifi_format': wifi_format,
                            'tx_power_set(dBm)': tx_power,
                            'fec_coding': fec_coding,
                            'rf_chan': rf_chan,
                            'short_gi': short_gi
                        }
                        fail_records.append(record)
                        has_data = True
                    j += 1
                i = j  # 更新 i 到数据结束的位置
                if not has_data:
                    # 有表头但无数据的 FAIL 记录
                    record = {
                        'test_item': test_item,
                        'rate': '',
                        'wifi_format': '',
                        'tx_power_set(dBm)': '',
                        'fec_coding': '',
                        'rf_chan': '',
                        'short_gi': ''
                    }
                    fail_records.append(record)
            else:
                # 没有详细信息的 FAIL 记录
                record = {
                    'test_item': test_item,
                    'rate': '',
                    'wifi_format': '',
                    'tx_power_set(dBm)': '',
                    'fec_coding': '',
                    'rf_chan': '',
                    'short_gi': ''
                }
                fail_records.append(record)
                i += 1
        else:
            i += 1

    # 写入 CSV 文件
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['test_item', 'rate', 'wifi_format', 'tx_power_set(dBm)', 'fec_coding', 'rf_chan', 'short_gi']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(fail_records)

    print(f"成功提取 {len(fail_records)} 条 FAIL 记录到 {csv_file}")

if __name__ == "__main__":
    txt_file = r"D:\users\gxu\e22_tx\spec_mask\resulttx_result_2026_03_18_1411.txt"
    csv_file = r"D:\users\gxu\e22_tx\spec_mask\fail_info_2026_03_18_1411.csv"
    extract_fail_info(txt_file, csv_file)
