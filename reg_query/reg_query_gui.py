#!/usr/bin/env python3
"""
E22寄存器查询工具 - GUI版本
功能：
1. 输入目标寄存器名字，输出目标寄存器所在的32bit寄存器的地址
2. 输入目标寄存器物理地址，输出寄存器详细信息和所在CSV文件
3. 支持指定CSV文件路径
4. 列出所有可用的寄存器定义CSV文件
5. 将查询结果导出到文本文件
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import csv
import re
import os
import sys
import threading
import time
import queue


# 获取脚本所在目录的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


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
        return None, f"错误: CSV文件目录不存在: {csv_dir}"

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
                            }, None
    return None, f"未找到寄存器: {reg_name}"


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
        return None, "地址格式错误"

    matched_module = None
    offset = 0
    sorted_modules = sorted(base_addr.items(), key=lambda x: x[1], reverse=True)
    for module, base in sorted_modules:
        if base <= target_addr:
            matched_module = module
            offset = target_addr - base
            break

    if not matched_module:
        return None, "未找到对应的模块"

    csv_path = os.path.join(csv_dir, f"{matched_module}.csv")

    if not os.path.exists(csv_path):
        return None, f"模块CSV文件不存在: {csv_path}"

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
                        }, None
                except ValueError:
                    continue

    return None, "未找到该地址的寄存器"


def format_register_info(info):
    """格式化寄存器信息为字符串"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"寄存器查询结果: {info['reg_name']}")
    lines.append("=" * 60)
    lines.append(f"所在文件: {info['csv_file']}")
    lines.append(f"文件路径: {info['csv_path']}")
    lines.append(f"所属模块: {info['module']}")
    lines.append(f"模块基地址: {info['base_addr']}")
    lines.append(f"地址偏移: {info['offset']}")
    lines.append(f"完整物理地址: {info['full_addr']}")
    if info.get('reg_name_full'):
        lines.append(f"寄存器名称: {info['reg_name_full']}")

    if info.get('bit_fields'):
        lines.append("\n位字段列表:")
        for field in info['bit_fields']:
            lines.append(f"  {field['signal']:40s} {field['bit_pos']:10s} = {field['default']}")

    lines.append(f"\n寄存器32bit默认值: {info['reg_default']} ({info['reg_default_dec']} 十进制)")
    lines.append(f"二进制默认值: 0b{info['reg_default_binary']}")
    lines.append("=" * 60)

    return '\n'.join(lines)


class RegQueryGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("E22 寄存器查询工具")
        self.root.geometry("900x700")

        self.csv_dir = os.path.join(SCRIPT_DIR, 'csv_files')

        self.setup_ui()

    def setup_ui(self):
        # 创建主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)

        # 查询方式选择
        self.query_type = tk.StringVar(value="name")
        ttk.Radiobutton(main_frame, text="按名称查询", variable=self.query_type, value="name").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Radiobutton(main_frame, text="按地址查询", variable=self.query_type, value="address").grid(row=0, column=1, sticky=tk.W, pady=(0, 5))

        # 查询输入框
        ttk.Label(main_frame, text="查询内容:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.query_entry = ttk.Entry(main_frame)
        self.query_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        self.query_entry.bind("<Return>", lambda x: self.perform_query())
        ttk.Label(main_frame, text="支持多个查询，用逗号或换行分隔").grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=(0, 5))

        # CSV路径选择
        ttk.Label(main_frame, text="CSV目录:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.csv_dir_entry = ttk.Entry(main_frame)
        self.csv_dir_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        self.csv_dir_entry.insert(0, self.csv_dir)
        ttk.Button(main_frame, text="浏览", command=self.browse_csv_dir).grid(row=2, column=2, padx=(5, 0), pady=(0, 5))

        # 查询按钮
        ttk.Button(main_frame, text="查询", command=self.perform_query, style="Accent.TButton").grid(row=3, column=0, columnspan=3, pady=(10, 0))

        # 列出可用CSV文件按钮
        ttk.Button(main_frame, text="列出可用CSV文件", command=self.list_csv_files).grid(row=4, column=0, columnspan=3, pady=(5, 0))

        # 查询结果显示
        ttk.Label(main_frame, text="查询结果:").grid(row=5, column=0, sticky=tk.W, pady=(10, 5))
        self.result_text = scrolledtext.ScrolledText(main_frame, height=20)
        self.result_text.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # 导出按钮
        ttk.Button(main_frame, text="导出结果到文件", command=self.export_result).grid(row=7, column=0, columnspan=3, pady=(0, 5))

        # 状态栏
        self.status_var = tk.StringVar(value="准备就绪")
        ttk.Label(main_frame, textvariable=self.status_var, style="Status.TLabel").grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E))

        # 创建样式
        style = ttk.Style()
        style.configure("Accent.TButton", foreground="black", background="#4CAF50")
        style.configure("Status.TLabel", foreground="blue")

    def browse_csv_dir(self):
        """浏览选择CSV文件目录"""
        directory = filedialog.askdirectory(initialdir=self.csv_dir)
        if directory:
            self.csv_dir = directory
            self.csv_dir_entry.delete(0, tk.END)
            self.csv_dir_entry.insert(0, self.csv_dir)
            self.status_var.set(f"CSV目录已更新: {self.csv_dir}")

    def perform_query(self):
        """执行查询"""
        query_text = self.query_entry.get().strip()
        if not query_text:
            messagebox.showwarning("警告", "请输入查询内容")
            return

        self.status_var.set("查询中...")
        self.result_text.delete(1.0, tk.END)

        # 创建后台线程执行查询
        thread = threading.Thread(target=self.query_thread, args=(query_text,))
        thread.daemon = True
        thread.start()

    def query_thread(self, query_text):
        """查询线程"""
        try:
            # 解析多个查询内容（支持逗号、换行分隔）
            queries = []
            # 按逗号分割
            split_by_comma = query_text.split(',')
            for q in split_by_comma:
                # 按换行分割
                split_by_newline = q.split('\n')
                for q2 in split_by_newline:
                    q2 = q2.strip()
                    if q2:
                        queries.append(q2)

            results = []
            errors = []

            for query in queries:
                if self.query_type.get() == "name":
                    info, error = find_register_info(query, self.csv_dir)
                else:
                    info, error = find_register_by_address(query, self.csv_dir)

                if error:
                    errors.append(f"查询 '{query}' 时出错: {error}")
                else:
                    results.append(format_register_info(info))

            # 显示结果
            self.root.after(0, lambda: self.result_text.delete(1.0, tk.END))

            if results:
                self.root.after(0, lambda: self.result_text.insert(tk.END, '\n\n'.join(results) + '\n'))

            if errors:
                self.root.after(0, lambda: self.result_text.insert(tk.END, '\n' + '-'*60 + '\n查询错误:\n' + '\n'.join(errors) + '\n'))

            self.root.after(0, lambda: self.status_var.set(f"查询完成: 成功 {len(results)} 个, 失败 {len(errors)} 个"))
        except Exception as e:
            self.root.after(0, lambda: self.result_text.insert(tk.END, f"查询错误: {str(e)}"))
            self.root.after(0, lambda: self.status_var.set("查询出错"))

    def list_csv_files(self):
        """列出可用的CSV文件"""
        if not os.path.exists(self.csv_dir):
            messagebox.showerror("错误", f"CSV目录不存在: {self.csv_dir}")
            return

        self.status_var.set("正在获取CSV文件列表...")
        self.result_text.delete(1.0, tk.END)

        try:
            csv_files = [f for f in os.listdir(self.csv_dir) if f.endswith('.csv')]
            if not csv_files:
                self.result_text.insert(tk.END, "未找到CSV文件")
            else:
                self.result_text.insert(tk.END, "可用的CSV文件列表:\n")
                for filename in csv_files:
                    file_path = os.path.join(self.csv_dir, filename)
                    file_size = os.path.getsize(file_path)
                    self.result_text.insert(tk.END, f"  - {filename} ({file_size} 字节)\n")
        except Exception as e:
            self.result_text.insert(tk.END, f"获取CSV文件列表失败: {str(e)}")

        self.status_var.set("准备就绪")

    def export_result(self):
        """导出查询结果到文件"""
        result_content = self.result_text.get(1.0, tk.END)
        if not result_content.strip():
            messagebox.showwarning("警告", "没有可导出的结果")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="reg_query_result.txt"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(result_content)
                messagebox.showinfo("成功", f"结果已导出到: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")


def main():
    root = tk.Tk()
    app = RegQueryGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
