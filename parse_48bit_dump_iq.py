#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unpack 64-bit #dump_data CSV into a 48-bit sample stream, then decode each
48-bit word into three 8-bit I/Q tap pairs.

64-bit → 48-bit packing (repeats every 3 x uint64 → 4 x uint48):
  s0 = w0[47:0]
  s1 = {w1[31:0], w0[63:48]}   (w1[31:0] = high 32, w0[63:48] = low 16)
  s2 = {w2[15:0], w1[63:48], w1[47:32]}
  s3 = {w2[63:48], w2[47:32], w2[31:16]}

48-bit field map (8-bit signed each):
  [7:0]   sample_i_0    [15:8]  sample_q_0
  [23:16] sample_i_1    [31:24] sample_q_1
  [39:32] sample_i_2    [47:40] sample_q_2

Downstream: use --merge-iq to flatten taps into continuous sample_i / sample_q
(columns compatible with merge_dump_3data_iq.py output).
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

# =============================================================================
# 配置区
# =============================================================================
INPUT_CSV = r"D:\test_data\E22_M2\260605\axi_dump_160M_data_parse"  # CSV 文件或含 CSV 的目录（目录时批量）
OUTPUT_CSV = ""  # 空 → 各输入同目录自动命名；目录批量时 -o 可指定输出目录
MERGE_IQ = True  # True → 输出 sample_i / sample_q 连续流（同 merge_dump_3data_iq）
KEEP_DUMP_DATA = False  # True → 保留源 #dump_data 列（每 48-bit 行重复所属 64-bit 组首 word）
DUMP_DATA_48_COL = "dump_data_48"  # 48bit_parse / merge_iq 均输出拆分后的原始 48-bit hex

MASK48 = (1 << 48) - 1
WORDS_PER_GROUP = 3
SAMPLES_PER_GROUP = 4
SAMPLE_BITS = 8

IQ_FIELDS: Tuple[Tuple[str, int, int], ...] = (
    ("sample_i_0", 0, 7),
    ("sample_q_0", 8, 15),
    ("sample_i_1", 16, 23),
    ("sample_q_1", 24, 31),
    ("sample_i_2", 32, 39),
    ("sample_q_2", 40, 47),
)


def twos_complement(value: int, bits: int) -> int:
    if value & (1 << (bits - 1)):
        value -= 1 << bits
    return value


def format_hex48(value: int) -> str:
    return f"0x{value & MASK48:012X}"


def _normalize_field(name: str) -> str:
    return (name or "").strip().lstrip("\ufeff")


def find_dump_column(fieldnames: Sequence[str]) -> str:
    for name in fieldnames:
        if "dump_data" in _normalize_field(name).lower():
            return _normalize_field(name)
    if fieldnames:
        return _normalize_field(fieldnames[0])
    raise ValueError("CSV has no header / dump_data column")


def parse_uint64_cell(cell: str) -> int:
    text = (cell or "").strip().rstrip(",")
    if not text:
        raise ValueError("empty dump cell")
    if text.lower().startswith("0x"):
        return int(text, 16)
    return int(text, 16)


def read_uint64_words(input_csv: str) -> Tuple[str, List[int]]:
    words: List[int] = []
    dump_col = ""
    with open(input_csv, newline="", encoding="utf-8") as fin:
        reader = csv.DictReader(fin)
        if not reader.fieldnames:
            raise ValueError("Input CSV has no header")
        fieldnames = [_normalize_field(n) for n in reader.fieldnames if n is not None]
        dump_col = find_dump_column(fieldnames)

        # DictReader keys may differ from normalized name (e.g. trailing space in header).
        raw_dump_key = reader.fieldnames[0] if reader.fieldnames else dump_col

        for row_no, row in enumerate(reader, start=2):
            cell = row.get(raw_dump_key, "")
            if not str(cell).strip():
                cell = row.get(dump_col, "")
            if not str(cell).strip():
                for value in row.values():
                    text = str(value or "").strip()
                    if text.lower().startswith("0x"):
                        cell = text
                        break
            try:
                words.append(parse_uint64_cell(str(cell)))
            except ValueError as exc:
                raise ValueError(f"{input_csv}:{row_no}: {exc}") from exc
    return dump_col, words


