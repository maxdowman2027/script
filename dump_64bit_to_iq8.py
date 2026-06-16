#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Directly decode 64-bit #dump_data CSV into 8-bit signed I/Q.

Single mode (default): consecutive (q, i) byte pairs from low to high:
  [7:0]   -> sample_q
  [15:8]  -> sample_i
  ... (4 pairs per 64-bit word by default)

2ant mode: dual-antenna byte order per 32-bit chunk (low to high):
  [7:0]   -> ch0_sample_q
  [15:8]  -> ch0_sample_i
  [23:16] -> ch1_sample_q
  [31:24] -> ch1_sample_i
  ... repeated (2 dual-antenna samples per 64-bit word by default)

Output: one row per sample (single: one q/i pair; 2ant: ch0 + ch1 q/i).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

# =============================================================================
# 配置区
# =============================================================================
INPUT_CSV = r"D:\test_data\E22_M2\260616\phymode20_2ant\2\espwifi_modem_dump.20260616-072927-004_data.csv"
OUTPUT_CSV = ""  # 空 → <stem>_iq8.csv
IQ_MODE = "2ant"  # single | 2ant
PAIRS_PER_WORD = 4  # single: (q,i) pairs per 64-bit word (1-4)
SAMPLES_PER_WORD_2ANT = 2  # 2ant: dual-antenna samples per 64-bit word (1-2)
KEEP_DUMP_DATA = True  # True → 输出源 64-bit dump_data 列
KEEP_RAW_CHUNK = True  # True → 输出本行对应的原始拆分 hex（16/32-bit）
OUTPUT_SUFFIX = "_iq8"

SINGLE_FIELDS = ("sample_q", "sample_i")
TWO_ANT_FIELDS = ("ch0_sample_q", "ch0_sample_i", "ch1_sample_q", "ch1_sample_i")
DUMP_COL = "dump_data"
DUMP_DATA_16_COL = "dump_data_16"  # single: 本行 16-bit 原始块
DUMP_DATA_32_COL = "dump_data_32"  # 2ant: 本行 32-bit 原始块
IQMode = str  # "single" | "2ant"


def twos_complement(value: int, bits: int = 8) -> int:
    if value & (1 << (bits - 1)):
        value -= 1 << bits
    return value


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
    return int(text, 16)


def iter_dump_words(input_csv: str) -> Iterator[Tuple[int, int]]:
    with open(input_csv, newline="", encoding="utf-8") as fin:
        reader = csv.DictReader(fin)
        if not reader.fieldnames:
            raise ValueError("Input CSV has no header")
        fieldnames = [_normalize_field(n) for n in reader.fieldnames if n is not None]
        dump_col = find_dump_column(fieldnames)
        raw_key = reader.fieldnames[0] if reader.fieldnames else dump_col

        for line_no, row in enumerate(reader, start=2):
            cell = row.get(raw_key, "") or row.get(dump_col, "")
            if not str(cell).strip():
                for value in row.values():
                    text = str(value or "").strip()
                    if text.lower().startswith("0x"):
                        cell = text
                        break
            if not str(cell).strip():
                continue
            try:
                yield line_no, parse_uint64_cell(str(cell))
            except ValueError as exc:
                raise ValueError(f"{input_csv}:{line_no}: {exc}") from exc


def decode_uint64_iq8_pairs(
    word: int,
    *,
    pairs: int = PAIRS_PER_WORD,
    keep_raw_chunk: bool = KEEP_RAW_CHUNK,
) -> List[Dict[str, object]]:
    """Single mode: one row dict per (q, i) pair from low 16-bit chunks upward."""
    out: List[Dict[str, object]] = []
    for n in range(pairs):
        shift = n * 16
        chunk = (word >> shift) & 0xFFFF
        q_raw = chunk & 0xFF
        i_raw = (chunk >> 8) & 0xFF
        row: Dict[str, object] = {
            "sample_q": twos_complement(q_raw),
            "sample_i": twos_complement(i_raw),
        }
        if keep_raw_chunk:
            row[DUMP_DATA_16_COL] = f"0x{chunk:04X}"
        out.append(row)
    return out


