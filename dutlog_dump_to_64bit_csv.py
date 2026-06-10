#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract 32-bit hex dump lines from ESP-IDF dutlog between
``Start Data Dump!`` and ``End Data Dump!``, pair consecutive words into
64-bit values (first = low 32, second = high 32), and write CSV.

A log may contain multiple dump blocks; each block is written to its own CSV
(``<stem>_dump001.csv``, ``<stem>_dump002.csv``, ...).

Also detects 3/4-word modem delimiter blocks (same rules as ``bin_to_64bit_csv.py``)
and optionally writes ``*_data.csv`` (delimiter stripped) and ``*_delim_report.csv``.

Input may be a single dutlog file or a directory: directory mode non-recursively
scans ``*.log`` / ``*.LOG`` and processes each file in sorted order.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Set, Tuple

from bin_to_64bit_csv import (
    DELIM_REPORT_SUFFIX,
    FILTERED_CSV_SUFFIX,
    DelimiterBlock,
    delimiter_skip_indices,
    find_delimiter_blocks,
    format_dump_hex,
    write_delimiter_report,
)

# =============================================================================
# 配置区
# =============================================================================
INPUT_LOG = r"D:\test_data\E22_M2\260610\tone_64bit\ch0\dutlog20260610-11-46-12.log"
OUTPUT_DIR = ""  # 空 → 与 log 同目录
START_MARKER = "Start Data Dump!"
END_MARKER = "End Data Dump!"
OUTPUT_STYLE = "dump"  # dump | full
WRITE_FILTERED_CSV = True  # 额外写 <stem>_dumpNNN_data.csv（去 delimiter）
WRITE_DELIM_REPORT = True  # 写 <stem>_dumpNNN_delim_report.csv

_HEX_LINE = re.compile(r"^0x([0-9A-Fa-f]{8})$")


@dataclass(frozen=True)
class DumpBlock:
    index: int  # 1-based
    words_32: Tuple[int, ...]
    meta: Optional[str] = None


def pair_low_high_to_uint64(low: int, high: int) -> int:
    return ((high & 0xFFFFFFFF) << 32) | (low & 0xFFFFFFFF)


def _parse_block_text(block: str) -> Tuple[List[int], Optional[str]]:
    words: List[int] = []
    meta: Optional[str] = None

    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = _HEX_LINE.match(line)
        if m:
            words.append(int(m.group(1), 16))
            continue
        if meta is None and ("start_addr" in line or "read_length" in line):
            meta = line

    return words, meta


def iter_dump_blocks(text: str) -> Iterator[DumpBlock]:
    """Yield every Start..End dump region in file order."""
    pos = 0
    block_no = 0

    while True:
        start = text.find(START_MARKER, pos)
        if start < 0:
            break

        end = text.find(END_MARKER, start + len(START_MARKER))
        if end < 0:
            raise ValueError(
                f"Unclosed dump block #{block_no + 1}: missing {END_MARKER!r}"
            )

        block_no += 1
        block_text = text[start + len(START_MARKER) : end]
        words, meta = _parse_block_text(block_text)
        yield DumpBlock(index=block_no, words_32=tuple(words), meta=meta)
        pos = end + len(END_MARKER)


def extract_all_dump_blocks(text: str) -> List[DumpBlock]:
    blocks = list(iter_dump_blocks(text))
    if not blocks:
        raise ValueError(
            f"No dump block found (markers: {START_MARKER!r} / {END_MARKER!r})"
        )
    return blocks


def words_to_uint64_list(words: Sequence[int], *, block_index: int) -> List[int]:
    if len(words) % 2:
        raise ValueError(
            f"Dump block #{block_index}: odd number of 32-bit words ({len(words)}); "
            "cannot pair low/high into 64-bit values."
        )
    out: List[int] = []
    for i in range(0, len(words), 2):
        out.append(pair_low_high_to_uint64(words[i], words[i + 1]))
    return out


def discover_log_files(input_path: str | Path) -> List[Path]:
    """
    Resolve input to one or more dutlog files.

    - File path → single-element list
    - Directory → non-recursive sorted ``*.log`` / ``*.LOG``
    """
    path = Path(input_path).resolve()
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(input_path)

    logs: List[Path] = []
    for entry in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        if entry.is_file() and entry.suffix.lower() == ".log":
            logs.append(entry)

    if not logs:
        raise FileNotFoundError(f"No .log files found in directory: {input_path}")
    return logs


