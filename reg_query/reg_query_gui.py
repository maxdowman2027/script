#!/usr/bin/env python3
"""
E22寄存器查询工具 - GUI版本
功能：
1. 输入目标寄存器名字，输出目标寄存器所在的32bit寄存器的地址
2. 输入目标寄存器物理地址，输出寄存器详细信息和所在CSV文件
3. 支持指定CSV文件路径
4. 列出所有可用的寄存器定义CSV文件
5. 将查询结果导出到文本文件
6. 可选：输入整寄存器 32bit 读回值，按 CSV 位域解析各信号取值
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


def parse_bit_range(bit_pos):
    """
    解析位域字符串，返回 (msb, lsb)。
    支持格式: [31:0], [7]；解析失败时默认 (31, 0)。
    """
    if not bit_pos:
        return 31, 0
    bit_pos = str(bit_pos).strip()
    m = re.search(r'\[(\d+)(?::(\d+))?\]', bit_pos)
    if not m:
        return 31, 0
    msb = int(m.group(1))
    lsb = int(m.group(2)) if m.group(2) is not None else msb
    if msb < lsb:
        msb, lsb = lsb, msb
    return msb, lsb


def parse_default_to_int(default_str):
    """
    解析默认值字符串(如 3'd2, 8'hff, 1'b0, d0)为整数。
    无法解析时返回 None。
    """
    if default_str is None:
        return None
    s = str(default_str).strip().lower()
    if not s:
        return None
    if s.endswith('d0'):
        return 0
    m = re.search(r"(\d+)'([bdh])?([0-9a-f]+)", s)
    if not m:
        return None
    base_type = m.group(2) or 'b'
    val_str = m.group(3)
    base = 2
    if base_type == 'd':
        base = 10
    elif base_type == 'h':
        base = 16
    try:
        return int(val_str, base)
    except ValueError:
        return None


def split_query_tokens(query_text):
    """解析查询框内容：逗号或换行分隔，忽略空项。"""
    queries = []
    for seg in query_text.split(','):
        for q2 in seg.split('\n'):
            q2 = q2.strip()
            if q2:
                queries.append(q2)
    return queries


def split_write_value_tokens(text):
    """
    解析写寄存器值输入：逗号或换行分隔，保留空项以便与查询项按位置对齐。
    例如 '0x1,,0x3' 表示第 2 个寄存器不写配置值（沿用 CSV 默认或模板）。
    """
    if text is None:
        return []
    raw = text.strip() if isinstance(text, str) else str(text).strip()
    if not raw:
        return []
    tokens = []
    for seg in raw.split(','):
        for line in seg.split('\n'):
            tokens.append(line.strip())
    return tokens


def align_write_tokens_to_queries(write_tokens, num_queries):
    """截断或尾部补空串，使长度与查询项数一致。"""
    if num_queries <= 0:
        return []
    out = write_tokens[:num_queries]
    while len(out) < num_queries:
        out.append('')
    return out


def parse_full_reg32_value(text):
    """
    解析 32bit 寄存器读回值（十六进制或十进制）。
    返回 (masked_uint32, None) 或 (None, 错误信息)。
    """
    if text is None:
        return None, None
    s = str(text).strip()
    if not s:
        return None, None
    try:
        v = int(s, 0)
    except ValueError:
        return None, f"32bit读值格式错误: {text}"
    if v < 0:
        return None, "32bit读值不支持负数"
    masked = v & 0xFFFFFFFF
    if v != masked:
        # 允许超过 32 位时仅取低 32 位，并在输出里说明
        pass
    return masked, None


def extract_bit_field_value(val32, msb, lsb):
    """从 32bit 无符号值中取出 [msb:lsb] 字段（含边界）。"""
    val32 &= 0xFFFFFFFF
    if msb < lsb:
        msb, lsb = lsb, msb
    w = msb - lsb + 1
    if w <= 0 or w > 32:
        return 0
    return (val32 >> lsb) & ((1 << w) - 1)


def decode_register_read_value(info, val32):
    """
    将 32bit 读回值按 CSV 位域拆成各信号取值。
    若无 bit_fields 但有 bit_pos（按名称命中子域），则只解析该域。
    """
    lines = []
    v = val32 & 0xFFFFFFFF
    lines.append(f"读回32bit: 0x{v:08X} ({v} 十进制)")
    lines.append(f"  二进制: 0b{bin(v)[2:].zfill(32)}")

    fields = list(info.get("bit_fields") or [])
    if not fields and info.get("bit_pos"):
        fields = [
            {
                "signal": info.get("reg_name") or "field",
                "bit_pos": info["bit_pos"],
                "default": info.get("bit_default", ""),
            }
        ]

    if not fields:
        lines.append("  (CSV 中无位域列表，无法按域拆分)")
        return "\n".join(lines)

    lines.append("\n按位域解析:")
    for field in fields:
        sig = str(field.get("signal", "")).strip() or "(unnamed)"
        bp = field.get("bit_pos", "")
        msb, lsb = parse_bit_range(bp)
        fv = extract_bit_field_value(v, msb, lsb)
        w = msb - lsb + 1
        frag = f"  {sig:40s} {str(bp):12s} [{msb}:{lsb}] = 0x{fv:X} ({fv} 十进制)"
        if w <= 16:
            frag += f"  bin:{bin(fv)[2:].zfill(w)}"
        lines.append(frag)

    return "\n".join(lines)


def parse_write_value_to_hex(write_value_text):
    """
    将用户输入的写值解析为十六进制字符串（0x...）。
    支持十六进制(0x)和十进制输入；空值返回(None, None)。
    """
    if write_value_text is None:
        return None, None
    s = str(write_value_text).strip()
    if not s:
        return None, None
    try:
        val = int(s, 0)
    except ValueError:
        return None, f"写寄存器值格式错误: {write_value_text}"
    if val < 0:
        return None, "写寄存器值不支持负数"
    return f"0x{val:X}", None


def generate_rw_commands(info, write_value_text=None):
    """
    根据查询结果生成读写命令：
    - 写命令模板: test_top.mem.wrm(addr , msb, lsb , <value_hex>)
    - 读命令: hex(test_top.mem.rdm(addr , msb, lsb))
    """
    full_addr = str(info.get('full_addr', '')).strip().lower()
    if not full_addr:
        full_addr = "0x00000000"
    msb, lsb = parse_bit_range(info.get('bit_pos', ''))
    read_cmd = f"hex(test_top.mem.rdm({full_addr} , {msb}, {lsb}))"
    write_cmd_template = f"test_top.mem.wrm({full_addr} , {msb}, {lsb} , <value_hex>)"

    default_val = None
    if info.get('bit_default'):
        default_val = parse_default_to_int(info.get('bit_default'))
    if default_val is None and info.get('reg_default'):
        try:
            default_val = int(str(info.get('reg_default')), 16)
        except ValueError:
            default_val = None

    write_cmd_default = None
    if default_val is not None:
        write_cmd_default = f"test_top.mem.wrm({full_addr} , {msb}, {lsb} , 0x{default_val:X})"

    configured_write_hex, write_parse_error = parse_write_value_to_hex(write_value_text)
    write_cmd_configured = None
    if configured_write_hex is not None:
        write_cmd_configured = f"test_top.mem.wrm({full_addr} , {msb}, {lsb} , {configured_write_hex})"

    write_cmd_for_execute = (
        write_cmd_configured
        or write_cmd_default
        or write_cmd_template
    )

    return {
        'msb': msb,
        'lsb': lsb,
        'read_cmd': read_cmd,
        'write_cmd_template': write_cmd_template,
        'write_cmd_default': write_cmd_default,
        'write_cmd_configured': write_cmd_configured,
        'write_cmd_for_execute': write_cmd_for_execute,
        'write_parse_error': write_parse_error,
    }


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


def format_register_info(
    info, write_value_text=None, reg_read_32=None, read_decode_error=None
):
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

    # 生成读写命令
    rw = generate_rw_commands(info, write_value_text=write_value_text)
    lines.append("\n寄存器读写命令:")
    lines.append(f"  位域范围: [{rw['msb']}:{rw['lsb']}]")
    lines.append(f"  读命令: {rw['read_cmd']}")
    lines.append(f"  写命令(模板): {rw['write_cmd_template']}")
    if rw.get('write_parse_error'):
        lines.append(f"  写值解析错误: {rw['write_parse_error']}")
    if rw.get('write_cmd_configured'):
        lines.append(f"  写命令(使用配置值): {rw['write_cmd_configured']}")
    if rw.get('write_cmd_default'):
        lines.append(f"  写命令(默认值示例): {rw['write_cmd_default']}")

    if read_decode_error:
        lines.append("\n32bit读值按位域解析:")
        lines.append(f"  错误: {read_decode_error}")
    elif reg_read_32 is not None:
        lines.append("\n32bit读值按位域解析:")
        lines.append(decode_register_read_value(info, reg_read_32))

    lines.append("=" * 60)

    return '\n'.join(lines)


class RegQueryGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("E22 寄存器查询工具")
        self.root.geometry("920x820")

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
        main_frame.rowconfigure(8, weight=1)
        main_frame.rowconfigure(10, weight=1)

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

        # 写寄存器值配置（可选，多项与查询按顺序一一对应）
        ttk.Label(main_frame, text="写寄存器值(可选):").grid(row=3, column=0, sticky=(tk.N, tk.W), pady=(0, 5))
        self.write_value_text = scrolledtext.ScrolledText(main_frame, height=4, wrap=tk.WORD)
        self.write_value_text.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        ttk.Label(
            main_frame,
            text="与查询顺序对应（逗号/换行）；仅填 1 个值且多条查询时作用于全部。\n"
                 "多项时用 ,, 占位跳过某一档。",
            justify=tk.LEFT,
        ).grid(row=3, column=2, sticky=tk.W, padx=(5, 0), pady=(0, 5))

        # 32bit 读回值（可选）：按位域拆成各信号取值；多项与查询顺序对应
        ttk.Label(main_frame, text="32bit读回值(可选):").grid(row=4, column=0, sticky=(tk.N, tk.W), pady=(0, 5))
        self.read32_value_text = scrolledtext.ScrolledText(main_frame, height=3, wrap=tk.WORD)
        self.read32_value_text.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        ttk.Label(
            main_frame,
            text="整寄存器读回值，按 CSV 位域解析。\n"
                 "与查询顺序对应；仅 1 个值且多条查询时作用于全部。\n"
                 "示例: 0xC30270D8 或 3277468120",
            justify=tk.LEFT,
        ).grid(row=4, column=2, sticky=tk.W, padx=(5, 0), pady=(0, 5))

        # 查询按钮
        ttk.Button(main_frame, text="查询", command=self.perform_query, style="Accent.TButton").grid(row=5, column=0, columnspan=3, pady=(10, 0))

        # 列出可用CSV文件按钮
        ttk.Button(main_frame, text="列出可用CSV文件", command=self.list_csv_files).grid(row=6, column=0, columnspan=3, pady=(5, 0))

        # 查询结果显示
        ttk.Label(main_frame, text="查询结果:").grid(row=7, column=0, sticky=tk.W, pady=(10, 5))
        self.result_text = scrolledtext.ScrolledText(main_frame, height=20)
        self.result_text.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # 命令输出（每行纯命令，可直接复制执行）
        ttk.Label(main_frame, text="命令输出(每行可直接执行):").grid(row=9, column=0, sticky=tk.W, pady=(0, 5))
        self.command_text = scrolledtext.ScrolledText(main_frame, height=10)
        self.command_text.grid(row=10, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # 导出按钮
        ttk.Button(main_frame, text="导出结果到文件", command=self.export_result).grid(row=11, column=0, columnspan=3, pady=(0, 5))

        # 状态栏
        self.status_var = tk.StringVar(value="准备就绪")
        ttk.Label(main_frame, textvariable=self.status_var, style="Status.TLabel").grid(row=12, column=0, columnspan=3, sticky=(tk.W, tk.E))

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
        self.command_text.delete(1.0, tk.END)

        write_raw = self.write_value_text.get(1.0, tk.END)
        read_raw = self.read32_value_text.get(1.0, tk.END)
        # 创建后台线程执行查询（写值/读值在主线程读取，避免 Tk 跨线程访问）
        thread = threading.Thread(
            target=self.query_thread, args=(query_text, write_raw, read_raw)
        )
        thread.daemon = True
        thread.start()

    def query_thread(self, query_text, write_raw, read_raw):
        """查询线程"""
        try:
            queries = split_query_tokens(query_text)
            write_tokens_full = split_write_value_tokens(write_raw)
            read_tokens_full = split_write_value_tokens(read_raw)

            results = []
            errors = []
            command_lines = []

            # 一条写值 + 多条查询：沿用旧行为，该写值作用于全部查询
            if (
                len(queries) > 1
                and len(write_tokens_full) == 1
                and write_tokens_full[0].strip()
            ):
                one = write_tokens_full[0].strip()
                write_aligned = [one] * len(queries)
            else:
                extra_n = 0
                if len(write_tokens_full) > len(queries):
                    extra_n = len(write_tokens_full) - len(queries)
                    write_tokens_full = write_tokens_full[: len(queries)]
                write_aligned = align_write_tokens_to_queries(
                    write_tokens_full, len(queries)
                )
                if extra_n > 0:
                    errors.append(
                        f"写寄存器值项数多于查询项，已忽略末尾 {extra_n} 个写值"
                    )

            # 32bit 读值：与写值相同的对齐与广播规则
            if (
                len(queries) > 1
                and len(read_tokens_full) == 1
                and read_tokens_full[0].strip()
            ):
                read_aligned = [read_tokens_full[0].strip()] * len(queries)
            else:
                read_extra = 0
                if len(read_tokens_full) > len(queries):
                    read_extra = len(read_tokens_full) - len(queries)
                    read_tokens_full = read_tokens_full[: len(queries)]
                read_aligned = align_write_tokens_to_queries(
                    read_tokens_full, len(queries)
                )
                if read_extra > 0:
                    errors.append(
                        f"32bit读回值项数多于查询项，已忽略末尾 {read_extra} 个读值"
                    )

            for idx, query in enumerate(queries):
                wtok = write_aligned[idx] if idx < len(write_aligned) else ''
                wv_for_cmd = wtok.strip() if wtok else None

                rtok = read_aligned[idx] if idx < len(read_aligned) else ''
                rtok_s = rtok.strip() if rtok else ''
                reg_read_32 = None
                read_decode_error = None
                if rtok_s:
                    reg_read_32, read_decode_error = parse_full_reg32_value(rtok_s)
                    if read_decode_error:
                        reg_read_32 = None

                if self.query_type.get() == "name":
                    info, error = find_register_info(query, self.csv_dir)
                else:
                    info, error = find_register_by_address(query, self.csv_dir)

                if error:
                    errors.append(f"查询 '{query}' 时出错: {error}")
                    continue

                rw = generate_rw_commands(info, write_value_text=wv_for_cmd)
                if rw.get('write_parse_error'):
                    errors.append(
                        f"查询 '{query}' 写值解析: {rw['write_parse_error']}"
                    )

                results.append(
                    format_register_info(
                        info,
                        write_value_text=wv_for_cmd,
                        reg_read_32=reg_read_32,
                        read_decode_error=read_decode_error,
                    )
                )
                command_lines.append(rw['read_cmd'])
                command_lines.append(rw['write_cmd_for_execute'])

            # 显示结果
            self.root.after(0, lambda: self.result_text.delete(1.0, tk.END))
            self.root.after(0, lambda: self.command_text.delete(1.0, tk.END))

            if results:
                self.root.after(0, lambda: self.result_text.insert(tk.END, '\n\n'.join(results) + '\n'))

            if errors:
                self.root.after(0, lambda: self.result_text.insert(tk.END, '\n' + '-'*60 + '\n查询错误:\n' + '\n'.join(errors) + '\n'))

            if command_lines:
                cmd_output = '\n'.join(command_lines) + '\n'
                self.root.after(0, lambda: self.command_text.insert(tk.END, cmd_output))

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
