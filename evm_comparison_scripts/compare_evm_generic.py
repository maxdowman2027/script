import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np
from datetime import datetime
import argparse


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="EVM Comparison Script for WiFi Test Results")
    parser.add_argument("file1", help="Path to the first version Excel file")
    parser.add_argument("file2", help="Path to the second version Excel file")
    parser.add_argument("-v1", "--version1", default="version1", help="Name of the first version (default: version1)")
    parser.add_argument("-v2", "--version2", default="version2", help="Name of the second version (default: version2)")
    parser.add_argument("-o", "--output", help="Path to output directory (default: ./evm_comparison_result)")

    args = parser.parse_args()

    # 文件路径
    file1 = args.file1
    file2 = args.file2
    version1 = args.version1
    version2 = args.version2
    output_dir = args.output if args.output else os.path.join(os.getcwd(), "evm_comparison_result")

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 读取第一个文件
    print(f"=== Start analyzing {version1} data ===")
    try:
        xls1 = pd.ExcelFile(file1)
        print(f"{version1} file contains {len(xls1.sheet_names)} Sheets: {xls1.sheet_names}")
    except Exception as e:
        print(f"Failed to read {version1} file: {e}")
        return

    # 读取第二个文件
    print(f"\n=== Start analyzing {version2} data ===")
    try:
        xls2 = pd.ExcelFile(file2)
        print(f"{version2} file contains {len(xls2.sheet_names)} Sheets: {xls2.sheet_names}")
    except Exception as e:
        print(f"Failed to read {version2} file: {e}")
        return

    # 读取所有Sheet数据
    data1 = {}
    for sheet in xls1.sheet_names:
        try:
            df = pd.read_excel(xls1, sheet_name=sheet)
            data1[sheet] = df
            print(f"\n{version1} {sheet} Sheet info:")
            print(f"Record count: {len(df)}")
            print(f"Column names: {list(df.columns)}")
            print(f"Format types: {df['wifi_format'].unique() if 'wifi_format' in df.columns else 'N/A'}")
            print(f"Rate types: {df['rate'].unique() if 'rate' in df.columns else 'N/A'}")
            print(f"TX Power range: {df['tx_power_set(dBm)'].min(), df['tx_power_set(dBm)'].max() if 'tx_power_set(dBm)' in df.columns else 'N/A'}")
            print(f"EVM columns: {'evm' if 'evm' in df.columns else 'evm_nss0/evm_nss1'}")
        except Exception as e:
            print(f"Failed to read {version1} {sheet} Sheet: {e}")

    data2 = {}
    for sheet in xls2.sheet_names:
        try:
            df = pd.read_excel(xls2, sheet_name=sheet)
            data2[sheet] = df
            print(f"\n{version2} {sheet} Sheet info:")
            print(f"Record count: {len(df)}")
            print(f"Column names: {list(df.columns)}")
            print(f"Format types: {df['wifi_format'].unique() if 'wifi_format' in df.columns else 'N/A'}")
            print(f"Rate types: {df['rate'].unique() if 'rate' in df.columns else 'N/A'}")
            print(f"TX Power range: {df['tx_power_set(dBm)'].min(), df['tx_power_set(dBm)'].max() if 'tx_power_set(dBm)' in df.columns else 'N/A'}")
            print(f"EVM column: {'evm' if 'evm' in df.columns else 'N/A'}")
        except Exception as e:
            print(f"Failed to read {version2} {sheet} Sheet: {e}")

    # Comparison analysis
    comparison_result = []
    for sheet1, df1 in data1.items():
        # Find matching sheet in the second file
        matched_sheet = find_matching_sheet(sheet1, data2.keys())
        if matched_sheet and matched_sheet in data2:
            print(f"\n=== Comparing {sheet1} ({version1}) and {matched_sheet} ({version2}) ===")
            compare_dataframes(df1, data2[matched_sheet], sheet1, matched_sheet, comparison_result, output_dir, version1, version2)
        else:
            print(f"\nWarning: No matching {version2} Sheet found for {version1} {sheet1}")

    # 保存对比结果
    save_comparison_results(comparison_result, output_dir, version1, version2)

    print(f"\n分析完成！所有结果已保存在: {output_dir}")


def find_matching_sheet(old_sheet, new_sheets):
    # 尝试找到匹配的Sheet，考虑可能的命名差异
    old_sheet_lower = old_sheet.lower()
    for new_sheet in new_sheets:
        new_sheet_lower = new_sheet.lower()
        if old_sheet_lower == new_sheet_lower:
            return new_sheet
        if '2g' in old_sheet_lower and '2g' in new_sheet_lower:
            return new_sheet
        if '5g' in old_sheet_lower and '5g' in new_sheet_lower:
            return new_sheet
        if 'vht' in old_sheet_lower and 'vht' in new_sheet_lower:
            return new_sheet
        if 'ht' in old_sheet_lower and 'ht' in new_sheet_lower:
            return new_sheet
    return None


