#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import math
import os

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

def plot_sensitivity_comparison(results_dict, output_pdf_path):
    """
    绘制灵敏度对比图表
    :param results_dict: 包含多个csv文件灵敏度数据的字典，key为文件夹名，value为DataFrame
    :param output_pdf_path: 输出PDF路径
    """
    with PdfPages(output_pdf_path) as pp:
        plt.figure(figsize=(11, 8))

        # 定义颜色列表，用于区分不同曲线
        colors = ['#FF0000', '#0000FF', '#00FF00', '#FFFF00', '#FF00FF', '#00FFFF', '#800000', '#008000',
                  '#000080', '#808000', '#F08080', '#8080F0', '#806F86', '#006066']

        # 绘制每个csv文件的灵敏度曲线
        for i, (folder_name, results) in enumerate(results_dict.items()):
            # 绘制notch_en=0的灵敏度曲线
            if 'sensitivity_notch0' in results.columns:
                plt.plot(results['cw_pow'], results['sensitivity_notch0'], 'o-',
                         color=colors[i % len(colors)], label=f'{folder_name} (notch_en=0)')
            # 绘制notch_en=1的灵敏度曲线
            if 'sensitivity_notch1' in results.columns:
                plt.plot(results['cw_pow'], results['sensitivity_notch1'], 's-',
                         color=colors[i % len(colors)], label=f'{folder_name} (notch_en=1)')

        # 设置图表属性
        plt.xlabel('cw_pow (dBm)')
        plt.ylabel('Sensitivity (dBm)')
        plt.title('Sensitivity vs cw_pow (folder comparison)')
        plt.legend(loc='best', fontsize=8)
        plt.grid(True)

        # 保存到PDF
        pp.savefig()
        plt.close()

if __name__ == "__main__":
    # 输入参数
    root_path = r"D:\users\gxu\spur_scan\260312\notch_cw_scan"
    output_pdf_path = r"D:\users\gxu\spur_scan\260312\notch_cw_scan\sensitivity_comparison.pdf"
    recursive_search = True  # 控制是否启用递归检索功能

    # 规范化路径，确保跨平台兼容性
    root_path = os.path.normpath(root_path)
    output_pdf_path = os.path.normpath(output_pdf_path)

    # 检查输出目录是否存在，不存在则创建
    output_dir = os.path.dirname(output_pdf_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 根据是否启用递归检索功能，处理CSV文件
    if recursive_search:
        # 递归检索指定路径下的所有CSV文件
        results_dict = {}
        for dir_name, subdir_list, file_list in os.walk(root_path):
            for file_name in file_list:
                if file_name.endswith('.csv'):
                    file_path = os.path.join(dir_name, file_name)
                    folder_name = os.path.basename(dir_name)
                    try:
                        # 处理CSV文件
                        results_df = process_csv_file(file_path)
                        results_dict[folder_name] = results_df
                        print(f"Successfully processed: {file_path}")
                    except Exception as e:
                        print(f"Failed to process {file_path}: {e}")

        # 绘制多曲线比较图表
        if results_dict:
            plot_sensitivity_comparison(results_dict, output_pdf_path)
            print(f"PDF文件已保存到: {output_pdf_path}")
        else:
            print("未找到可处理的CSV文件")
    else:
        # 处理单个CSV文件
        csv_file_path = r"D:\users\gxu\spur_scan\260312\notch_cw_scan\mcs_diff_3\RX_mcs9vht_20260312_153953.csv"
        csv_file_path = os.path.normpath(csv_file_path)
        results_df = process_csv_file(csv_file_path)
        # 由于plot_sensitivity_comparison函数参数修改，此处需要将数据转换为字典格式
        plot_sensitivity_comparison({'single_file': results_df}, output_pdf_path)
        print(f"PDF文件已保存到: {output_pdf_path}")
