#!/usr/bin/env python3
"""
一个类似ag（The Silver Searcher）的快速文本搜索工具
在指定路径下搜索包含特定模式的文件和内容
Windows系统专用版本
"""

import os
import re
import sys
import argparse
import time


def search_in_file(file_path, pattern, case_sensitive=True):
    """
    在单个文件中搜索模式
    """
    matches = []
    try:
        # 检测文件编码，先尝试utf-8，失败则使用gbk（Windows常用编码）
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            with open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                content = f.read()

        if not case_sensitive:
            pattern = pattern.lower()
            content = content.lower()

        # 逐行搜索
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            if pattern in line:
                # Windows命令行支持ANSI颜色
                highlighted_line = line.replace(pattern, f"\033[31;1m{pattern}\033[0m")
                matches.append((line_num, highlighted_line))

    except Exception as e:
        pass

    return matches


def should_ignore(file_path, ignore_patterns):
    """
    检查文件是否应该被忽略
    """
    for pattern in ignore_patterns:
        if pattern in file_path:
            return True
    return False


def find_files(path, file_extensions=None, ignore_patterns=None):
    """
    递归查找符合条件的文件
    """
    if file_extensions is None:
        file_extensions = []

    if ignore_patterns is None:
        ignore_patterns = [
            '.git', '.hg', '.svn',
            '__pycache__', '.pyc', '.pyo',
            '.o', '.obj', '.exe', '.dll',
            '.swp', '.swo', '.~',
            '.zip', '.tar.gz', '.tar.bz2', '.rar', '.7z',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
        ]

    found_files = []

    for root, dirs, files in os.walk(path):
        # 从dirs中移除要忽略的目录
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), ignore_patterns)]

        for file_name in files:
            file_path = os.path.join(root, file_name)

            if should_ignore(file_path, ignore_patterns):
                continue

            # 检查文件扩展名
            if file_extensions:
                file_ext = os.path.splitext(file_name)[1].lower()
                if file_ext not in file_extensions:
                    continue

            found_files.append(file_path)

    return found_files


def format_result(file_path, matches):
    """
    格式化搜索结果
    """
    lines = []
    if matches:
        lines.append(f"{file_path}:")
        for line_num, line in matches:
            lines.append(f"    {line_num}: {line}")
    return lines


def main():
    parser = argparse.ArgumentParser(
        description='类似ag的快速文本搜索工具（Windows版本）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  搜索所有包含"error"的Python文件
  python my_ag.py "error" --ext .py

  在当前目录搜索包含"TODO"的文件（不区分大小写）
  python my_ag.py "TODO" --ignore-case

  在指定目录搜索
  python my_ag.py "function" "D:\\path\\to\\search"

  搜索包含正则表达式模式的文件
  python my_ag.py "def\\s+\\w+" --regex
        '''
    )

    parser.add_argument('pattern', help='要搜索的模式')
    parser.add_argument('path', nargs='?', default='.', help='搜索路径（默认当前目录）')
    parser.add_argument('--ext', '-e', action='append', help='文件扩展名（可以多次指定）')
    parser.add_argument('--ignore-case', '-i', action='store_true', help='不区分大小写搜索')
    parser.add_argument('--count', '-c', action='store_true', help='只显示匹配的文件计数')
    parser.add_argument('--list-files', '-l', action='store_true', help='只显示匹配的文件路径')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    parser.add_argument('--hidden', '-H', action='store_true', help='包含隐藏文件和目录')
    parser.add_argument('--regex', '-r', action='store_true', help='将模式作为正则表达式处理')

    args = parser.parse_args()

    # 处理文件扩展名
    file_extensions = None
    if args.ext:
        file_extensions = []
        for ext in args.ext:
            if not ext.startswith('.'):
                ext = f".{ext}"
            file_extensions.append(ext.lower())

    # 处理忽略模式
    ignore_patterns = None
    if not args.hidden:
        ignore_patterns = [
            '.git', '.hg', '.svn',
            '__pycache__', '.pyc', '.pyo',
            '.o', '.obj', '.exe', '.dll',
            '.swp', '.swo', '.~',
            '.zip', '.tar.gz', '.tar.bz2', '.rar', '.7z',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
        ]

    start_time = time.time()

    # 查找符合条件的文件
    if args.verbose:
        print(f"在 {args.path} 中搜索包含 '{args.pattern}' 的文件")

    files_to_search = find_files(args.path, file_extensions, ignore_patterns)

    if args.verbose:
        print(f"找到 {len(files_to_search)} 个文件需要检查")

    # 执行搜索
    matches_count = 0
    matched_files = []
    all_results = []

    for file_path in files_to_search:
        if args.regex:
            matches = search_in_file_regex(file_path, args.pattern, not args.ignore_case)
        else:
            matches = search_in_file(file_path, args.pattern, not args.ignore_case)

        if matches:
            matches_count += len(matches)
            matched_files.append(file_path)

            if args.list_files:
                all_results.append(file_path)
            elif args.count:
                all_results.append(f"{file_path}: {len(matches)}")
            else:
                all_results.extend(format_result(file_path, matches))

    # 输出结果
    if args.count:
        print(f"找到 {matches_count} 个匹配项，分布在 {len(matched_files)} 个文件中")
    elif args.list_files:
        for file_path in matched_files:
            print(file_path)
    else:
        for line in all_results:
            print(line)

    if args.verbose:
        elapsed_time = time.time() - start_time
        print(f"搜索完成，耗时 {elapsed_time:.2f} 秒")
        print(f"检查了 {len(files_to_search)} 个文件")
        print(f"找到了 {len(matched_files)} 个匹配的文件")
        print(f"找到了 {matches_count} 个匹配项")


def search_in_file_regex(file_path, pattern, case_sensitive=True):
    """
    使用正则表达式搜索文件内容
    """
    matches = []
    try:
        # 检测文件编码，先尝试utf-8，失败则使用gbk（Windows常用编码）
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            with open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                content = f.read()

        flags = re.IGNORECASE if not case_sensitive else 0

        # 逐行搜索
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            if re.search(pattern, line, flags=flags):
                # 高亮匹配内容
                highlighted_line = re.sub(pattern, lambda m: f"\033[31;1m{m.group()}\033[0m", line, flags=flags)
                matches.append((line_num, highlighted_line))

    except Exception as e:
        pass

    return matches


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n搜索被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"搜索过程中发生错误: {e}")
        sys.exit(1)
