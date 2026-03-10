#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读取指定路径下的CSV文件，比较相同bw和freqMhz配置下的数据，以freqCw为横坐标，
diff_pwr为纵坐标，按channel区分画线，并保存为PDF文件。
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import argparse


def plot_csv_data(input_path, output_pdf):
    """
    读取CSV文件并绘制图表到PDF文件

    参数:
        input_path: 输入路径（可以是文件或文件夹）
        output_pdf: 输出PDF文件路径
    """
    # 收集所有CSV文件
    csv_files = []
    if os.path.isfile(input_path) and input_path.endswith('.csv'):
        csv_files = [input_path]
    elif os.path.isdir(input_path):
        for filename in os.listdir(input_path):
            if filename.endswith('.csv'):
                csv_files.append(os.path.join(input_path, filename))
    else:
        print(f"错误: {input_path} 不是有效的文件或文件夹")
        return

    if not csv_files:
        print(f"错误: 在 {input_path} 中未找到CSV文件")
        return

    print(f"找到 {len(csv_files)} 个CSV文件")

    # 读取所有CSV文件数据
    dfs = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            # 去除列名的首尾空格
            df.columns = [col.strip() for col in df.columns]
            print(f"成功读取: {os.path.basename(csv_file)} ({len(df)} 行)")
            dfs.append(df)
        except Exception as e:
            print(f"读取文件 {csv_file} 时出错: {e}")
            continue

    if not dfs:
        print("错误: 没有成功读取任何CSV文件")
        return

    # 合并所有数据
    combined_df = pd.concat(dfs, ignore_index=True)

    print(f"\n合并后的数据总记录数: {len(combined_df)}")
    print(f"唯一的带宽配置 (bw): {sorted(combined_df['bw'].unique())}")
    print(f"唯一的中心频率配置 (freqMhz): {sorted(combined_df['freqMhz'].unique())}")
    print(f"唯一的通道配置 (channel): {sorted(combined_df['channel'].unique())}")

    # 创建PDF文件
    with PdfPages(output_pdf) as pdf:
        # 按bw和freqMhz分组绘制图表
        grouped = combined_df.groupby(['bw', 'freqMhz'])

        for (bw, freqMhz), group_data in grouped:
            print(f"\n处理配置: bw={bw}, freqMhz={freqMhz}")

            # 创建图表
            fig, ax = plt.subplots(figsize=(12, 8), dpi=100)

            # 按channel分组绘制
            channel_groups = group_data.groupby('channel')
            for channel, channel_data in channel_groups:
                # 按freqCw排序
                channel_data = channel_data.sort_values('freqCw')

                # 绘制曲线
                ax.plot(channel_data['freqCw'], channel_data['diff_pwr'],
                        marker='o', linewidth=2, markersize=4, label=channel)

                print(f"  通道 {channel}: {len(channel_data)} 个数据点")

            # 设置图表标题和标签
            ax.set_title(f'bw={bw}, freqMhz={freqMhz}', fontsize=16, fontweight='bold')
            ax.set_xlabel('freqCw (MHz)', fontsize=14)
            ax.set_ylabel('diff_pwr', fontsize=14)

            # 设置坐标轴网格
            ax.grid(True, alpha=0.3)

            # 设置图例
            ax.legend(title='Channel', bbox_to_anchor=(1.02, 1), loc='upper left')

            # 调整布局
            plt.tight_layout()

            # 将图表添加到PDF
            pdf.savefig(fig)
            plt.close(fig)

            print(f"  图表已保存到PDF")

    print(f"\nPDF文件已生成: {output_pdf}")


def main():
    parser = argparse.ArgumentParser(
        description='读取指定路径下的CSV文件，比较相同bw和freqMhz配置下的数据，'
                    '以freqCw为横坐标，diff_pwr为纵坐标，按channel区分画线，并保存为PDF文件。'
    )
    parser.add_argument('input_path', help='输入路径（可以是CSV文件或包含CSV文件的文件夹）')
    parser.add_argument('-o', '--output', default='rx_iq_cal_plots.pdf',
                        help='输出路径（可以是文件名或目录。如果是目录，将使用默认文件名 rx_iq_cal_plots.pdf）')

    args = parser.parse_args()

    # 处理输出路径
    output_path = args.output
    if os.path.isdir(output_path):
        # 如果是目录，使用默认文件名
        output_path = os.path.join(output_path, 'rx_iq_cal_plots.pdf')
    else:
        # 确保输出目录存在
        output_dir = os.path.dirname(os.path.abspath(output_path))
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

    plot_csv_data(args.input_path, output_path)


if __name__ == '__main__':
    main()