def block_output_path(
    input_path: Path,
    block_index: int,
    *,
    output_dir: str | Path = "",
) -> Path:
    out_dir = Path(output_dir) if output_dir else input_path.parent
    return out_dir / f"{input_path.stem}_dump{block_index:03d}.csv"


def sibling_csv_path(output_csv: Path, suffix: str) -> Path:
    return output_csv.with_name(f"{output_csv.stem}{suffix}{output_csv.suffix}")


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


def write_uint64_csv(
    output_csv: Path,
    words: Sequence[int],
    *,
    output_style: str = OUTPUT_STYLE,
    skip: Optional[Set[int]] = None,
) -> int:
    """Write one CSV (full or filtered). Returns number of rows written."""
    skip = skip or set()
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    count = 0

    with open(output_csv, "w", newline="", encoding="utf-8") as fout:
        if output_style == "dump":
            fout.write("#dump_data \n")
            for idx, word in enumerate(words):
                if idx in skip:
                    continue
                _write_dump_word(fout, word)
                count += 1
        elif output_style == "full":
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
            out_idx = 0
            for idx, word in enumerate(words):
                if idx in skip:
                    continue
                _write_full_row(writer, out_idx, word)
                out_idx += 1
                count += 1
        else:
            raise ValueError(f"output_style must be 'dump' or 'full', got {output_style!r}")

    return count


def write_block_csvs(
    output_csv: Path,
    words_64: Sequence[int],
    delim_blocks: Sequence[DelimiterBlock],
    *,
    output_style: str = OUTPUT_STYLE,
    write_filtered_csv: bool = WRITE_FILTERED_CSV,
    filtered_suffix: str = FILTERED_CSV_SUFFIX,
    write_delim_report: bool = WRITE_DELIM_REPORT,
    delim_report_suffix: str = DELIM_REPORT_SUFFIX,
) -> Tuple[int, int, int]:
    """
    Write full CSV plus optional *_data.csv and *_delim_report.csv.

    Returns (total_words, data_words, delimiter_block_count).
    """
    skip = delimiter_skip_indices(delim_blocks)
    total_count = len(words_64)
    data_count = total_count - len(skip)

    write_uint64_csv(output_csv, words_64, output_style=output_style)

    filtered_csv = sibling_csv_path(output_csv, filtered_suffix)
    report_csv = sibling_csv_path(output_csv, delim_report_suffix)

    if write_filtered_csv:
        write_uint64_csv(
            filtered_csv,
            words_64,
            output_style=output_style,
            skip=skip,
        )
    if write_delim_report:
        write_delimiter_report(str(report_csv), delim_blocks)

    return total_count, data_count, len(delim_blocks)


def convert_dutlog_dump(
    input_log: str | Path,
    output_dir: str | Path = "",
    *,
    output_style: str = OUTPUT_STYLE,
    write_filtered_csv: bool = WRITE_FILTERED_CSV,
    filtered_suffix: str = FILTERED_CSV_SUFFIX,
    write_delim_report: bool = WRITE_DELIM_REPORT,
    delim_report_suffix: str = DELIM_REPORT_SUFFIX,
) -> List[Path]:
    input_path = Path(input_log)
    if not input_path.is_file():
        raise FileNotFoundError(input_log)

    output_style = output_style.lower()
    if output_style not in ("dump", "full"):
        raise ValueError("output_style must be 'dump' or 'full'")

    raw = input_path.read_bytes()
    text = raw.decode("utf-8", errors="replace")

    blocks = extract_all_dump_blocks(text)
    out_paths: List[Path] = []

    print(f"Input : {input_path}")
    print(f"Blocks: {len(blocks)}")
    if write_filtered_csv:
        print(f"Filtered suffix: {filtered_suffix!r} (remove 3/4-word delimiter blocks)")
    if write_delim_report:
        print(f"Report suffix  : {delim_report_suffix!r}")

    for block in blocks:
        words_64 = words_to_uint64_list(block.words_32, block_index=block.index)
        out_path = block_output_path(input_path, block.index, output_dir=output_dir)
        delim_blocks = find_delimiter_blocks(words_64)
        total, data, n_delim = write_block_csvs(
            out_path,
            words_64,
            delim_blocks,
            output_style=output_style,
            write_filtered_csv=write_filtered_csv,
            filtered_suffix=filtered_suffix,
            write_delim_report=write_delim_report,
            delim_report_suffix=delim_report_suffix,
        )
        out_paths.append(out_path)

        print(f"--- block {block.index:03d} ---")
        if block.meta:
            print(f"Meta  : {block.meta}")
        print(f"32-bit words: {len(block.words_32)}")
        print(f"64-bit words: {total}")
        print(f"Output: {out_path}")
        if write_filtered_csv:
            filtered_path = sibling_csv_path(out_path, filtered_suffix)
            print(
                f"Filtered: {filtered_path} "
                f"({data} data word(s), {total - data} delimiter word(s) in {n_delim} block(s))"
            )
            out_paths.append(filtered_path)
        if write_delim_report:
            report_path = sibling_csv_path(out_path, delim_report_suffix)
            print(f"Report : {report_path} ({n_delim} delimiter block(s))")
            out_paths.append(report_path)
        if words_64:
            print(f"First : {format_dump_hex(words_64[0])}")
            print(f"Last  : {format_dump_hex(words_64[-1])}")

        lost_blocks = [b for b in delim_blocks if b.data_lost_flag]
        if lost_blocks:
            total_lost = sum(b.lost_bytes for b in lost_blocks)
            print(
                f"[WARN] {len(lost_blocks)} delimiter block(s) report data loss, "
                f"total {total_lost} bytes",
                file=sys.stderr,
            )

    return out_paths


