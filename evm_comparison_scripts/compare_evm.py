import os
import pandas as pd
import glob

def parse_filename(filename):
    """
    从文件名解析配置信息
    """
    config = {}
    # 文件名格式示例：risc_wifitx_20m_['eht']_BCC_channel5180_GILTF0_2025-1226-224055.csv

    # 使用正则表达式匹配关键信息
    import re

    # 匹配带宽 (20m, 40m, 80m等)
    bandwidth_match = re.search(r'_(\d+m)_', filename)
    config['bandwidth'] = bandwidth_match.group(1) if bandwidth_match else 'unknown'

    # 匹配WiFi格式 (['eht'], ['hesu'], ['ht']等)
    format_match = re.search(r'\[(.+?)\]', filename)
    config['wifi_format'] = format_match.group(1) if format_match else 'unknown'

    # 匹配编码方式 (BCC, LDPC)
    coding_match = re.search(r'_(BCC|LDPC)_', filename)
    config['coding'] = coding_match.group(1) if coding_match else 'unknown'

    # 匹配频道 (channel11, channel5180等)
    channel_match = re.search(r'_channel(\d+)_', filename)
    config['channel'] = channel_match.group(1) if channel_match else 'unknown'

    # 匹配GILTF (GILTF0, GILTF1等)
    giltf_match = re.search(r'_GILTF(\d+)_', filename)
    config['giltf'] = giltf_match.group(1) if giltf_match else 'unknown'

    return config

def find_matching_files(dir1, dir2):
    """
    查找两个目录下配置相同的文件
    """
    dir1_files = {}
    # 遍历第一个目录的文件
    for csv_file in glob.glob(os.path.join(dir1, 'risc*.csv')):
        filename = os.path.basename(csv_file)
        config = parse_filename(filename)
        key = (config['bandwidth'], config['wifi_format'], config['coding'], config['channel'], config['giltf'])
        dir1_files[key] = csv_file

    dir2_files = {}
    # 遍历第二个目录的文件
    for root, dirs, files in os.walk(dir2):
        for csv_file in glob.glob(os.path.join(root, 'risc*.csv')):
            filename = os.path.basename(csv_file)
            config = parse_filename(filename)
            key = (config['bandwidth'], config['wifi_format'], config['coding'], config['channel'], config['giltf'])
            dir2_files[key] = csv_file

    # 找到相同配置的文件对
    matching_pairs = []
    for key in dir1_files:
        if key in dir2_files:
            matching_pairs.append((dir1_files[key], dir2_files[key], key))

    return matching_pairs

def compare_evm(file1, file2, config):
    """
    比较两个文件的EVM统计结果
    """
    try:
        df1 = pd.read_csv(file1)
        df2 = pd.read_csv(file2)

        # 检查是否有evm列
        if 'evm' not in df1.columns or 'evm' not in df2.columns:
            return None

        # 计算统计结果
        stats = {}

        # 基本统计
        stats['config'] = config
        stats['file1'] = os.path.basename(file1)
        stats['file2'] = os.path.basename(file2)

        # 整体统计
        stats['file1_evm_mean'] = df1['evm'].mean()
        stats['file1_evm_std'] = df1['evm'].std()
        stats['file1_evm_min'] = df1['evm'].min()
        stats['file1_evm_max'] = df1['evm'].max()

        stats['file2_evm_mean'] = df2['evm'].mean()
        stats['file2_evm_std'] = df2['evm'].std()
        stats['file2_evm_min'] = df2['evm'].min()
        stats['file2_evm_max'] = df2['evm'].max()

        # 差异
        stats['mean_diff'] = stats['file1_evm_mean'] - stats['file2_evm_mean']
        stats['std_diff'] = stats['file1_evm_std'] - stats['file2_evm_std']
        stats['min_diff'] = stats['file1_evm_min'] - stats['file2_evm_min']
        stats['max_diff'] = stats['file1_evm_max'] - stats['file2_evm_max']

        return stats
    except Exception as e:
        print(f"Error comparing {file1} and {file2}: {e}")
        return None

def print_config(config):
    """
    格式化配置信息输出
    """
    return f"{config[0]} {config[1]} {config[2]} channel{config[3]} GILTF{config[4]}"

def main():
    # 两个目录路径
    dir1 = r"D:\chip_test\dev\chip_tx\eagletest\py_script_fpga_tx_wifi7\Log\wifi_tx\251226"
    dir2 = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx"

    print("正在查找匹配的文件对...")
    matching_pairs = find_matching_files(dir1, dir2)
    print(f"找到 {len(matching_pairs)} 对匹配的文件")

    if not matching_pairs:
        print("\n未找到完全匹配的文件对，尝试显示所有文件信息：")

        # 显示第一个目录的所有配置
        print("\n目录1的所有文件配置：")
        for csv_file in glob.glob(os.path.join(dir1, 'risc*.csv')):
            filename = os.path.basename(csv_file)
            config = parse_filename(filename)
            key = (config['bandwidth'], config['wifi_format'], config['coding'], config['channel'], config['giltf'])
            print(f"  {print_config(key)}")

        # 显示第二个目录的所有配置
        print("\n目录2的所有文件配置：")
        for root, dirs, files in os.walk(dir2):
            for csv_file in glob.glob(os.path.join(root, 'risc*.csv')):
                filename = os.path.basename(csv_file)
                config = parse_filename(filename)
                key = (config['bandwidth'], config['wifi_format'], config['coding'], config['channel'], config['giltf'])
                print(f"  {print_config(key)}")

        return

    # 比较结果
    results = []
    print("正在比较EVM统计结果...")
    for file1, file2, config in matching_pairs:
        print(f"比较 {print_config(config)}")
        result = compare_evm(file1, file2, config)
        if result:
            results.append(result)

    # 输出结果
    print("\n" + "-" * 80)
    print("EVM比较结果")
    print("-" * 80)

    if not results:
        print("没有找到包含EVM列的匹配文件")
        return

    for result in results:
        config_str = print_config(result['config'])
        print(f"\n配置: {config_str}")
        print(f"文件1 ({result['file1']}):")
        print(f"  平均值: {result['file1_evm_mean']:.2f} dB, 标准差: {result['file1_evm_std']:.2f}, 最小: {result['file1_evm_min']:.2f}, 最大: {result['file1_evm_max']:.2f}")
        print(f"文件2 ({result['file2']}):")
        print(f"  平均值: {result['file2_evm_mean']:.2f} dB, 标准差: {result['file2_evm_std']:.2f}, 最小: {result['file2_evm_min']:.2f}, 最大: {result['file2_evm_max']:.2f}")
        print(f"差值:")
        print(f"  平均值: {result['mean_diff']:.2f} dB, 标准差: {result['std_diff']:.2f}, 最小: {result['min_diff']:.2f}, 最大: {result['max_diff']:.2f}")

    # 保存结果到CSV
    output_file = "evm_comparison_results.csv"
    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False)
    print(f"\n详细结果已保存到 {output_file}")

if __name__ == "__main__":
    main()