def unpack_group_to_48bit(w0: int, w1: int, w2: int) -> Tuple[int, int, int, int]:
    """Convert one 3 x uint64 group into 4 x uint48 samples."""
    s0 = w0 & MASK48
    s1 = ((w1 & 0xFFFFFFFF) << 16) | ((w0 >> 48) & 0xFFFF)
    s2 = (
        ((w2 & 0xFFFF) << 32)
        | (((w1 >> 48) & 0xFFFF) << 16)
        | ((w1 >> 32) & 0xFFFF)
    )
    s3 = (
        (((w2 >> 48) & 0xFFFF) << 32)
        | (((w2 >> 32) & 0xFFFF) << 16)
        | ((w2 >> 16) & 0xFFFF)
    )
    return s0, s1, s2, s3


def iter_48bit_from_uint64(words: Sequence[int]) -> Iterator[Tuple[int, int]]:
    """
    Yield (group_index, uint48_value) for every complete 3-word group.

    Trailing 1–2 words without a full group are skipped (see stats in main).
    """
    n = len(words)
    complete_groups = n // WORDS_PER_GROUP
    for g in range(complete_groups):
        base = g * WORDS_PER_GROUP
        w0, w1, w2 = words[base], words[base + 1], words[base + 2]
        for sample in unpack_group_to_48bit(w0, w1, w2):
            yield g, sample


def decode_48bit_iq(value: int) -> Dict[str, int]:
    """Extract six 8-bit signed I/Q fields from one 48-bit sample."""
    out: Dict[str, int] = {}
    for name, lo, hi in IQ_FIELDS:
        width = hi - lo + 1
        mask = (1 << width) - 1
        raw = (value >> lo) & mask
        out[name] = twos_complement(raw, width)
    return out


def format_hex64(value: int) -> str:
    return f"0x{value & ((1 << 64) - 1):016X}"


def build_output_fieldnames(
    *,
    merge_iq: bool,
    keep_dump_data: bool,
    dump_col: str,
) -> List[str]:
    fieldnames: List[str] = [DUMP_DATA_48_COL]
    if keep_dump_data:
        fieldnames.append(dump_col)
    if merge_iq:
        fieldnames.extend(["sample_i", "sample_q"])
    else:
        fieldnames.extend([name for name, _, _ in IQ_FIELDS])
    return fieldnames


def build_parsed_row(
    sample48: int,
    iq: Dict[str, int],
    *,
    merge_iq: bool,
    tap: Optional[int],
    keep_dump_data: bool,
    dump_col: str,
    group_first_word: int,
) -> Dict[str, object]:
    row: Dict[str, object] = {DUMP_DATA_48_COL: format_hex48(sample48)}
    if keep_dump_data:
        row[dump_col] = format_hex64(group_first_word)
    if merge_iq:
        if tap is None:
            raise ValueError("tap index required when merge_iq=True")
        row["sample_i"] = iq[f"sample_i_{tap}"]
        row["sample_q"] = iq[f"sample_q_{tap}"]
    else:
        row.update(iq)
    return row


OUTPUT_SUFFIX_48BIT = "_48bit_parse"
OUTPUT_SUFFIX_IQ_MERGED = "_iq_merged"


def default_output_path(input_csv: str, *, merge_iq: bool) -> str:
    base, ext = os.path.splitext(os.path.abspath(input_csv))
    suffix = OUTPUT_SUFFIX_IQ_MERGED if merge_iq else OUTPUT_SUFFIX_48BIT
    return f"{base}{suffix}{ext}"


