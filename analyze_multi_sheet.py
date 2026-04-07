import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

# 设置中文字体（Windows系统）
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def analyze_sheet(df, sheet_name, base_dir):
    """分析单个Sheet的数据"""
    print(f"\n=== 正在分析 '{sheet_name}' ===")
    print(f"数据行数: {len(df)}")
    print(f"数据列数: {len(df.columns)}")

    # 检查必要列是否存在
    required_columns = ['rate', 'tx_power_set(dBm)', 'evm']
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        print(f"警告: '{sheet_name}' 缺少列: {', '.join(missing_cols)}")
        return

    # 按照wifi_format分组分析
    if 'wifi_format' in df.columns:
        wifi_formats = df['wifi_format'].unique()
        print(f"包含的wifi_format: {', '.join(wifi_formats)}")

        for wifi_format in wifi_formats:
            print(f"\n--- 分析 '{sheet_name}' 中的 '{wifi_format}' ---")
            format_df = df[df['wifi_format'] == wifi_format]

            # 统计信息
            print(f"记录数: {len(format_df)}")
            print(f"Rate 分布: {format_df['rate'].value_counts().sort_index().to_dict()}")
            print(f"TX Power Set 范围: {format_df['tx_power_set(dBm)'].min()} - {format_df['tx_power_set(dBm)'].max()}")
            print(f"EVM 统计:")
            print(f"  最小值: {format_df['evm'].min():.2f}")
            print(f"  最大值: {format_df['evm'].max():.2f}")
            print(f"  平均值: {format_df['evm'].mean():.2f}")
            print(f"  标准差: {format_df['evm'].std():.2f}")

            # 创建子文件夹保存图表
            format_dir = os.path.join(base_dir, sheet_name, wifi_format)
            os.makedirs(format_dir, exist_ok=True)

            # 可视化分析
            plot_analysis(format_df, wifi_format, sheet_name, format_dir)
    else:
        print("警告: 数据中缺少 'wifi_format' 列")

        # 直接分析整个Sheet
        create_sheet_summary(df, sheet_name, base_dir)
        plot_analysis(df, "all", sheet_name, os.path.join(base_dir, sheet_name))

    return True

def create_sheet_summary(df, sheet_name, base_dir):
    """创建Sheet级别的统计摘要"""
    print(f"\n--- '{sheet_name}' 整体分析 ---")
    print(f"记录数: {len(df)}")
    print(f"Rate 分布: {df['rate'].value_counts().sort_index().to_dict()}")
    print(f"TX Power Set 范围: {df['tx_power_set(dBm)'].min()} - {df['tx_power_set(dBm)'].max()}")
    print(f"EVM 统计:")
    print(f"  最小值: {df['evm'].min():.2f}")
    print(f"  最大值: {df['evm'].max():.2f}")
    print(f"  平均值: {df['evm'].mean():.2f}")
    print(f"  标准差: {df['evm'].std():.2f}")

def plot_analysis(df, wifi_format, sheet_name, output_dir):
    """生成各种可视化图表"""
    os.makedirs(output_dir, exist_ok=True)

    # 1. Rate vs EVM 箱线图
    plt.figure(figsize=(12, 6))
    sns.boxplot(x='rate', y='evm', data=df.sort_values('rate'))
    plt.title(f"Rate vs EVM ({wifi_format}) - {sheet_name}")
    plt.xlabel('Rate')
    plt.ylabel('EVM (dB)')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'rate_vs_evm_{wifi_format}.png'), dpi=300)
    plt.close()

    # 2. TX Power Set vs EVM 散点图
    plt.figure(figsize=(12, 6))
    sns.scatterplot(x='tx_power_set(dBm)', y='evm', data=df, alpha=0.6)
    plt.title(f"TX Power Set vs EVM ({wifi_format}) - {sheet_name}")
    plt.xlabel('TX Power Set (dBm)')
    plt.ylabel('EVM (dB)')

    # 添加趋势线
    z = df['tx_power_set(dBm)'].values
    w = df['evm'].values
    p = np.polyfit(z, w, 1)
    plt.plot(z, np.polyval(p, z), "r--", label=f"趋势线: EVM = {p[0]:.2f} * Power + {p[1]:.2f}")
    plt.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'tx_power_vs_evm_{wifi_format}.png'), dpi=300)
    plt.close()

    # 3. EVM 分布直方图
    plt.figure(figsize=(10, 6))
    sns.histplot(df['evm'], kde=True, bins=30)
    plt.title(f"EVM 分布直方图 ({wifi_format}) - {sheet_name}")
    plt.xlabel('EVM (dB)')
    plt.ylabel('频率')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'evm_distribution_{wifi_format}.png'), dpi=300)
    plt.close()

    # 4. Rate 和 TX Power Set 热图
    plt.figure(figsize=(12, 8))
    pivot = df.pivot_table(values='evm', index='rate', columns='tx_power_set(dBm)', aggfunc='mean')
    sns.heatmap(pivot, annot=True, cmap='coolwarm', fmt='.1f')
    plt.title(f"EVM 热图 ({wifi_format}) - {sheet_name}")
    plt.xlabel('TX Power Set (dBm)')
    plt.ylabel('Rate')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'evm_heatmap_{wifi_format}.png'), dpi=300)
    plt.close()

def main():
    # 文件路径
    file_path = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx_rls4\hesu_heersu_260402\merged_tx_result.xlsx"

    # 输出目录
    output_dir = os.path.join(os.path.dirname(file_path), 'analysis_by_sheet')
    os.makedirs(output_dir, exist_ok=True)

    try:
        # 读取Excel文件的所有Sheet
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names

        print(f"Excel文件包含 {len(sheet_names)} 个Sheet:")
        for i, sheet in enumerate(sheet_names, 1):
            print(f"  {i}. {sheet}")

        # 分析每个Sheet
        for sheet_name in sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            analyze_sheet(df, sheet_name, output_dir)

        # 保存汇总信息
        summary_file = os.path.join(output_dir, 'sheet_summary.xlsx')
        save_summary(xls, sheet_names, summary_file)

        print(f"\n分析完成！")
        print(f"所有分析结果保存在: {output_dir}")
        print(f"汇总信息保存在: {summary_file}")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        print(traceback.format_exc())

def save_summary(xls, sheet_names, output_file):
    """保存每个Sheet的基本信息汇总"""
    summaries = []
    for sheet_name in sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            sheet_info = {
                'Sheet Name': sheet_name,
                '记录数': len(df),
                '列数': len(df.columns),
                'Rate 种类数': df['rate'].nunique() if 'rate' in df.columns else 'N/A',
                'TX Power Set 范围': (df['tx_power_set(dBm)'].min(), df['tx_power_set(dBm)'].max()) if 'tx_power_set(dBm)' in df.columns else 'N/A',
                'EVM 平均值': df['evm'].mean() if 'evm' in df.columns else 'N/A',
                'wifi_format 种类数': df['wifi_format'].nunique() if 'wifi_format' in df.columns else 'N/A'
            }
            summaries.append(sheet_info)
        except Exception as e:
            print(f"读取 '{sheet_name}' 时出错: {e}")
            sheet_info = {
                'Sheet Name': sheet_name,
                '记录数': '错误',
                '列数': '错误',
                'Rate 种类数': '错误',
                'TX Power Set 范围': '错误',
                'EVM 平均值': '错误',
                'wifi_format 种类数': '错误'
            }
            summaries.append(sheet_info)

    df_summary = pd.DataFrame(summaries)
    df_summary.to_excel(output_file, index=False)

if __name__ == "__main__":
    main()