def decode_uint64_2ant_iq8(
    word: int,
    *,
    samples: int = SAMPLES_PER_WORD_2ANT,
    keep_raw_chunk: bool = KEEP_RAW_CHUNK,
) -> List[Dict[str, object]]:
    """
    2ant mode: one row per 32-bit chunk from LSB.

    Byte order per chunk: ch0_q, ch0_i, ch1_q, ch1_i
    """
    out: List[Dict[str, object]] = []
    for n in range(samples):
        base = n * 32
        chunk = (word >> base) & 0xFFFFFFFF
        row: Dict[str, object] = {
            "ch0_sample_q": twos_complement((chunk >> 0) & 0xFF),
            "ch0_sample_i": twos_complement((chunk >> 8) & 0xFF),
            "ch1_sample_q": twos_complement((chunk >> 16) & 0xFF),
            "ch1_sample_i": twos_complement((chunk >> 24) & 0xFF),
        }
        if keep_raw_chunk:
            row[DUMP_DATA_32_COL] = f"0x{chunk:08X}"
        out.append(row)
    return out


def default_output_path(input_csv: str) -> str:
    base, ext = os.path.splitext(os.path.abspath(input_csv))
    return f"{base}{OUTPUT_SUFFIX}{ext}"


def is_generated_output(path: str) -> bool:
    return Path(path).stem.lower().endswith(OUTPUT_SUFFIX)


def discover_input_csvs(input_path: str) -> List[str]:
    p = Path(input_path).resolve()
    if p.is_file():
        return [str(p)]
    if not p.is_dir():
        raise FileNotFoundError(input_path)

    csvs = [
        str(f)
        for f in sorted(p.iterdir(), key=lambda x: x.name.lower())
        if f.is_file() and f.suffix.lower() == ".csv" and not is_generated_output(str(f))
    ]
    if not csvs:
        raise FileNotFoundError(f"No input .csv files in directory: {input_path}")
    return csvs


def output_fieldnames(
    *,
    mode: IQMode,
    keep_dump_data: bool,
    keep_raw_chunk: bool,
) -> List[str]:
    raw_cols: List[str] = []
    if keep_dump_data:
        raw_cols.append(DUMP_COL)
    if keep_raw_chunk:
        raw_cols.append(DUMP_DATA_32_COL if mode == "2ant" else DUMP_DATA_16_COL)
    iq_cols = list(TWO_ANT_FIELDS if mode == "2ant" else SINGLE_FIELDS)
    return raw_cols + iq_cols


