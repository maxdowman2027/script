#!/usr/bin/env python3
"""
E22寄存器查询工具 - 增强版
功能：
1. 通过寄存器名称查询寄存器详细信息
2. 通过物理地址查询寄存器所在CSV文件和详细信息
3. 支持指定CSV文件路径
4. 支持查询寄存器地址或名称
"""

import csv
import re
import os
import argparse
import sys


def read_base_addr(base_addr_path=None):
    """读取基地址文件"""
    base_addr = {}
    if base_addr_path and os.path.exists(base_addr_path):
        with open(base_addr_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    module, addr = line.split(',')
                    base_addr[module.strip()] = int(addr.strip(), 16)
    else:
        # 默认基地址
        base_addr = {
            'phy_common': 0xc3026000,
            'phy_txfreq': 0xc3026400,
            'phy_txdfe_reg': 0xc3026800,
            'phy_rxfreq': 0xc3026C00,
            'phy_rxtime': 0xc3027000,
            'phy_txbf': 0xc3027C00,
            'phy_fft': 0xc3027e00,
            'phy_rx11b': 0xc3027a00
        }
    return base_addr


def calculate_reg_default(rows, addr_row_idx):
    """计算寄存器的32位默认值"""
    default_bits = ['0'] * 32
    j = addr_row_idx
    bit_fields = []

    while j < len(rows):
        bit_row = rows[j]
        if j > addr_row_idx and len(bit_row) > 0 and bit_row[0]:
            break  # 遇到下一个地址行，停止
        if len(bit_row) > 8 and bit_row[8]:
            bit_pos = bit_row[7]
            default = bit_row[8]
            signal = bit_row[6] if len(bit_row) > 6 else ''

            if signal:
                bit_fields.append({
                    'signal': signal,
                    'bit_pos': bit_pos,
                    'default': default
                })

            bit_match = re.search(r'\[(\d+)(?::(\d+))?\]', bit_pos)
            if bit_match:
                if bit_match.group(2):
                    start_bit = int(bit_match.group(1))
                    end_bit = int(bit_match.group(2))
                else:
                    start_bit = int(bit_match.group(1))
                    end_bit = start_bit

                default_val = 0
                quote_match = re.search(r"(\d+)'([bdh])?([0-9a-f]+)", default.lower())
                if quote_match:
                    val_str = quote_match.group(3)
                    num_base = 2
                    if quote_match.group(2) == 'd':
                        num_base = 10
                    elif quote_match.group(2) == 'h':
                        num_base = 16
                    default_val = int(val_str, num_base)
                elif default.endswith('d0'):
                    default_val = 0

                val_binary = bin(default_val)[2:].zfill(start_bit - end_bit + 1)
                for k in range(start_bit, end_bit - 1, -1):
                    pos = 31 - k
                    if len(val_binary) > (start_bit - k):
                        default_bits[pos] = val_binary[start_bit - k]
        j += 1

    default_32bit = ''.join(default_bits)
    default_dec = int(default_32bit, 2)
    default_hex = f"0x{default_dec:08X}"

    return default_hex, default_32bit, default_dec, bit_fields


def find_register_info(reg_name, csv_dir=None):
    """通过寄存器名称查找寄存器信息"""
    if csv_dir is None:
        csv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'csv_files')

    base_addr = read_base_addr()

    if not os.path.exists(csv_dir):
        print(f"错误: CSV文件目录不存在: {csv_dir}")
        return None

    for filename in os.listdir(csv_dir):
        if filename.endswith('.csv'):
            module = filename.replace('.csv', '')
            csv_path = os.path.join(csv_dir, filename)

            with open(csv_path, 'r') as f:
                reader = csv.reader(f, delimiter=';')
                rows = list(reader)

                for i, row in enumerate(rows):
                    if len(row) > 6 and reg_name in row[6]:
                        reg_row = row
                        addr_row = None
                        addr_row_idx = -1
                        for j in range(i, -1, -1):
                            if rows[j][0] and rows[j][0].startswith('0x'):
                                addr_row = rows[j]
                                addr_row_idx = j
                                break

                        if addr_row:
                            offset = int(addr_row[0], 16)
                            base = base_addr.get(module, 0)
                            full_addr = base + offset
                            default_hex, default_32bit, default_dec, bit_fields = calculate_reg_default(rows, addr_row_idx)

                            return {
                                'reg_name': reg_name,
                                'module': module,
                                'base_addr': f"0x{base:08X}",
                                'offset': addr_row[0],
                                'full_addr': f"0x{full_addr:08X}",
                                'bit_pos': reg_row[7],
                                'bit_default': reg_row[8],
                                'reg_default': default_hex,
                                'reg_default_binary': default_32bit,
                                'reg_default_dec': default_dec,
                                'csv_file': filename,
                                'csv_path': csv_path,
                                'bit_fields': bit_fields,
                                'reg_name_full': addr_row[1] if len(addr_row) > 1 else ''
                            }
    return None