def compare_dataframes(df1, df2, sheet1, sheet2, comparison_result, output_dir, version1, version2):
    # Ensure key columns exist
    required_cols = ['wifi_format', 'rate', 'tx_power_set(dBm)']
    missing_cols = []
    for col in required_cols:
        if col not in df1.columns or col not in df2.columns:
            missing_cols.append(col)

    if missing_cols:
        print(f"Warning: Missing key columns {', '.join(missing_cols)}, cannot complete comparison")
        return

    # 确定使用哪个EVM列
    evm_col1 = 'evm'
    if 'evm' not in df1.columns:
        if 'evm_nss0' in df1.columns:
            evm_col1 = 'evm_nss0'
        elif 'evm_nss1' in df1.columns:
            evm_col1 = 'evm_nss1'
        else:
            print(f"Warning: No EVM column found in {version1} data")
            return

    if 'evm' not in df2.columns:
        print(f"Warning: No EVM column found in {version2} data")
        return

    # Merge data
    merged_df = pd.merge(
        df1[required_cols + [evm_col1]],
        df2[required_cols + ['evm']],
        on=['wifi_format', 'rate', 'tx_power_set(dBm)'],
        how='inner',
        suffixes=(f'_{version1}', f'_{version2}')
    )

    print(f"Found {len(merged_df)} matching records")

    # 计算EVM差异
    merged_df['evm_diff'] = merged_df[f'evm_{version2}'] - merged_df[f'{evm_col1}_{version1}']
    merged_df['abs_diff'] = abs(merged_df['evm_diff'])

    # 保存详细的对比结果，并为EVM值添加填充色
    output_file = os.path.join(output_dir, f'{sheet1}_vs_{sheet2}_detailed.xlsx')
    merged_df.to_excel(output_file, index=False)

    # 为EVM值和差值添加填充色
    import openpyxl
    from openpyxl.styles import PatternFill

    wb = openpyxl.load_workbook(output_file)
    ws = wb.active

    # 查找EVM相关列的索引
    evm_col1_idx = None
    evm_col2_idx = None
    evm_diff_col_idx = None
    for idx, cell in enumerate(ws[1]):
        if cell.value == f'{evm_col1}_{version1}':
            evm_col1_idx = idx + 1
        elif cell.value == f'evm_{version2}':
            evm_col2_idx = idx + 1
        elif cell.value == 'evm_diff':
            evm_diff_col_idx = idx + 1

    # 定义EVM颜色填充规则（EVM值越小越好，负数表示dB）
    def get_evm_fill(evm_value):
        if evm_value <= -30:
            return PatternFill(start_color='00FF00', end_color='00FF00', fill_type='solid')  # 绿色
        elif evm_value <= -25:
            return PatternFill(start_color='90EE90', end_color='90EE90', fill_type='solid')  # 浅绿色
        elif evm_value <= -20:
            return PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')  # 黄色
        elif evm_value <= -15:
            return PatternFill(start_color='FFA500', end_color='FFA500', fill_type='solid')  # 橙色
        else:
            return PatternFill(start_color='FF0000', end_color='FF0000', fill_type='solid')  # 红色

    # 定义差值颜色填充规则
    def get_diff_fill(diff_value):
        if diff_value <= -2:
            return PatternFill(start_color='00FF00', end_color='00FF00', fill_type='solid')  # 绿色（第二个版本明显更好）
        elif diff_value <= -1:
            return PatternFill(start_color='90EE90', end_color='90EE90', fill_type='solid')  # 浅绿色（第二个版本更好）
        elif diff_value <= 1:
            return PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')  # 黄色（无显著差异）
        elif diff_value <= 2:
            return PatternFill(start_color='FFA500', end_color='FFA500', fill_type='solid')  # 橙色（第二个版本较差）
        else:
            return PatternFill(start_color='FF0000', end_color='FF0000', fill_type='solid')  # 红色（第二个版本明显较差）

    # 为两个版本的EVM值添加填充色
    if evm_col1_idx:
        for row in range(2, ws.max_row + 1):
            cell = ws.cell(row=row, column=evm_col1_idx)
            evm_value = cell.value
            if isinstance(evm_value, (int, float)):
                cell.fill = get_evm_fill(evm_value)

    if evm_col2_idx:
        for row in range(2, ws.max_row + 1):
            cell = ws.cell(row=row, column=evm_col2_idx)
            evm_value = cell.value
            if isinstance(evm_value, (int, float)):
                cell.fill = get_evm_fill(evm_value)

    # 为差值添加填充色
    if evm_diff_col_idx:
        for row in range(2, ws.max_row + 1):
            cell = ws.cell(row=row, column=evm_diff_col_idx)
            diff_value = cell.value
            if isinstance(diff_value, (int, float)):
                cell.fill = get_diff_fill(diff_value)

    wb.save(output_file)

    # 统计结果
    stats = merged_df.groupby(['wifi_format', 'rate']).agg(
        count=('evm_diff', 'count'),
        mean_diff=('evm_diff', 'mean'),
        median_diff=('evm_diff', 'median'),
        std_diff=('evm_diff', 'std'),
        min_diff=('evm_diff', 'min'),
        max_diff=('evm_diff', 'max'),
        mean_abs_diff=('abs_diff', 'mean'),
        version1_mean_evm=(f'{evm_col1}_{version1}', 'mean'),
        version1_median_evm=(f'{evm_col1}_{version1}', 'median'),
        version1_std_evm=(f'{evm_col1}_{version1}', 'std'),
        version2_mean_evm=(f'evm_{version2}', 'mean'),
        version2_median_evm=(f'evm_{version2}', 'median'),
        version2_std_evm=(f'evm_{version2}', 'std')
    ).reset_index()

    stats.to_excel(os.path.join(output_dir, f'{sheet1}_vs_{sheet2}_summary.xlsx'), index=False)

    # 可视化
    plot_comparison(stats, merged_df, sheet1, sheet2, output_dir, evm_col1, version1, version2)

    # 更新比较结果列表
    comparison_result.append({
        f'{version1}_sheet': sheet1,
        f'{version2}_sheet': sheet2,
        'matched_count': len(merged_df),
        f'total_{version1}_records': len(df1),
        f'total_{version2}_records': len(df2),
        'mean_evm_diff': stats['mean_diff'].mean(),
        'max_evm_diff': stats['max_diff'].max(),
        'min_evm_diff': stats['min_diff'].min(),
        'avg_abs_diff': stats['mean_abs_diff'].mean(),
        f'{version1}_evm_col': evm_col1
    })