def is_generated_output_csv(path: str) -> bool:
    """Skip outputs from this script when scanning an input directory."""
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    return stem.endswith(OUTPUT_SUFFIX_48BIT) or stem.endswith(OUTPUT_SUFFIX_IQ_MERGED)


def discover_input_csvs(input_path: str) -> List[str]:
    """
    Resolve input to one or more CSV files.

    - File path → single-element list
    - Directory → non-recursive sorted ``*.csv`` (excludes this script's outputs)
    """
    input_path = os.path.abspath(input_path)
    if os.path.isfile(input_path):
        return [input_path]
    if not os.path.isdir(input_path):
        raise FileNotFoundError(input_path)

    csvs: List[str] = []
    for name in sorted(os.listdir(input_path)):
        if not name.lower().endswith(".csv"):
            continue
        full = os.path.join(input_path, name)
        if not os.path.isfile(full):
            continue
        if is_generated_output_csv(full):
            continue
        csvs.append(full)

    if not csvs:
        raise FileNotFoundError(f"No input .csv files found in directory: {input_path}")
    return csvs


def resolve_output_csv_for_input(
    input_csv: str,
    output_csv: str,
    *,
    output_dir: str = "",
    merge_iq: bool,
) -> str:
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        stem = os.path.splitext(os.path.basename(input_csv))[0]
        suffix = OUTPUT_SUFFIX_IQ_MERGED if merge_iq else OUTPUT_SUFFIX_48BIT
        return os.path.join(os.path.abspath(output_dir), f"{stem}{suffix}.csv")
    if output_csv:
        return os.path.abspath(output_csv)
    return default_output_path(input_csv, merge_iq=merge_iq)


