#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def summarize_fail_configs(txt_file, output_file):
    # 打开文件
    with open(txt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fail_configs = []

    i = 0
    line_count = len(lines)

    while i < line_count:
        line = lines[i].strip()

        # 检查是否是测试块开始
        if line.startswith('****************************') and line.endswith('*******************************'):
            # 解析测试块标题
            title = line.strip('*').strip()

            # 跳过标题行
            i += 1

            # 检查下一行是否是 Check FAIL
            while i < line_count and not lines[i].startswith('****************************'):
                current_line = lines[i].strip()

                if 'Check' in current_line and 'FAIL' in current_line:
                    # 提取测试项目
                    parts = current_line.split()
                    check_index = parts.index('Check')
                    test_item = ' '.join(parts[:check_index])

                    # 检查是否有详细参数
                    j = i + 1
                    has_params = False
                    header_line = ''

                    while j < line_count and not lines[j].startswith('****************************'):
                        if 'rate' in lines[j] and 'wifi_format' in lines[j]:
                            has_params = True
                            header_line = lines[j]
                            break
                        elif 'Check' in lines[j] and 'PASS' in lines[j]:
                            break
                        j += 1

                    if has_params:
                        # 有参数表头
                        j += 1
                        # 读取参数行
                        while j < line_count and lines[j].strip() != '' and not lines[j].startswith('****************************') and not ('Check' in lines[j] and 'PASS' in lines[j]):
                            data_line = lines[j].strip()
                            if data_line and not data_line.startswith('rate'):
                                # 分割参数行
                                data_parts = data_line.split()
                                # 提取参数
                                params = {}

                                # 跳过第一列（索引）
                                data_index = 1

                                # 解析参数（根据标题判断列数）
                                if 'short_gi' in header_line and len(data_parts) >= 7:
                                    params['rate'] = data_parts[1]
                                    params['wifi_format'] = data_parts[2]
                                    params['tx_power'] = data_parts[3]
                                    params['fec_coding'] = data_parts[4]
                                    params['rf_chan'] = data_parts[5]
                                    params['short_gi'] = data_parts[6]
                                elif 'fec_coding' in header_line and len(data_parts) >= 6:
                                    params['rate'] = data_parts[1]
                                    params['wifi_format'] = data_parts[2]
                                    params['tx_power'] = data_parts[3]
                                    params['fec_coding'] = data_parts[4]
                                    params['rf_chan'] = data_parts[5]
                                elif 'tx_power_set(dBm)' in header_line or 'tx_power' in header_line and len(data_parts) >= 5:
                                    params['rate'] = data_parts[1]
                                    params['wifi_format'] = data_parts[2]
                                    params['tx_power'] = data_parts[3]
                                    params['rf_chan'] = data_parts[4]
                                else:
                                    params['rate'] = data_parts[1]
                                    params['wifi_format'] = data_parts[2]

                                fail_configs.append({
                                    'block_title': title,
                                    'test_item': test_item,
                                    'parameters': params
                                })

                            j += 1
                        i = j
                    else:
                        # 没有详细参数信息
                        fail_configs.append({
                            'block_title': title,
                            'test_item': test_item,
                            'parameters': {}
                        })
                        i += 1
                else:
                    i += 1
        else:
            i += 1

    # 生成总结
    summary = "D:\\users\\gxu\\e22_tx\\spec_mask\\fail_blocks_2026_03_18_1411.txt 错误配置总结\n"
    summary += "=" * 100 + "\n"

    # 按测试块分组
    block_groups = {}
    for config in fail_configs:
        block_title = config['block_title']
        if block_title not in block_groups:
            block_groups[block_title] = []
        block_groups[block_title].append(config)

    # 输出每个测试块的配置
    for block_title, configs in block_groups.items():
        summary += f"\n测试块标题: {block_title}\n"
        summary += "-" * 80 + "\n"

        # 按测试项目分组
        item_groups = {}
        for config in configs:
            test_item = config['test_item']
            if test_item not in item_groups:
                item_groups[test_item] = []
            item_groups[test_item].append(config)

        for test_item, item_configs in item_groups.items():
            summary += f"  测试项目: {test_item}\n"

            # 如果有参数，显示参数
            if item_configs[0]['parameters']:
                summary += "  失败的配置:\n"
                # 获取所有可能的参数键
                param_keys = set()
                for config in item_configs:
                    param_keys.update(config['parameters'].keys())

                # 创建表头
                header = "    "
                for key in sorted(list(param_keys)):
                    header += f"{key:<15} "
                summary += header + "\n"
                summary += "    " + "-" * (16 * len(param_keys) - 1) + "\n"

                # 输出参数值
                for config in item_configs:
                    line = "    "
                    for key in sorted(list(param_keys)):
                        value = config['parameters'].get(key, '')
                        line += f"{value:<15} "
                    summary += line + "\n"
            else:
                summary += "  无详细参数信息\n"

    # 写入到文件
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        f.write(summary)

    print(f"总结已生成，保存到: {output_file}")
    print(f"总共有 {len(fail_configs)} 个失败的配置")

if __name__ == "__main__":
    input_file = r"D:\users\gxu\e22_tx\spec_mask\fail_blocks_2026_03_18_1411.txt"
    output_file = r"D:\users\gxu\e22_tx\spec_mask\fail_config_summary_2026_03_18_1411.txt"
    summarize_fail_configs(input_file, output_file)