def plot_comparison(stats, merged_df, sheet1, sheet2, output_dir, evm_col1, version1, version2):
    sheet_dir = os.path.join(output_dir, f'{sheet1}_vs_{sheet2}')
    os.makedirs(sheet_dir, exist_ok=True)

    # 1. EVM difference distribution histogram
    plt.figure(figsize=(12, 6))
    plt.hist(merged_df['evm_diff'], bins=30, alpha=0.7, color='b')
    plt.axvline(merged_df['evm_diff'].mean(), color='r', linestyle='--', label=f'Mean = {merged_df["evm_diff"].mean():.2f}')
    plt.axvline(0, color='g', linestyle='-', label='No Difference')
    plt.title(f'{sheet1} vs {sheet2} EVM Difference Distribution')
    plt.xlabel('EVM Difference (dB)')
    plt.ylabel('Number of Records')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(sheet_dir, 'evm_diff_distribution.png'), dpi=150)
    plt.close()

    # 2. Average difference by wifi_format and rate
    plt.figure(figsize=(16, 8))
    pivot = stats.pivot(index='rate', columns='wifi_format', values='mean_diff')
    sns.heatmap(pivot, annot=True, cmap='coolwarm', fmt='.2f', cbar_kws={'label': 'Average EVM Difference (dB)'})
    plt.title(f'{sheet1} vs {sheet2} Average EVM Difference by Format and Rate')
    plt.tight_layout()
    plt.savefig(os.path.join(sheet_dir, 'evm_diff_heatmap.png'), dpi=150)
    plt.close()

    # 3. Version 1 vs Version 2 EVM comparison scatter plot
    plt.figure(figsize=(12, 10))
    plt.scatter(merged_df[f'{evm_col1}_{version1}'], merged_df[f'evm_{version2}'], alpha=0.6, s=20)
    plt.plot([merged_df[f'{evm_col1}_{version1}'].min(), merged_df[f'{evm_col1}_{version1}'].max()],
             [merged_df[f'{evm_col1}_{version1}'].min(), merged_df[f'{evm_col1}_{version1}'].max()], 'r--', label='Ideal Case')
    plt.xlabel(f'{version1} EVM ({evm_col1}) (dB)')
    plt.ylabel(f'{version2} EVM (dB)')
    plt.title(f'{sheet1} vs {sheet2} {version1} vs {version2} EVM Comparison')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(sheet_dir, 'evm_comparison_scatter.png'), dpi=150)
    plt.close()

    # 4. EVM difference boxplot by wifi_format
    plt.figure(figsize=(16, 8))
    sns.boxplot(x='wifi_format', y='mean_diff', data=stats)
    plt.axhline(y=0, color='g', linestyle='-', label='No Difference')
    plt.title(f'{sheet1} vs {sheet2} EVM Difference by Wifi Format')
    plt.xlabel('Wifi Format')
    plt.ylabel('EVM Difference (dB)')
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(sheet_dir, 'evm_diff_by_format.png'), dpi=150)
    plt.close()

    # 5. EVM difference boxplot by rate
    plt.figure(figsize=(16, 8))
    sns.boxplot(x='rate', y='mean_diff', data=stats)
    plt.axhline(y=0, color='g', linestyle='-', label='No Difference')
    plt.title(f'{sheet1} vs {sheet2} EVM Difference by Rate')
    plt.xlabel('Rate')
    plt.ylabel('EVM Difference (dB)')
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(sheet_dir, 'evm_diff_by_rate.png'), dpi=150)
    plt.close()


