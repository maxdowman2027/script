#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
import os
import pandas as pd


def hex_to_decimal_with_sign(value, bit_width):
    """
    将数值字符串转换为带符号的十进制数
    :param value: 数值字符串（可能是十进制、十六进制或带符号的）
    :param bit_width: 数据位宽
    :return: 带符号的十进制数
    """
    try:
        # 移除可能的前缀和格式化字符
        # 只移除明确的前缀和后缀字符，避免删除数值中的字符
        # 只在值看起来符合十六进制表示（包含字母）时才移除h后缀
        clean_value = str(value).strip().lower().replace("'", "")

        # 检查是否是明确的十六进制表示
        has_hex_chars = any(c in 'abcdef' for c in clean_value)

        if has_hex_chars and clean_value.endswith('h'):
            clean_value = clean_value[:-1]
            print(f"移除h后缀: {clean_value}")
        # 只在值看起来符合十进制表示（只包含数字）时才移除d后缀
        elif not has_hex_chars and clean_value.endswith('d'):
            clean_value = clean_value[:-1]
            print(f"移除d后缀: {clean_value}")

        if clean_value.startswith('0x'):
            clean_value = clean_value[2:]

        if not clean_value:
            return 0

        # 首先尝试直接解析为整数（处理负数）
        if clean_value.startswith('-'):
            try:
                # 如果是负数，直接解析为十进制整数
                return int(clean_value)
            except:
                pass

        # 对于dac_vliad_ch0[0:0]（1位宽），特殊处理
        if bit_width == 1:
            try:
                # 1位宽的值只能是0或1，返回无符号值
                return int(clean_value, 16) if clean_value else 0
            except:
                return int(clean_value) if clean_value else 0

        # 对于dac_i和dac_q列，根据格式判断：
        # - 如果包含字母字符（a-f），则是十六进制
        # - 如果长度是3位且以0开头，可能是十六进制
        # - 特殊格式如000/fff/ffd/ffe，是十六进制
        is_hex = False

        # 包含字母字符（a-f），一定是十六进制
        if any(c in 'abcdef' for c in clean_value):
            is_hex = True
        # 长度3位且包含非十进制字符，是十六进制
        elif len(clean_value) == 3 and (any(c in 'abcdef' for c in clean_value) or 'f' in clean_value):
            is_hex = True
        # 格式为000、001、fff等，是十六进制
        elif len(clean_value) > 1 and (clean_value[0] == '0' and len(clean_value) == 3 or
                                       clean_value == 'fff' or clean_value == 'ffd' or clean_value == 'ffe'):
            is_hex = True

        if is_hex:
            try:
                # 转换为无符号整数
                unsigned_val = int(clean_value, 16)

                # 处理有符号数
                if bit_width > 0:
                    sign_bit = 1 << (bit_width - 1)
                    if unsigned_val & sign_bit:
                        unsigned_val -= (1 << bit_width)

                return unsigned_val
            except:
                pass

        # 默认解析为十进制
        try:
            return int(clean_value)
        except:
            return 0

    except Exception as e:
        print(f"转换错误: 值={value}, 错误={e}")
        return 0


def process_waveform_csv(input_file, output_file):
    """
    处理CSV文件，将指定列的十六进制数据转换为十进制
    """
    print(f"正在处理文件: {input_file}")

    try:
        # 读取CSV文件
        df = pd.read_csv(input_file, encoding='utf-8', engine='python')

        # 定义需要转换的列及其位宽
        columns_to_convert = {
            'dac_i_ch0[11:0]': 12,
            'dac_q_ch0[11:0]': 12,
            'dac_vliad_ch0[0:0]': 1,
            'dac_i_ch1[11:0]': 12,
            'dac_q_ch1[11:0]': 12
        }

        # 转换各列
        for col_name, bit_width in columns_to_convert.items():
            if col_name in df.columns:
                print(f"正在转换列: {col_name} (位宽: {bit_width})")
                # 应用转换函数
                df[col_name] = df[col_name].apply(lambda x: hex_to_decimal_with_sign(x, bit_width))
            else:
                print(f"警告: 未找到列 '{col_name}'")

        # 保存结果到新文件
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"处理完成！结果已保存到: {output_file}")

        return True
    except Exception as e:
        print(f"处理文件时出错: {e}")
        return False


def main():
    input_file = r"D:\test_data\wifi7\260327_hesu_nss2\waveform.csv"
    output_file = r"D:\test_data\wifi7\260327_hesu_nss2\waveform_decimal.csv"

    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在 - {input_file}")
        return False

    return process_waveform_csv(input_file, output_file)


if __name__ == "__main__":
    main()
