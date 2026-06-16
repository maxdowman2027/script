#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Decode 64-bit #dump_data CSV into dual-antenna 10-bit signed I/Q.

Each uint64 word drops the top 4 bits [63:60], keeping 60-bit payload [59:0].
Every 2 x 60-bit (120-bit) yields 3 x 40-bit samples; each 40-bit word maps:

  [9:0]   ch0_sample_q
  [19:10] ch0_sample_i
  [29:20] ch1_sample_q
  [39:30] ch1_sample_i

Cross-row sample (middle of the group):
  {word1[19:0], word0[59:40]}  -- previous row in lower bits.

Output: one row per 40-bit sample (3 rows per 2 input 64-bit words).
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
INPUT_CSV = r"D:\test_data\E22_M2\260616\phymode20_2ant\espwifi_modem_dump.20260616-071545-003_data.csv"
OUTPUT_CSV = ""  # 空 → <stem>_2ant_iq.csv
KEEP_DUMP_DATA_40 = True  # True → 输出 dump_data_40 列（原始 40-bit hex）
DUMP_DATA_40_COL = "dump_data_40"
OUTPUT_SUFFIX = "_2ant_iq"
RUN_VERIFY = False  # True → 逐组校验 64->40 拆包

MASK60 = (1 << 60) - 1
MASK40 = (1 << 40) - 1
MASK20 = (1 << 20) - 1
WORDS_PER_GROUP = 2
SAMPLES_PER_GROUP = 3
FIELD_BITS = 10

IQ_FIELDS: Tuple[Tuple[str, int, int], ...] = (
    ("ch0_sample_q", 0, 9),
    ("ch0_sample_i", 10, 19),
    ("ch1_sample_q", 20, 29),
    ("ch1_sample_i", 30, 39),
)


def twos_complement(value: int, bits: int) -> int:
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


def to_60bit(word: int) -> int:
    """Drop top 4 bits [63:60], keep [59:0]."""
    return word & MASK60


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


def unpack_group_to_40bit(w0: int, w1: int) -> Tuple[int, int, int]:
    """
    2 x 60-bit (drop [63:60] from each uint64) -> 3 x 40-bit.

      s0 = w0[39:0]
      s1 = {w1[19:0], w0[59:40]}
      s2 = w1[59:20]
    """
    a0 = to_60bit(w0)
    a1 = to_60bit(w1)
    s0 = a0 & MASK40
    s1 = ((a1 & MASK20) << 20) | ((a0 >> 40) & MASK20)
    s2 = (a1 >> 20) & MASK40
    return s0, s1, s2


def unpack_group_bitstream(w0: int, w1: int) -> Tuple[int, int, int]:
    """Reference unpack via 120-bit concatenated stream."""
    stream = to_60bit(w0) | (to_60bit(w1) << 60)
    return tuple((stream >> (40 * i)) & MASK40 for i in range(SAMPLES_PER_GROUP))


def decode_40bit_iq(value: int) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for name, lo, hi in IQ_FIELDS:
        width = hi - lo + 1
        mask = (1 << width) - 1
        raw = (value >> lo) & mask
        out[name] = twos_complement(raw, width)
    return out


def format_hex40(value: int) -> str:
    return f"0x{value & MASK40:010X}"


def decode_2word_2ant_iq10(
    w0: int,
    w1: int,
    *,
    keep_dump_data_40: bool = KEEP_DUMP_DATA_40,
) -> List[Dict[str, object]]:
    """Return 3 output rows (one per 40-bit sample) from a 2-word group."""
    rows: List[Dict[str, object]] = []
    for sample40 in unpack_group_to_40bit(w0, w1):
        row: Dict[str, object] = decode_40bit_iq(sample40)
        if keep_dump_data_40:
            row = {DUMP_DATA_40_COL: format_hex40(sample40), **row}
        rows.append(row)
    return rows


def verify_group(w0: int, w1: int) -> None:
    fast = unpack_group_to_40bit(w0, w1)
    ref = unpack_group_bitstream(w0, w1)
    if fast != ref:
        raise ValueError(
            "64->40 unpack mismatch: "
            f"fast={[format_hex40(x) for x in fast]} "
            f"ref={[format_hex40(x) for x in ref]}"
        )


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


