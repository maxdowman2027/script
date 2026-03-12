#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import math

def calculate_sensitivity(per_values, pow_values, sens_accuracy=100):
    """
    计算灵敏度（PER <= 0.1时的最小功率）
    :param per_values: PER值列表
    :param pow_values: 对应的功率值列表
    :param sens_accuracy: 精度参数
    :return: 灵敏度值
    """
    for i in range(len(per_values)):
        if per_values[i] < 0.1:
            per_sens = math.log10(per_values[i])
            pow_sens = pow_values[i]

            if per_values[i] == 0:
                if i > 0 and per_values[i-1] != 0:
                    delta_per = (math.log10(per_values[i-1]) + 10) / sens_accuracy
                    per_sens = -10
                else:
                    delta_per = 0
            else:
                delta_per = (math.log10(per_values[i-1]) - math.log10(per_values[i])) / sens_accuracy

            for j in range(sens_accuracy):
                per_sens += delta_per
                pow_sens -= 1 / sens_accuracy

                if per_sens >= -1:  # log10(0.1) = -1
                    return round(pow_sens, 2)
    return None

def process_csv_file(file_path):
    """
    处理CSV文件，计算不同notch_en条件下的灵敏度
    :param file_path: CSV文件路径
    :return: 包含cw_pow、notch_en=0灵敏度、notch_en=1灵敏度的DataFrame
    """
    # 读取CSV文件
    df = pd.read_csv(file_path)

    # 去除列名的前导空格
    df.columns = df.columns.str.strip()

    # 计算PER
    PAK_NUM = 1000
    df['per'] = df['rxnum'].map(lambda x: 1 - min(x, PAK_NUM) / PAK_NUM)

    # 按notch_en和cw_pow分组，计算平均PER
    grouped = df.groupby(['notch_en', 'cw_pow'])['per'].mean().reset_index()

    # 分离notch_en=0和notch_en=1的数据
    data_notch0 = grouped[grouped['notch_en'] == 0].sort_values('cw_pow')
    data_notch1 = grouped[grouped['notch_en'] == 1].sort_values('cw_pow')

    # 计算灵敏度
    results = []
    cw_pow_values = sorted(df['cw_pow'].unique())

    for cw_pow in cw_pow_values:
        # 获取当前cw_pow下的notch0数据
        notch0_data = data_notch0[data_notch0['cw_pow'] == cw_pow]
        notch1_data = data_notch1[data_notch1['cw_pow'] == cw_pow]

        if not notch0_data.empty and not notch1_data.empty:
            # 获取不同rfpwr下的per和对应的rfpwr
            notch0_rfpwr_per = df[(df['notch_en'] == 0) & (df['cw_pow'] == cw_pow)].groupby('rfpwr')['per'].mean().reset_index()
            notch1_rfpwr_per = df[(df['notch_en'] == 1) & (df['cw_pow'] == cw_pow)].groupby('rfpwr')['per'].mean().reset_index()

            # 计算灵敏度
            notch0_sens = calculate_sensitivity(notch0_rfpwr_per['per'].values, notch0_rfpwr_per['rfpwr'].values)
            notch1_sens = calculate_sensitivity(notch1_rfpwr_per['per'].values, notch1_rfpwr_per['rfpwr'].values)

            results.append({
                'cw_pow': cw_pow,
                'sensitivity_notch0': notch0_sens,
                'sensitivity_notch1': notch1_sens
            })

    return pd.DataFrame(results)

def plot_sensitivity_comparison(results, output_pdf_path):
    """
    绘制灵敏度对比图表
    :param results: 包含灵敏度数据的DataFrame
    :param output_pdf_path: 输出PDF路径
    """
    with PdfPages(output_pdf_path) as pp:
        plt.figure(figsize=(11, 8))

        # 绘制notch_en=0的灵敏度曲线
        plt.plot(results['cw_pow'], results['sensitivity_notch0'], 'o-', color='#FF0000', label='notch_en=0')

        # 绘制notch_en=1的灵敏度曲线
        plt.plot(results['cw_pow'], results['sensitivity_notch1'], 'o-', color='#0000FF', label='notch_en=1')

        # 设置图表属性
        plt.xlabel('cw_pow (dBm)')
        plt.ylabel('Sensitivity (dBm)')
        plt.title('Sensitivity vs cw_pow (notch_en comparison)')
        plt.legend(loc='best')
        plt.grid(True)

        # 保存到PDF
        pp.savefig()
        plt.close()

if __name__ == "__main__":
    # 输入参数
    csv_file_path = "D:\chip_test\dev\chip_rx\eagletest\rftest_data\wifi_notch_test_spur_test\FPGA752_FPGA761_20260312\RX_mcs9vht_20260312_151455.csv"
    output_pdf_path = "D:/chip_test/dev/chip_rx/eagletest/rftest_data/wifi_notch_test_spur_test/FPGA752_FPGA761_20260312/rx_20260312/sensitivity_comparison.pdf"

    # 处理CSV文件
    results_df = process_csv_file(csv_file_path)

    # 绘制图表
    plot_sensitivity_comparison(results_df, output_pdf_path)

    print(f"PDF文件已保存到: {output_pdf_path}")