def convert_dutlog_inputs(
    input_path: str | Path,
    output_dir: str | Path = "",
    *,
    output_style: str = OUTPUT_STYLE,
    write_filtered_csv: bool = WRITE_FILTERED_CSV,
    filtered_suffix: str = FILTERED_CSV_SUFFIX,
    write_delim_report: bool = WRITE_DELIM_REPORT,
    delim_report_suffix: str = DELIM_REPORT_SUFFIX,
) -> List[Tuple[Path, List[Path]]]:
    """
    Convert one dutlog or every ``.log`` in a directory.

    Returns list of (input_log, output_csv_paths).
    """
    log_files = discover_log_files(input_path)
    results: List[Tuple[Path, List[Path]]] = []

    if len(log_files) > 1:
        print(f"Found {len(log_files)} .log file(s) under {Path(input_path).resolve()}")

    for idx, log_path in enumerate(log_files, start=1):
        if len(log_files) > 1:
            print(f"\n=== [{idx}/{len(log_files)}] {log_path.name} ===")
        out_paths = convert_dutlog_dump(
            log_path,
            output_dir,
            output_style=output_style,
            write_filtered_csv=write_filtered_csv,
            filtered_suffix=filtered_suffix,
            write_delim_report=write_delim_report,
            delim_report_suffix=delim_report_suffix,
        )
        results.append((log_path, out_paths))

    if len(log_files) > 1:
        print(f"\n[OK] Batch done: {len(log_files)} log file(s)")

    return results


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Parse dutlog Start/End Data Dump blocks: pair 32-bit hex lines "
            "(low, high) into 64-bit CSV. Multiple blocks -> multiple CSV files. "
            "Detects 3/4-word delimiter gaps like bin_to_64bit_csv.py."
        )
    )
    parser.add_argument(
        "input_log",
        nargs="?",
        default=INPUT_LOG,
        help="dutlog file or directory to scan for .log files (non-recursive batch)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=OUTPUT_DIR,
        help="output directory (default: same dir as log; files: <stem>_dumpNNN.csv)",
    )
    parser.add_argument(
        "--style",
        choices=("dump", "full"),
        default=OUTPUT_STYLE,
        help="dump: #dump_data only; full: index + split columns",
    )
    parser.add_argument(
        "--no-filtered",
        action="store_true",
        help="Do not write delimiter-stripped _data.csv",
    )
    parser.add_argument(
        "--filtered-suffix",
        default=FILTERED_CSV_SUFFIX,
        help="Suffix before .csv for filtered output (default: _data)",
    )
    parser.add_argument(
        "--no-delim-report",
        action="store_true",
        help="Do not write _delim_report.csv",
    )
    parser.add_argument(
        "--delim-report-suffix",
        default=DELIM_REPORT_SUFFIX,
        help="Suffix for delimiter report CSV (default: _delim_report)",
    )
    args = parser.parse_args(argv)

    try:
        convert_dutlog_inputs(
            args.input_log,
            args.output_dir,
            output_style=args.style,
            write_filtered_csv=not args.no_filtered,
            filtered_suffix=args.filtered_suffix,
            write_delim_report=not args.no_delim_report,
            delim_report_suffix=args.delim_report_suffix,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