def save_comparison_results(comparison_result, output_dir, version1, version2):
    # 保存HTML报告
    html_file = os.path.join(output_dir, 'evm_comparison_report.html')
    generate_html_report(comparison_result, output_dir, html_file, version1, version2)

    print(f"HTML报告已保存: {html_file}")


def generate_html_report(comparison_result, output_dir, output_file, version1, version2):
    # Generate HTML report
    html_content = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>%s vs %s Version EVM Comparison Analysis</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1, h2, h3 {
                color: #333;
            }
            .section {
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 1px solid #ddd;
            }
            .summary-table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
                background-color: white;
            }
            .summary-table th, .summary-table td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            .summary-table th {
                background-color: #f2f2f2;
            }
            .summary-table tr:hover {
                background-color: #f5f5f5;
            }
            .success {
                color: green;
            }
            .warning {
                color: orange;
            }
            .error {
                color: red;
            }
            .image-container {
                text-align: center;
                margin: 20px 0;
            }
            .image-container img {
                max-width: 100%;
                height: auto;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            .sheet-link {
                color: #1a73e8;
                text-decoration: none;
            }
            .sheet-link:hover {
                text-decoration: underline;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 6px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            .stat-card h4 {
                margin-top: 0;
                color: #555;
            }
            .stat-value {
                font-size: 24px;
                font-weight: bold;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>%s 与 %s 版本 EVM 对比分析</h1>

            <div class="section">
                <h2>1. 整体对比统计</h2>
                <div class="stats">
    ''' % (version1, version2, version1, version2)

    total_matched = 0
    total_version1_records = 0
    total_version2_records = 0
    max_diff = None
    min_diff = None
    avg_abs_diff = None

    for result in comparison_result:
        total_matched += result['matched_count']
        total_version1_records += result[f'total_{version1}_records']
        total_version2_records += result[f'total_{version2}_records']

        if max_diff is None or result['max_evm_diff'] > max_diff:
            max_diff = result['max_evm_diff']

        if min_diff is None or result['min_evm_diff'] < min_diff:
            min_diff = result['min_evm_diff']

        if avg_abs_diff is None:
            avg_abs_diff = result['avg_abs_diff']
        else:
            avg_abs_diff = (avg_abs_diff + result['avg_abs_diff']) / 2

    html_content += '''
                <div class="stat-card">
                    <h4>匹配记录数</h4>
                    <div class="stat-value">%d</div>
                    <p>%s总记录数: %d<br>%s总记录数: %d</p>
                </div>
                <div class="stat-card">
                    <h4>平均EVM差值</h4>
                    <div class="stat-value" style="color:%s;">%.2f dB</div>
                    <p>平均值</p>
                </div>
                <div class="stat-card">
                    <h4>最大EVM差值</h4>
                    <div class="stat-value" style="color:%s;">%.2f dB</div>
                    <p>最大值</p>
                </div>
                <div class="stat-card">
                    <h4>最小EVM差值</h4>
                    <div class="stat-value" style="color:%s;">%.2f dB</div>
                    <p>最小值</p>
                </div>
    ''' % (
        total_matched, version1, total_version1_records, version2, total_version2_records,
        'green' if abs(avg_abs_diff) < 1 else 'orange' if abs(avg_abs_diff) < 2 else 'red',
        avg_abs_diff,
        'red' if max_diff > 2 else 'orange' if max_diff > 1 else 'green',
        max_diff,
        'green' if min_diff > -1 else 'orange' if min_diff > -2 else 'red',
        min_diff
    )

    html_content += '''
                </div>
            </div>

            <div class="section">
                <h2>2. Sheet级对比详情</h2>
                <table class="summary-table">
                    <thead>
                        <tr>
                            <th>%s Sheet</th>
                            <th>%s Sheet</th>
                            <th>匹配记录数</th>
                            <th>%s记录数</th>
                            <th>%s记录数</th>
                            <th>平均差值</th>
                            <th>最大差值</th>
                            <th>最小差值</th>
                            <th>平均绝对差值</th>
                            <th>%s EVM列</th>
                            <th>详细结果</th>
                        </tr>
                    </thead>
                    <tbody>
    ''' % (version1, version2, version1, version2, version1)

    for result in comparison_result:
        avg_diff_class = 'success' if abs(result['mean_evm_diff']) < 1 else 'warning' if abs(result['mean_evm_diff']) < 2 else 'error'
        max_diff_class = 'success' if result['max_evm_diff'] <= 2 else 'warning' if result['max_evm_diff'] <= 5 else 'error'
        min_diff_class = 'success' if result['min_evm_diff'] >= -2 else 'warning' if result['min_evm_diff'] >= -5 else 'error'
        avg_abs_class = 'success' if result['avg_abs_diff'] < 1 else 'warning' if result['avg_abs_diff'] < 2 else 'error'

        html_content += '''
                        <tr>
                            <td>%s</td>
                            <td>%s</td>
                            <td>%d</td>
                            <td>%d</td>
                            <td>%d</td>
                            <td class="%s">%.2f</td>
                            <td class="%s">%.2f</td>
                            <td class="%s">%.2f</td>
                            <td class="%s">%.2f</td>
                            <td>%s</td>
                            <td>
                                <a href="%s_vs_%s_detailed.xlsx" class="sheet-link">Detailed Data</a><br>
                                <a href="%s_vs_%s_summary.xlsx" class="sheet-link">Statistical Summary</a><br>
                                <a href="%s_vs_%s" class="sheet-link">Charts</a>
                            </td>
                        </tr>
        ''' % (
            result[f'{version1}_sheet'],
            result[f'{version2}_sheet'],
            result['matched_count'],
            result[f'total_{version1}_records'],
            result[f'total_{version2}_records'],
            avg_diff_class, result['mean_evm_diff'],
            max_diff_class, result['max_evm_diff'],
            min_diff_class, result['min_evm_diff'],
            avg_abs_class, result['avg_abs_diff'],
            result[f'{version1}_evm_col'],
            result[f'{version1}_sheet'], result[f'{version2}_sheet'],
            result[f'{version1}_sheet'], result[f'{version2}_sheet'],
            result[f'{version1}_sheet'], result[f'{version2}_sheet']
        )

    html_content += '''
                    </tbody>
                </table>
            </div>

            <div class="section">
                <h2>3. 主要发现</h2>
                <ul>
                    <li><strong>匹配记录百分比:</strong> %s记录中有%.2f%%在%s版本中找到了匹配项</li>
                    <li><strong>整体EVM趋势:</strong> %s</li>
                    <li><strong>主要差异来源:</strong> 需要进一步分析特定Rate和Format组合的性能</li>
                </ul>
            </div>

            <div class="section">
                <h2>4. 使用建议</h2>
                <ol>
                    <li>应优先检查具有较大差异的Sheet和Rate/Format组合</li>
                    <li>重点分析平均绝对差值大于2dB的配置</li>
                    <li>检查%s版本是否覆盖了所有测试场景</li>
                    <li>如有必要，进行硬件验证以确认差异是否合理</li>
                </ol>
            </div>

            <div class="section">
                <h2>5. 文件描述</h2>
                <ul>
                    <li><strong>分析脚本:</strong> compare_evm_generic.py</li>
                    <li><strong>%s版本文件:</strong> %s</li>
                    <li><strong>%s版本文件:</strong> %s</li>
                    <li><strong>生成时间:</strong> %s</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    ''' % (
        version1, (total_matched / total_version1_records) * 100, version2,
        f"{version2}版本整体EVM更好" if avg_abs_diff < -0.5 else f"{version2}版本整体EVM更差" if avg_abs_diff > 0.5 else f"{version1}和{version2}版本之间的EVM差异不显著",
        version2,
        version1, 'file1',
        version2, 'file2',
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)


if __name__ == "__main__":
    main()