def parse_48bit_dump_iq(
    input_csv: str,
    output_csv: str = "",
    *,
    merge_iq: bool = MERGE_IQ,
    keep_dump_data: bool = KEEP_DUMP_DATA,
) -> Tuple[int, int, int]:
    """
    Parse one 64-bit dump CSV → 48-bit IQ rows.

    Returns (input_uint64_count, output_rows, skipped_tail_uint64).
    """
    input_csv = os.path.abspath(input_csv)
    if not os.path.isfile(input_csv):
        raise FileNotFoundError(input_csv)

    output_csv = output_csv or default_output_path(input_csv, merge_iq=merge_iq)
    output_csv = os.path.abspath(output_csv)
    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)

    dump_col, words = read_uint64_words(input_csv)
    skipped_tail = len(words) % WORDS_PER_GROUP
    if skipped_tail:
        print(
            f"[WARN] {skipped_tail} trailing 64-bit word(s) ignored "
            f"(need multiples of {WORDS_PER_GROUP})",
            file=sys.stderr,
        )

    parsed_rows: List[Dict[str, object]] = []
    group_first_word: Dict[int, int] = {}

    for g, sample48 in iter_48bit_from_uint64(words):
        if g not in group_first_word:
            group_first_word[g] = words[g * WORDS_PER_GROUP]
        iq = decode_48bit_iq(sample48)
        group_w0 = group_first_word[g]
        if merge_iq:
            for tap in range(3):
                parsed_rows.append(
                    build_parsed_row(
                        sample48,
                        iq,
                        merge_iq=True,
                        tap=tap,
                        keep_dump_data=keep_dump_data,
                        dump_col=dump_col,
                        group_first_word=group_w0,
                    )
                )
        else:
            parsed_rows.append(
                build_parsed_row(
                    sample48,
                    iq,
                    merge_iq=False,
                    tap=None,
                    keep_dump_data=keep_dump_data,
                    dump_col=dump_col,
                    group_first_word=group_w0,
                )
            )

    fieldnames = build_output_fieldnames(
        merge_iq=merge_iq,
        keep_dump_data=keep_dump_data,
        dump_col=dump_col,
    )

    with open(output_csv, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(parsed_rows)

    groups = len(words) // WORDS_PER_GROUP
    samples48 = groups * SAMPLES_PER_GROUP
    print(f"Input : {input_csv}")
    print(f"  64-bit words : {len(words)} ({groups} complete groups)")
    print(f"  48-bit samples: {samples48}")
    print(f"Output: {output_csv}")
    print(f"  rows         : {len(parsed_rows)}")
    print(f"  mode         : {'merge_iq' if merge_iq else '48bit_6col'}")
    if parsed_rows and not merge_iq:
        first = parsed_rows[0]
        print(
            "  first sample : "
            + ", ".join(f"{k}={first[k]}" for k in fieldnames if k.startswith("sample_"))
        )
    return len(words), len(parsed_rows), skipped_tail


def parse_48bit_dump_inputs(
    input_path: str,
    output_csv: str = "",
    *,
    merge_iq: bool = MERGE_IQ,
    keep_dump_data: bool = KEEP_DUMP_DATA,
) -> List[Tuple[str, int, int, int]]:
    """
    Parse one CSV or every input ``.csv`` in a directory.

    Returns list of (input_csv, uint64_count, output_rows, skipped_tail).
    """
    csv_files = discover_input_csvs(input_path)
    output_dir = ""

    if output_csv:
        abs_out = os.path.abspath(output_csv)
        if len(csv_files) > 1:
            if abs_out.lower().endswith(".csv") and not os.path.isdir(abs_out):
                raise ValueError(
                    f"Input directory has {len(csv_files)} .csv file(s); "
                    f"--output must be a directory, not a single .csv file: {output_csv!r}"
                )
            output_dir = abs_out
            os.makedirs(output_dir, exist_ok=True)
        elif os.path.isdir(abs_out):
            output_dir = abs_out
            output_csv = ""

    results: List[Tuple[str, int, int, int]] = []
    total_files = len(csv_files)

    if total_files > 1:
        print(f"Found {total_files} input .csv file(s) under {os.path.abspath(input_path)}")

    for idx, csv_path in enumerate(csv_files, start=1):
        if total_files > 1:
            print(f"\n=== [{idx}/{total_files}] {os.path.basename(csv_path)} ===")

        out_csv = resolve_output_csv_for_input(
            csv_path,
            output_csv,
            output_dir=output_dir,
            merge_iq=merge_iq,
        )
        n64, n_rows, skipped = parse_48bit_dump_iq(
            csv_path,
            out_csv,
            merge_iq=merge_iq,
            keep_dump_data=keep_dump_data,
        )
        results.append((csv_path, n64, n_rows, skipped))

    if total_files > 1:
        print(
            f"\n[OK] Batch done: {total_files} file(s), "
            f"{sum(r[1] for r in results)} total 64-bit word(s), "
            f"{sum(r[2] for r in results)} total output row(s)"
        )

    return results


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Unpack 64-bit #dump_data CSV to 48-bit stream and decode "
            "3x I/Q (8-bit) per 48-bit word."
        )
    )
    p.add_argument(
        "input_csv",
        nargs="?",
        default=INPUT_CSV,
        help="64-bit #dump_data CSV, or directory to process all input .csv files (non-recursive)",
    )
    p.add_argument(
        "-o",
        "--output",
        default=OUTPUT_CSV,
        help=(
            "Output CSV for single input, or output directory when input is a folder "
            "with multiple .csv files (default: <each_stem>_48bit_parse.csv or _iq_merged.csv)"
        ),
    )
    p.add_argument(
        "--merge-iq",
        action="store_true",
        default=MERGE_IQ,
        help="Flatten to sample_i / sample_q (like merge_dump_3data_iq.py)",
    )
    p.add_argument(
        "--keep-dump-data",
        action="store_true",
        default=KEEP_DUMP_DATA,
        help="Include source 64-bit #dump_data (first word of each 3-word group)",
    )
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        parse_48bit_dump_inputs(
            args.input_csv,
            args.output,
            merge_iq=args.merge_iq,
            keep_dump_data=args.keep_dump_data,
        )
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
