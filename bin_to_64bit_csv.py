#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert raw binary dump (.bin) to CSV with 64-bit sample rows.

Each 8-byte word becomes one CSV row. Default output matches FPGA / modem dump
CSV used by tx_adcdump_data_parse.py (#dump_data column, 0x-prefixed hex).

Example input:
  D:\\test_data\\E22_M2\\260604\\espwifi_modem_dump.20260604-033842-003.bin
"""

from __future__ import annotations

import argparse
import csv
import os
import struct
import sys
from pathlib import Path
from typing import BinaryIO, Iterator, List, Optional, Tuple

# =============================================================================
# 配置区（直接改这里可免命令行）
# =============================================================================
INPUT_BIN = r"D:\test_data\E22_M2\260604\espwifi_modem_dump.20260604-033842-003.bin"
OUTPUT_CSV = ""  # 空 → 与输入同目录、同 stem + .csv
BYTEORDER = "big"  # espwifi_modem_dump .bin：按文件字节序 big-endian 读 uint64
OUTPUT_STYLE = "dump"  # dump | full
CHUNK_WORDS = 8192  # 流式读写的块大小（64-bit word 数）


def _word_struct(byteorder: str, count: int = 1) -> str:
    if byteorder not in ("big", "little"):
        raise ValueError(f"byteorder must be 'big' or 'little', got {byteorder!r}")
    endian = ">" if byteorder == "big" else "<"
    return f"{endian}{count}Q"


def iter_uint64_words(
    fp: BinaryIO,
    *,
    byteorder: str = "big",
    chunk_words: int = CHUNK_WORDS,
) -> Iterator[Tuple[int, int]]:
    """
    Yield (word_index, uint64_value) from a binary stream.

    Trailing bytes fewer than 8 are skipped with a warning printed to stderr.
    """
    word_idx = 0
    tail = b""

    while True:
        block = fp.read(chunk_words * 8)
        if not block and not tail:
            break
        block = tail + block
        n_full = len(block) // 8
        if n_full:
            words = struct.unpack(_word_struct(byteorder, n_full), block[: n_full * 8])
            for w in words:
                yield word_idx, w
                word_idx += 1
        tail = block[n_full * 8 :]
        if not block or (len(block) < chunk_words * 8 and not tail):
            break
        if len(block) < chunk_words * 8:
            break

    if tail:
        print(
            f"[WARN] Ignored {len(tail)} trailing byte(s) (not a full 64-bit word)",
            file=sys.stderr,
        )


def default_output_path(input_bin: str) -> str:
    base, _ext = os.path.splitext(os.path.abspath(input_bin))
    return f"{base}.csv"


def format_dump_hex(value: int, *, width: int = 16) -> str:
    """Format as 0xHEX with optional fixed width (64-bit default)."""
    if width > 0:
        return f"0x{value:0{width}X}"
    return f"0x{value:X}"


def convert_bin_to_csv(
    input_bin: str,
    output_csv: str,
    *,
    byteorder: str = BYTEORDER,
    output_style: str = OUTPUT_STYLE,
    chunk_words: int = CHUNK_WORDS,
) -> int:
    """
    Convert .bin to CSV. Returns number of 64-bit words written.
    """
    input_bin = os.path.abspath(input_bin)
    if not os.path.isfile(input_bin):
        raise FileNotFoundError(input_bin)

    output_csv = output_csv or default_output_path(input_bin)
    output_csv = os.path.abspath(output_csv)
    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)

    output_style = output_style.lower()
    if output_style not in ("dump", "full"):
        raise ValueError("output_style must be 'dump' or 'full'")

    file_size = os.path.getsize(input_bin)
    print(f"Input : {input_bin} ({file_size} bytes)")
    print(f"Output: {output_csv}")
    print(f"Byte order: {byteorder}, style: {output_style}")

    count = 0
    with open(input_bin, "rb") as fin, open(output_csv, "w", newline="", encoding="utf-8") as fout:
        if output_style == "dump":
            fout.write("#dump_data \n")
            for _idx, word in iter_uint64_words(fin, byteorder=byteorder, chunk_words=chunk_words):
                fout.write(f"{format_dump_hex(word)},\n")
                count += 1
        else:
            writer = csv.writer(fout)
            writer.writerow(
                [
                    "index",
                    "dump_data",
                    "uint64_dec",
                    "uint64_hex",
                    "low32_hex",
                    "high32_hex",
                ]
            )
            for idx, word in iter_uint64_words(fin, byteorder=byteorder, chunk_words=chunk_words):
                low = word & 0xFFFFFFFF
                high = (word >> 32) & 0xFFFFFFFF
                writer.writerow(
                    [
                        idx,
                        format_dump_hex(word),
                        word,
                        f"0x{word:016X}",
                        f"0x{low:08X}",
                        f"0x{high:08X}",
                    ]
                )
                count += 1

    print(f"[OK] Wrote {count} x 64-bit word(s) -> {output_csv}")
    return count


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convert binary dump (.bin) to CSV with 64-bit hex rows (#dump_data)."
    )
    p.add_argument(
        "input_bin",
        nargs="?",
        default=INPUT_BIN,
        help="Input .bin path",
    )
    p.add_argument(
        "-o",
        "--output",
        default=OUTPUT_CSV,
        help="Output CSV path (default: <input_stem>.csv)",
    )
    p.add_argument(
        "--byteorder",
        choices=("big", "little"),
        default=BYTEORDER,
        help="64-bit word byte order (default: big, matches espwifi_modem_dump .bin)",
    )
    p.add_argument(
        "--style",
        choices=("dump", "full"),
        default=OUTPUT_STYLE,
        help="dump: #dump_data column for tx_adcdump; full: index + hex/dec/32-bit split",
    )
    p.add_argument(
        "--chunk-words",
        type=int,
        default=CHUNK_WORDS,
        help="Stream read chunk size in 64-bit words",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        convert_bin_to_csv(
            args.input_bin,
            args.output,
            byteorder=args.byteorder,
            output_style=args.style,
            chunk_words=max(1, int(args.chunk_words)),
        )
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
