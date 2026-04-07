#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def extract_fail_blocks(txt_file, output_file):
    # 打开结果文件
    with open(txt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    blocks = []
    current_block = []
    i = 0
    line_count = len(lines)

    while i < line_count:
        line = lines[i]

        # 检查是否是测试块开始标记
        if line.startswith('****************************'):
            if current_block:
                # 保存之前的块
                blocks.append(''.join(current_block))
                current_block = []

            # 开始新块
            current_block.append(line)
            i += 1

            # 继续读取直到下一个开始标记或文件结束
            while i < line_count and not lines[i].startswith('****************************'):
                current_block.append(lines[i])
                i += 1
        else:
            i += 1

    # 保存最后一个块
    if current_block:
        blocks.append(''.join(current_block))

    # 筛选包含 FAIL 的测试块
    fail_blocks = []
    for block in blocks:
        if 'Check' in block and 'FAIL' in block:
            fail_blocks.append(block)

    # 写入新文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for block in fail_blocks:
            f.write(block + '\n')

    print(f"成功提取 {len(fail_blocks)} 个包含 FAIL 的测试块到 {output_file}")

if __name__ == "__main__":
    txt_file = r"D:\users\gxu\e22_tx\spec_mask\resulttx_result_2026_03_18_1411.txt"
    output_file = r"D:\users\gxu\e22_tx\spec_mask\fail_blocks_2026_03_18_1411.txt"
    extract_fail_blocks(txt_file, output_file)