def parse_64bit_to_2ant_iq10(
    input_csv: str,
    output_csv: str = "",
    *,
    keep_dump_data_40: bool = KEEP_DUMP_DATA_40,
    run_verify: bool = RUN_VERIFY,
) -> Tuple[int, int]:
    """
    Parse one #dump_data CSV (streaming, 2 words -> 3 I/Q rows).

    Returns (input_uint64_count, output_rows).
    """
    input_csv = os.path.abspath(input_csv)
    if not os.path.isfile(input_csv):
        raise FileNotFoundError(input_csv)

    output_csv = output_csv or default_output_path(input_csv)
    output_csv = os.path.abspath(output_csv)
    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)

    fieldnames = [DUMP_DATA_40_COL, *[name for name, _, _ in IQ_FIELDS]] if keep_dump_data_40 else [name for name, _, _ in IQ_FIELDS]

    src_words = 0
    out_rows = 0
    pending: Optional[int] = None
    groups = 0

    with open(output_csv, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()

        for _line_no, word in iter_dump_words(input_csv):
            src_words += 1
            if pending is None:
                pending = word
                continue

            if run_verify:
                verify_group(pending, word)

            for row in decode_2word_2ant_iq10(
                pending,
                word,
                keep_dump_data_40=keep_dump_data_40,
            ):
                writer.writerow(row)
                out_rows += 1

            pending = None
            groups += 1

    skipped = 1 if pending is not None else 0
    if skipped:
        print(
            f"[WARN] {skipped} trailing 64-bit word(s) ignored "
            f"(need multiples of {WORDS_PER_GROUP})",
            file=sys.stderr,
        )

    if run_verify and groups:
        print(f"[OK] 64->40 unpack verified ({groups} group(s), {SAMPLES_PER_GROUP} samples/group)")

    print(f"Input : {input_csv}")
    print(f"  64-bit words : {src_words} ({groups} groups x {WORDS_PER_GROUP})")
    print(f"Output: {output_csv}")
    print(f"  rows         : {out_rows} ({SAMPLES_PER_GROUP} sample(s)/group)")
    print(f"  columns      : {', '.join(fieldnames)}")
    return src_words, out_rows


def parse_64bit_to_2ant_iq10_inputs(
    input_path: str,
    output_csv: str = "",
    *,
    keep_dump_data_40: bool = KEEP_DUMP_DATA_40,
    run_verify: bool = RUN_VERIFY,
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
            out_csv = str(Path(output_dir) / f"{Path(csv_path).stem}{OUTPUT_SUFFIX}.csv")
        elif len(csv_files) > 1 and output_csv:
            out_dir = Path(output_csv)
            if out_dir.is_dir():
                out_csv = str(out_dir / f"{Path(csv_path).stem}{OUTPUT_SUFFIX}.csv")

        n64, n_rows = parse_64bit_to_2ant_iq10(
            csv_path,
            out_csv,
            keep_dump_data_40=keep_dump_data_40,
            run_verify=run_verify,
        )
        results.append((csv_path, n64, n_rows))

    if len(csv_files) > 1:
        print(
            f"\n[OK] Batch done: {len(csv_files)} file(s), "
            f"{sum(r[2] for r in results)} total output row(s)"
        )
    return results


# Backward-compatible aliases
parse_60bit_40bit_2ant_iq = parse_64bit_to_2ant_iq10
parse_60bit_40bit_inputs = parse_64bit_to_2ant_iq10_inputs


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Decode 64-bit #dump_data CSV to dual-antenna 10-bit signed I/Q "
            "(drop [63:60]; 2 x 60-bit -> 3 x 40-bit samples per group)."
        )
    )
    p.add_argument(
        "input_csv",
        nargs="?",
        default=INPUT_CSV,
        help="Input *_data.csv or directory (non-recursive batch)",
    )
    p.add_argument(
        "-o",
        "--output",
        default=OUTPUT_CSV,
        help="Output CSV or output directory for batch",
    )
    p.add_argument(
        "--keep-dump-data-40",
        action="store_true",
        default=KEEP_DUMP_DATA_40,
        help="Include dump_data_40 hex column (default: on)",
    )
    p.add_argument(
        "--no-dump-data-40",
        action="store_true",
        help="Do not write dump_data_40 column",
    )
    p.add_argument(
        "--verify",
        action="store_true",
        default=RUN_VERIFY,
        help="Verify 64->40 unpack for each 2-word group",
    )
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = ""
    output_csv = args.output or ""
    if output_csv and Path(output_csv).suffix.lower() != ".csv" and not output_csv.endswith(OUTPUT_SUFFIX):
        output_dir = output_csv
        output_csv = ""

    keep_dump_data_40 = False if args.no_dump_data_40 else args.keep_dump_data_40

    try:
        parse_64bit_to_2ant_iq10_inputs(
            args.input_csv,
            output_csv,
            keep_dump_data_40=keep_dump_data_40,
            run_verify=args.verify,
            output_dir=output_dir,
        )
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
