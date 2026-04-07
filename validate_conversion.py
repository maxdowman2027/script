#!/usr/bin/env python3
import csv

def validate_conversion():
    csv_file = r"D:\test_data\wifi7\260327_hesu_nss2\waveform_decimal.csv"

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            total_rows = 0
            valid_values = 0
            errors = 0

            for row in reader:
                total_rows += 1
                try:
                    # 检查所有需要转换的列
                    dac_i_ch0 = int(row['dac_i_ch0[11:0]'])
                    dac_q_ch0 = int(row['dac_q_ch0[11:0]'])
                    dac_vliad_ch0 = int(row['dac_vliad_ch0[0:0]'])
                    dac_i_ch1 = int(row['dac_i_ch1[11:0]'])
                    dac_q_ch1 = int(row['dac_q_ch1[11:0]'])

                    valid_values += 1
                except Exception as e:
                    errors += 1

            print(f"转换结果统计:")
            print(f"  总数据行数: {total_rows}")
            print(f"  有效值行数: {valid_values}")
            print(f"  错误行数: {errors}")

            # 检查是否有负数值（对于有符号位宽）
            with open(csv_file, 'r', encoding='utf-8') as f2:
                reader2 = csv.DictReader(f2)
                negative_values = 0
                for row in reader2:
                    dac_i_ch0 = int(row['dac_i_ch0[11:0]'])
                    dac_q_ch0 = int(row['dac_q_ch0[11:0]'])
                    dac_i_ch1 = int(row['dac_i_ch1[11:0]'])
                    dac_q_ch1 = int(row['dac_q_ch1[11:0]'])

                    if any(x < 0 for x in [dac_i_ch0, dac_q_ch0, dac_i_ch1, dac_q_ch1]):
                        negative_values += 1

            print(f"  包含负值的行数: {negative_values}")

            # 检查值的范围是否在12位有符号整数范围内
            valid_range_count = 0
            with open(csv_file, 'r', encoding='utf-8') as f3:
                reader3 = csv.DictReader(f3)
                for row in reader3:
                    try:
                        dac_i_ch0 = int(row['dac_i_ch0[11:0]'])
                        dac_q_ch0 = int(row['dac_q_ch0[11:0]'])
                        dac_i_ch1 = int(row['dac_i_ch1[11:0]'])
                        dac_q_ch1 = int(row['dac_q_ch1[11:0]'])

                        # 12位有符号数范围：-2048到2047
                        if all(-2048 <= x <= 2047 for x in [dac_i_ch0, dac_q_ch0, dac_i_ch1, dac_q_ch1]):
                            valid_range_count += 1
                    except:
                        pass

            print(f"  值在12位有符号范围的行数: {valid_range_count}")

            return True

    except Exception as e:
        print(f"验证时出错: {e}")
        return False

if __name__ == "__main__":
    validate_conversion()