def find_register_by_address(search_addr, csv_dir=None):
    """通过物理地址查找寄存器信息"""
    if csv_dir is None:
        csv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'csv_files')

    base_addr = read_base_addr()

    try:
        if isinstance(search_addr, str):
            search_addr = search_addr.lower()
            if search_addr.startswith('0x'):
                target_addr = int(search_addr, 16)
            else:
                target_addr = int(search_addr, 0)
        else:
            target_addr = int(search_addr)
    except ValueError:
        return None

    matched_module = None
    offset = 0
    sorted_modules = sorted(base_addr.items(), key=lambda x: x[1], reverse=True)
    for module, base in sorted_modules:
        if base <= target_addr:
            matched_module = module
            offset = target_addr - base
            break

    if not matched_module:
        return None

    csv_path = os.path.join(csv_dir, f"{matched_module}.csv")

    if not os.path.exists(csv_path):
        return None

    with open(csv_path, 'r') as f:
        reader = csv.reader(f, delimiter=';')
        rows = list(reader)

        for i, row in enumerate(rows):
            if row and row[0] and row[0].startswith('0x'):
                try:
                    row_offset = int(row[0], 16)
                    if row_offset == offset:
                        addr_row = row
                        base = base_addr[matched_module]
                        default_hex, default_32bit, default_dec, bit_fields = calculate_reg_default(rows, i)

                        return {
                            'reg_name': addr_row[1] if len(addr_row) > 1 else '',
                            'module': matched_module,
                            'base_addr': f"0x{base:08X}",
                            'offset': addr_row[0],
                            'full_addr': f"0x{target_addr:08X}",
                            'bit_pos': '',
                            'bit_default': '',
                            'reg_default': default_hex,
                            'reg_default_binary': default_32bit,
                            'reg_default_dec': default_dec,
                            'csv_file': f"{matched_module}.csv",
                            'csv_path': csv_path,
                            'bit_fields': bit_fields,
                            'reg_name_full': addr_row[1] if len(addr_row) > 1 else ''
                        }
                except ValueError:
                    continue

    return None


def print_register_info(info, query_str, is_address=False):
    """打印寄存器信息"""
    print(f"{'='*60}")
    if is_address:
        print(f"寄存器地址查询结果: {query_str}")
    else:
        print(f"寄存器查询结果: {query_str}")
    print(f"{'='*60}")
    print(f"所在文件: {info['csv_file']}")
    print(f"文件路径: {info['csv_path']}")
    print(f"所属模块: {info['module']}")
    print(f"模块基地址: {info['base_addr']}")
    print(f"地址偏移: {info['offset']}")
    print(f"完整物理地址: {info['full_addr']}")
    if info.get('reg_name_full'):
        print(f"寄存器名称: {info['reg_name_full']}")

    if info.get('bit_fields'):
        print(f"\n位字段列表:")
        for field in info['bit_fields']:
            print(f"  {field['signal']:40s} {field['bit_pos']:10s} = {field['default']}")

    print(f"\n寄存器32bit默认值: {info['reg_default']} ({info['reg_default_dec']} 十进制)")
    print(f"二进制默认值: 0b{info['reg_default_binary']}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='E22寄存器查询工具 - 支持名称和地址查询')
    parser.add_argument('-c', '--csv-dir', help='CSV文件目录路径(默认使用当前目录下的csv_files)')
    parser.add_argument('-l', '--list-csv', action='store_true', help='列出所有可用的CSV文件')
    parser.add_argument('query', nargs='?', help='要查询的寄存器名称或物理地址(如0xc30270d8)')
    args = parser.parse_args()

    # 设置CSV目录
    csv_dir = args.csv_dir
    if csv_dir is None:
        csv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'csv_files')

    # 列出可用CSV文件
    if args.list_csv:
        print(f"{'='*60}")
        print(f"可用的CSV文件列表: {csv_dir}")
        print(f"{'='*60}")
        if os.path.exists(csv_dir):
            for filename in os.listdir(csv_dir):
                if filename.endswith('.csv'):
                    print(f"  - {filename}")
        else:
            print(f"CSV文件目录不存在: {csv_dir}")
        return

    # 检查是否提供了查询参数
    if args.query is None:
        print("错误: 请提供要查询的寄存器名称或物理地址")
        print("使用 --help 参数查看使用说明")
        return

    query = args.query.strip()

    is_address = False
    if query.startswith('0x') or (query.isdigit() and len(query) >= 7):
        is_address = True

    info = None
    if is_address:
        info = find_register_by_address(query, csv_dir)
        if not info:
            info = find_register_info(query, csv_dir)
            is_address = False
    else:
        info = find_register_info(query, csv_dir)

    if info:
        print_register_info(info, query, is_address=is_address)
    else:
        print(f"未找到寄存器: {query}")
        print("提示: 可以输入寄存器名称(如reg_bw_chg_dly_start)或物理地址(如0xc30270d8)")


if __name__ == '__main__':
    main()