def dump_64bit_to_iq8(
    input_csv: str,
    output_csv: str = "",
    *,
    mode: IQMode = IQ_MODE,
    pairs_per_word: int = PAIRS_PER_WORD,
    samples_per_word_2ant: int = SAMPLES_PER_WORD_2ANT,
    keep_dump_data: bool = KEEP_DUMP_DATA,
    keep_raw_chunk: bool = KEEP_RAW_CHUNK,
) -> Tuple[int, int]:
    input_csv = os.path.abspath(input_csv)
    if not os.path.isfile(input_csv):
        raise FileNotFoundError(input_csv)

    output_csv = output_csv or default_output_path(input_csv)
    output_csv = os.path.abspath(output_csv)
    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)

    if mode == "single":
        if pairs_per_word < 1 or pairs_per_word > 4:
            raise ValueError("pairs_per_word must be 1..4 for a 64-bit word in single mode")
    else:
        if samples_per_word_2ant < 1 or samples_per_word_2ant > 2:
            raise ValueError("samples_per_word_2ant must be 1..2 for a 64-bit word in 2ant mode")

    fieldnames = output_fieldnames(
        mode=mode,
        keep_dump_data=keep_dump_data,
        keep_raw_chunk=keep_raw_chunk,
    )
    src_words = 0
    out_rows = 0

    with open(output_csv, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()

        for _line_no, word in iter_dump_words(input_csv):
            src_words += 1
            hex64 = f"0x{word & ((1 << 64) - 1):016X}"

            if mode == "2ant":
                decoded = decode_uint64_2ant_iq8(
                    word,
                    samples=samples_per_word_2ant,
                    keep_raw_chunk=keep_raw_chunk,
                )
            else:
                decoded = decode_uint64_iq8_pairs(
                    word,
                    pairs=pairs_per_word,
                    keep_raw_chunk=keep_raw_chunk,
                )

            for row_data in decoded:
                row: Dict[str, object] = dict(row_data)
                if keep_dump_data:
                    row[DUMP_COL] = hex64
                writer.writerow(row)
                out_rows += 1

    per_word = samples_per_word_2ant if mode == "2ant" else pairs_per_word
    print(f"Input : {input_csv}")
    print(f"  64-bit words : {src_words}")
    print(f"  mode         : {mode}")
    print(f"Output: {output_csv}")
    print(f"  rows         : {out_rows} ({per_word} sample(s)/word)")
    print(f"  columns      : {', '.join(fieldnames)}")
    return src_words, out_rows


def dump_64bit_to_iq8_inputs(
    input_path: str,
    output_csv: str = "",
    *,
    mode: IQMode = IQ_MODE,
    pairs_per_word: int = PAIRS_PER_WORD,
    samples_per_word_2ant: int = SAMPLES_PER_WORD_2ANT,
    keep_dump_data: bool = KEEP_DUMP_DATA,
    keep_raw_chunk: bool = KEEP_RAW_CHUNK,
    output_dir: str = "",
) -> List[Tuple[str, int, int]]:
    csv_files = discover_input_csvs(input_path)
    results: List[Tuple[str, int, int]] = []

    if len(csv_files) > 1:
        print(f"Found {len(csv_files)} input .csv file(s) under {Path(input_path).resolve()}")

    for idx, csv_path in enumerate(csv_files, start=1):
        if len(csv_files) > 1:
            print(f"\n=== [{idx}/{len(csv_files)}] {Path(csv_path).name} ===")

        out_csv = output_csv
        if output_dir:
            stem = Path(csv_path).stem
            out_csv = str(Path(output_dir) / f"{stem}{OUTPUT_SUFFIX}.csv")
        elif len(csv_files) > 1 and output_csv:
            out_dir = Path(output_csv)
            if out_dir.is_dir():
                out_csv = str(out_dir / f"{Path(csv_path).stem}{OUTPUT_SUFFIX}.csv")

        n64, n_rows = dump_64bit_to_iq8(
            csv_path,
            out_csv,
            mode=mode,
            pairs_per_word=pairs_per_word,
            samples_per_word_2ant=samples_per_word_2ant,
            keep_dump_data=keep_dump_data,
            keep_raw_chunk=keep_raw_chunk,
        )
        results.append((csv_path, n64, n_rows))

    if len(csv_files) > 1:
        print(
            f"\n[OK] Batch done: {len(csv_files)} file(s), "
            f"{sum(r[2] for r in results)} total output row(s)"
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Decode 64-bit #dump_data CSV to 8-bit signed I/Q. "
            "single: sample_q/i pairs; 2ant: ch0/ch1 q/i per 32-bit chunk."
        )
    )
    p.add_argument(
        "input_csv",
        nargs="?",
        default=INPUT_CSV,
        help="Input *_data.csv or directory (non-recursive batch)",
    )
    p.add_argument("-o", "--output", default=OUTPUT_CSV, help="Output CSV or output directory for batch")
    p.add_argument(
        "--mode",
        choices=("single", "2ant"),
        default=IQ_MODE,
        help="single: sample_q/i; 2ant: ch0/ch1 q/i (default: single)",
    )
    p.add_argument(
        "--pairs",
        type=int,
        default=PAIRS_PER_WORD,
        help="I/Q pairs per 64-bit word in single mode (1-4, default 4)",
    )
    p.add_argument(
        "--samples",
        type=int,
        default=SAMPLES_PER_WORD_2ANT,
        help="Dual-antenna samples per 64-bit word in 2ant mode (1-2, default 2)",
    )
    p.add_argument(
        "--keep-dump-data",
        action="store_true",
        default=KEEP_DUMP_DATA,
        help="Include source 64-bit dump_data hex column (default: on)",
    )
    p.add_argument(
        "--no-dump-data",
        action="store_true",
        help="Do not write dump_data column",
    )
    p.add_argument(
        "--no-raw-chunk",
        action="store_true",
        help="Do not write dump_data_16 / dump_data_32 per-row hex column",
    )
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = ""
    output_csv = args.output or ""
    if output_csv and Path(output_csv).suffix.lower() != ".csv" and not output_csv.endswith(OUTPUT_SUFFIX):
        output_dir = output_csv
        output_csv = ""

    keep_dump_data = False if args.no_dump_data else args.keep_dump_data
    keep_raw_chunk = not args.no_raw_chunk

    try:
        dump_64bit_to_iq8_inputs(
            args.input_csv,
            output_csv,
            mode=args.mode,
            pairs_per_word=args.pairs,
            samples_per_word_2ant=args.samples,
            keep_dump_data=keep_dump_data,
            keep_raw_chunk=keep_raw_chunk,
            output_dir=output_dir,
        )
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
