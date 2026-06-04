#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert raw binary dump (.bin) to CSV with 64-bit sample rows.

Each 8-byte word becomes one CSV row. Default output matches FPGA / modem dump
CSV used by tx_adcdump_data_parse.py (#dump_data column, 0x-prefixed hex).

espwifi_modem_dump frame delimiter (4 x 64-bit words, removed in *_data.csv):
  0x0000000000000000, 0x0000000000000000, 0x00000000ABABABAB, 0x55555555xxxxxxxx
Frame header low32: bit31 = data-loss flag; bit30:0 = lost length in 32-byte units.
"""

from __future__ import annotations

import argparse
import csv
import os
import struct
import sys
from dataclasses import dataclass
from typing import BinaryIO, Iterator, List, Optional, Sequence, Set, Tuple

# =============================================================================
# 配置区（直接改这里可免命令行）
# =============================================================================
INPUT_BIN = r"D:\test_data\E22_M2\260604\espwifi_modem_dump.20260604-033842-003.bin"
OUTPUT_CSV = ""  # 空 → 与输入同目录、同 stem + .csv
BYTEORDER = "little"  # espwifi_modem_dump .bin：按文件字节序读 uint64
OUTPUT_STYLE = "dump"  # dump | full
CHUNK_WORDS = 8192  # 流式读写的块大小（64-bit word 数）

# 完整 delimiter：4 个连续 64-bit word（仅整段匹配时才从 _data.csv 剔除）
DELIM_WORD_ZERO = 0x0000000000000000
DELIM_WORD_ABAB = 0x00000000ABABABAB  # low32=0xABABABAB, high32=0
DELIM_FRAME_HIGH32 = 0x55555555
DELIM_BLOCK_WORDS = 4


def is_abab_word(word: int) -> bool:
    return (word & 0xFFFFFFFF) == 0xABABABAB and ((word >> 32) & 0xFFFFFFFF) == 0


def is_frame_header_word(word: int) -> bool:
    return ((word >> 32) & 0xFFFFFFFF) == DELIM_FRAME_HIGH32


def match_delimiter_block_at(words: Sequence[int], start: int) -> Optional[int]:
    """
    Return frame-header word if words[start:start+4] is a delimiter block.

    Supports both stream orders seen in dumps:
    - doc order: 0, 0, ABAB, 0x55555555xxxxxxxx
    - on-wire order (E22): 0x55555555xxxxxxxx, ABAB, 0, 0
    """
    if start + DELIM_BLOCK_WORDS > len(words):
        return None
    w0, w1, w2, w3 = words[start : start + DELIM_BLOCK_WORDS]
    if (
        w0 == DELIM_WORD_ZERO
        and w1 == DELIM_WORD_ZERO
        and is_abab_word(w2)
        and is_frame_header_word(w3)
    ):
        return w3
    if (
        is_frame_header_word(w0)
        and is_abab_word(w1)
        and w2 == DELIM_WORD_ZERO
        and w3 == DELIM_WORD_ZERO
    ):
        return w0
    return None

WRITE_FILTERED_CSV = True  # 额外写出去 delimiter 的 <stem>_data.csv
FILTERED_CSV_SUFFIX = "_data"
WRITE_DELIM_REPORT = True  # 写 delimiter 解析报告 <stem>_delim_report.csv
DELIM_REPORT_SUFFIX = "_delim_report"


@dataclass(frozen=True)
class DelimiterBlock:
    """One matched 4-word delimiter gap in the raw word stream."""

    block_index: int
    start_word_index: int
    frame_header_word: int
    data_lost_flag: int
    lost_units_32b: int
    lost_bytes: int


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


def read_all_uint64_words(
    input_bin: str,
    *,
    byteorder: str = BYTEORDER,
    chunk_words: int = CHUNK_WORDS,
) -> List[int]:
    words: List[int] = []
    with open(input_bin, "rb") as fin:
        for _idx, word in iter_uint64_words(fin, byteorder=byteorder, chunk_words=chunk_words):
            words.append(word)
    return words


def parse_frame_header_word(word: int) -> Tuple[int, int, int]:
    """
    Parse 0x55555555xxxxxxxx frame header.

    low32 bit31 = data-loss flag (1 = gap had lost data)
    low32 bit30:0 = lost amount in 32-byte units
    """
    if not is_frame_header_word(word):
        high32 = (word >> 32) & 0xFFFFFFFF
        raise ValueError(
            f"frame header high32 expected 0x{DELIM_FRAME_HIGH32:08X}, got 0x{high32:08X}"
        )
    low32 = word & 0xFFFFFFFF
    data_lost_flag = (low32 >> 31) & 1
    lost_units_32b = low32 & 0x7FFFFFFF
    return data_lost_flag, lost_units_32b, lost_units_32b * 32


def find_delimiter_blocks(words: Sequence[int]) -> List[DelimiterBlock]:
    """Scan raw word list for complete 4-word delimiter sequences."""
    blocks: List[DelimiterBlock] = []
    i = 0
    n = len(words)
    block_index = 0
    while i <= n - DELIM_BLOCK_WORDS:
        header_word = match_delimiter_block_at(words, i)
        if header_word is not None:
            flag, units, lost_bytes = parse_frame_header_word(header_word)
            blocks.append(
                DelimiterBlock(
                    block_index=block_index,
                    start_word_index=i,
                    frame_header_word=header_word,
                    data_lost_flag=flag,
                    lost_units_32b=units,
                    lost_bytes=lost_bytes,
                )
            )
            block_index += 1
            i += DELIM_BLOCK_WORDS
        else:
            i += 1
    return blocks


def delimiter_skip_indices(blocks: Sequence[DelimiterBlock]) -> Set[int]:
    skip: Set[int] = set()
    for block in blocks:
        for offset in range(DELIM_BLOCK_WORDS):
            skip.add(block.start_word_index + offset)
    return skip


def default_output_path(input_bin: str) -> str:
    base, _ext = os.path.splitext(os.path.abspath(input_bin))
    return f"{base}.csv"


def sibling_output_path(output_csv: str, suffix: str) -> str:
    base, ext = os.path.splitext(os.path.abspath(output_csv))
    return f"{base}{suffix}{ext}"


def format_dump_hex(value: int, *, width: int = 16) -> str:
    """Format as 0xHEX with optional fixed width (64-bit default)."""
    if width > 0:
        return f"0x{value:0{width}X}"
    return f"0x{value:X}"


def _write_dump_word(fout, word: int) -> None:
    fout.write(f"{format_dump_hex(word)},\n")


def _write_full_row(writer, idx: int, word: int) -> None:
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


def write_delimiter_report(report_csv: str, blocks: Sequence[DelimiterBlock]) -> None:
    os.makedirs(os.path.dirname(report_csv) or ".", exist_ok=True)
    with open(report_csv, "w", newline="", encoding="utf-8") as fout:
        writer = csv.writer(fout)
        writer.writerow(
            [
                "block_index",
                "start_word_index",
                "frame_header_hex",
                "data_lost_flag",
                "lost_units_32B",
                "lost_bytes",
            ]
        )
        for block in blocks:
            writer.writerow(
                [
                    block.block_index,
                    block.start_word_index,
                    format_dump_hex(block.frame_header_word),
                    block.data_lost_flag,
                    block.lost_units_32b,
                    block.lost_bytes,
                ]
            )


def convert_bin_to_csv(
    input_bin: str,
    output_csv: str,
    *,
    byteorder: str = BYTEORDER,
    output_style: str = OUTPUT_STYLE,
    chunk_words: int = CHUNK_WORDS,
    write_filtered_csv: bool = WRITE_FILTERED_CSV,
    filtered_suffix: str = FILTERED_CSV_SUFFIX,
    write_delim_report: bool = WRITE_DELIM_REPORT,
    delim_report_suffix: str = DELIM_REPORT_SUFFIX,
) -> Tuple[int, int, int]:
    """
    Convert .bin to CSV.

    Returns (total_words, data_words, delimiter_block_count).
    Writes full dump to output_csv; optionally *_data.csv without 4-word delimiters
    and *_delim_report.csv with frame-header loss flags.
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

    filtered_csv = sibling_output_path(output_csv, filtered_suffix) if write_filtered_csv else ""
    report_csv = sibling_output_path(output_csv, delim_report_suffix) if write_delim_report else ""

    file_size = os.path.getsize(input_bin)
    print(f"Input : {input_bin} ({file_size} bytes)")
    print(f"Output: {output_csv}")
    if write_filtered_csv:
        print(f"Filtered: {filtered_csv} (remove {DELIM_BLOCK_WORDS}-word delimiter blocks)")
    if write_delim_report:
        print(f"Report : {report_csv}")
    print(f"Byte order: {byteorder}, style: {output_style}")

    words = read_all_uint64_words(input_bin, byteorder=byteorder, chunk_words=chunk_words)
    blocks = find_delimiter_blocks(words)
    skip = delimiter_skip_indices(blocks)

    total_count = len(words)
    data_count = total_count - len(skip)

    with open(output_csv, "w", newline="", encoding="utf-8") as fout:
        if output_style == "dump":
            fout.write("#dump_data \n")
            for word in words:
                _write_dump_word(fout, word)
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
            for idx, word in enumerate(words):
                _write_full_row(writer, idx, word)

    if write_filtered_csv:
        data_idx = 0
        with open(filtered_csv, "w", newline="", encoding="utf-8") as fout:
            if output_style == "dump":
                fout.write("#dump_data \n")
                for idx, word in enumerate(words):
                    if idx in skip:
                        continue
                    _write_dump_word(fout, word)
                    data_idx += 1
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
                for idx, word in enumerate(words):
                    if idx in skip:
                        continue
                    _write_full_row(writer, data_idx, word)
                    data_idx += 1

    if write_delim_report:
        write_delimiter_report(report_csv, blocks)

    lost_blocks = [b for b in blocks if b.data_lost_flag]
    total_lost_bytes = sum(b.lost_bytes for b in lost_blocks)

    print(f"[OK] Wrote {total_count} x 64-bit word(s) -> {output_csv}")
    if write_filtered_csv:
        print(
            f"[OK] Wrote {data_count} data word(s) "
            f"({len(skip)} delimiter word(s) in {len(blocks)} block(s)) -> {filtered_csv}"
        )
    if write_delim_report:
        print(f"[OK] Delimiter report: {len(blocks)} block(s) -> {report_csv}")
    if lost_blocks:
        print(
            f"[WARN] {len(lost_blocks)} delimiter block(s) report data loss, "
            f"total {total_lost_bytes} bytes"
        )

    return total_count, data_count, len(blocks)


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
    p.add_argument(
        "--no-filtered",
        action="store_true",
        help="Do not write delimiter-stripped _data.csv",
    )
    p.add_argument(
        "--filtered-suffix",
        default=FILTERED_CSV_SUFFIX,
        help="Suffix before .csv for filtered output (default: _data)",
    )
    p.add_argument(
        "--no-delim-report",
        action="store_true",
        help="Do not write _delim_report.csv",
    )
    p.add_argument(
        "--delim-report-suffix",
        default=DELIM_REPORT_SUFFIX,
        help="Suffix for delimiter report CSV (default: _delim_report)",
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
            write_filtered_csv=not args.no_filtered,
            filtered_suffix=args.filtered_suffix,
            write_delim_report=not args.no_delim_report,
            delim_report_suffix=args.delim_report_suffix,
        )
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
