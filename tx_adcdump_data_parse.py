#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parse #dump_data CSV: extract bit fields as signed or unsigned integers.

Directory input: scan ``*.csv`` in the folder (non-recursive by default); prefer
``*_data.csv`` from ``bin_to_64bit_csv.py``; skip ``*_adcdump.csv`` and related
outputs. Use ``-r`` for recursive search; ``-o out_dir`` for batch output directory.
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
INPUT_FILE = r"D:\test_data\E22_M2\260622\0x220\2\espwifi_modem_dump.20260622-123809-003_data.csv"
OUTPUT_FILE = ""  # 空 → <input_stem>_adcdump.csv
PRESET = "gain"
VALUE_TYPE = "unsigned"  # signed | unsigned
OUTPUT_SUFFIX = "_adcdump"
PREFERRED_INPUT_SUFFIX = "_data"
SKIP_OUTPUT_SUFFIXES = (
    OUTPUT_SUFFIX,
    "_iq8",
    "_2ant_iq",
    "_iq_merged",
    "_48bit_parse",
    "_delim_report",
    "_spec",
)

PRESETS: Dict[str, Dict[str, List[str]]] = {
    "3tap10": {
        "bit_fields": [
            "[9:0]",
            "[19:10]",
            "[29:20]",
            "[39:30]",
            "[49:40]",
            "[59:50]",
        ],
        "column_names": [
            "sample_i_0",
            "sample_q_0",
            "sample_i_1",
            "sample_q_1",
            "sample_i_2",
            "sample_q_2",
        ],
    },
    "2tap12": {
        "bit_fields": ["[11:0]", "[23:12]"],
        "column_names": ["sample_q", "sample_i"],
    },
    "gain": {
        "bit_fields": ["[23:21]" ,"[20:15]"],
        "column_names": ["lna" ,"vga"],
    },    
}


def twos_complement(value: int, bits: int) -> int:
    if value & (1 << (bits - 1)):
        value -= 1 << bits
    return value


def convert_field_value(extracted: int, bits: int, *, signed: bool) -> int:
    """Apply twos-complement decode or return raw unsigned field."""
    if signed:
        return twos_complement(extracted, bits)
    return extracted


def _normalize_field(name: str) -> str:
    return (name or "").strip().lstrip("\ufeff")


def find_dump_column(fieldnames: Sequence[str]) -> str:
    for name in fieldnames:
        if "dump_data" in _normalize_field(name).lower():
            return _normalize_field(name)
    if fieldnames:
        return _normalize_field(fieldnames[0])
    raise ValueError("CSV has no header / dump_data column")


def default_output_path(input_file: str, suffix: str = OUTPUT_SUFFIX) -> str:
    base, ext = os.path.splitext(os.path.abspath(input_file))
    return f"{base}{suffix}{ext}"


def is_generated_output_csv(path: str) -> bool:
    """Skip outputs from this script and related pipelines when scanning a folder."""
    stem = Path(path).stem.lower()
    return any(stem.endswith(suffix.lower()) for suffix in SKIP_OUTPUT_SUFFIXES)


def is_preferred_data_csv(path: str) -> bool:
    """``bin_to_64bit_csv`` filtered dump: ``<stem>_data.csv``."""
    return Path(path).stem.lower().endswith(PREFERRED_INPUT_SUFFIX.lower())


def _iter_csv_candidates(root: Path, *, recursive: bool) -> Iterator[Path]:
    if recursive:
        yield from sorted(root.rglob("*.csv"), key=lambda p: str(p).lower())
        return
    for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if entry.is_file() and entry.suffix.lower() == ".csv":
            yield entry


def discover_input_csvs(input_path: str, *, recursive: bool = False) -> List[str]:
    """
    Resolve input to one or more dump CSV files.

    - File path → single-element list
    - Directory → sorted ``*.csv`` (non-recursive by default)
    - When ``*_data.csv`` exists in the scan set, use only those
    - Excludes ``*_adcdump.csv`` and other generated outputs
    """
    p = Path(input_path).resolve()
    if p.is_file():
        return [str(p)]
    if not p.is_dir():
        raise FileNotFoundError(input_path)

    seen: set[str] = set()
    csvs: List[str] = []
    for entry in _iter_csv_candidates(p, recursive=recursive):
        full = str(entry.resolve())
        if full in seen:
            continue
        seen.add(full)
        if not entry.is_file():
            continue
        if is_generated_output_csv(full):
            continue
        csvs.append(full)

    preferred = [c for c in csvs if is_preferred_data_csv(c)]
    if preferred:
        csvs = preferred

    if not csvs:
        hint = " (try --recursive)" if not recursive else ""
        raise FileNotFoundError(f"No input .csv files found in directory: {input_path}{hint}")
    return csvs


def resolve_output_csv_for_input(
    input_csv: str,
    output_csv: str,
    *,
    output_dir: str = "",
    suffix: str = OUTPUT_SUFFIX,
) -> str:
    """Map one input CSV to its output path given CLI/config output options."""
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        stem = Path(input_csv).stem
        return str(Path(output_dir).resolve() / f"{stem}{suffix}.csv")
    if output_csv:
        return os.path.abspath(output_csv)
    return default_output_path(input_csv, suffix=suffix)


def parse_adcdump_csv(
    input_file: str,
    output_file: str = "",
    *,
    bit_fields: Sequence[str],
    column_names: Sequence[str],
    signed: bool = True,
) -> Tuple[str, int]:
    input_file = os.path.abspath(input_file)
    if not os.path.isfile(input_file):
        raise FileNotFoundError(input_file)

    output_file = output_file or default_output_path(input_file)
    output_file = os.path.abspath(output_file)
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

    if len(column_names) != len(bit_fields):
        column_names = [f"{field}_signed" for field in bit_fields]

    print(f"Input : {input_file}")
    print(f"Output: {output_file}")
    print(f"Value type: {'signed' if signed else 'unsigned'}")

    row_count = 0
    with open(input_file, mode="r", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames:
            raise ValueError("Input CSV has no header")

        dump_col = find_dump_column(reader.fieldnames)
        raw_key = reader.fieldnames[0]
        fieldnames = [dump_col] + list(column_names)

        with open(output_file, mode="w", newline="", encoding="utf-8") as out_file:
            writer = csv.DictWriter(out_file, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                cell = row.get(raw_key, row.get(dump_col, ""))
                new_row: Dict[str, object] = {dump_col: cell}

                try:
                    hex_value = str(cell).strip().rstrip(",")
                    value = int(hex_value, 16)

                    for i, field in enumerate(bit_fields):
                        if field.startswith("[") and field.endswith("]"):
                            high_bit, low_bit = map(int, field[1:-1].split(":"))
                            mask = (1 << (high_bit - low_bit + 1)) - 1
                            extracted = (value >> low_bit) & mask
                            bits = high_bit - low_bit + 1
                            new_row[column_names[i]] = convert_field_value(
                                extracted, bits, signed=signed
                            )
                except ValueError as exc:
                    print(f"[WARN] line {row_count + 2}: cannot parse {cell!r}: {exc}")
                    for col_name in column_names:
                        new_row[col_name] = ""

                writer.writerow(new_row)
                row_count += 1

    print(f"[OK] Parsed {row_count} row(s) -> {output_file}")
    return output_file, row_count


def parse_adcdump_with_preset(
    input_file: str,
    output_file: str = "",
    *,
    preset: str = PRESET,
    signed: bool = True,
) -> Tuple[str, int]:
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset {preset!r}; choose from {list(PRESETS)}")
    cfg = PRESETS[preset]
    return parse_adcdump_csv(
        input_file,
        output_file,
        bit_fields=cfg["bit_fields"],
        column_names=cfg["column_names"],
        signed=signed,
    )


def parse_adcdump_inputs(
    input_path: str,
    output_file: str = "",
    *,
    preset: str = PRESET,
    signed: bool = True,
    recursive: bool = False,
) -> List[Tuple[str, str, int]]:
    """
    Parse one ``*_data.csv`` or every eligible ``.csv`` in a directory.

    Returns list of (input_csv, output_csv, row_count).
    """
    csv_files = discover_input_csvs(input_path, recursive=recursive)
    resolved_output_dir = ""
    input_is_dir = Path(input_path).resolve().is_dir()

    if output_file:
        abs_out = os.path.abspath(output_file)
        treat_as_dir = (
            os.path.isdir(abs_out)
            or len(csv_files) > 1
            or (input_is_dir and not abs_out.lower().endswith(".csv"))
        )
        if treat_as_dir:
            if abs_out.lower().endswith(".csv") and not os.path.isdir(abs_out):
                raise ValueError(
                    f"Batch / directory input ({len(csv_files)} file(s)); "
                    f"--output must be a directory, not a single .csv file: {output_file!r}"
                )
            resolved_output_dir = abs_out
            os.makedirs(resolved_output_dir, exist_ok=True)
            output_file = ""

    results: List[Tuple[str, str, int]] = []
    total_files = len(csv_files)

    if total_files > 1:
        scope = "recursively " if recursive else ""
        print(f"Found {total_files} input .csv file(s) {scope}under {Path(input_path).resolve()}")

    for idx, csv_path in enumerate(csv_files, start=1):
        if total_files > 1:
            print(f"\n=== [{idx}/{total_files}] {Path(csv_path).name} ===")

        out_csv = resolve_output_csv_for_input(
            csv_path,
            output_file,
            output_dir=resolved_output_dir,
        )
        out_path, row_count = parse_adcdump_with_preset(
            csv_path,
            out_csv,
            preset=preset,
            signed=signed,
        )
        results.append((csv_path, out_path, row_count))

    if total_files > 1:
        print(
            f"\n[OK] Batch done: {total_files} file(s), "
            f"{sum(r[2] for r in results)} total parsed row(s)"
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Parse #dump_data bit fields to signed or unsigned column values."
    )
    p.add_argument(
        "input_csv",
        nargs="?",
        default=INPUT_FILE,
        help="Input *_data.csv, or a directory to batch-parse eligible .csv files",
    )
    p.add_argument(
        "-o",
        "--output",
        default=OUTPUT_FILE,
        help="Output CSV (single input) or output directory (directory input / batch)",
    )
    p.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="When input is a directory, search subfolders for .csv files",
    )
    p.add_argument(
        "--preset",
        choices=tuple(PRESETS),
        default=PRESET,
        help=f"Bit-field layout preset (default: {PRESET})",
    )
    value_group = p.add_mutually_exclusive_group()
    value_group.add_argument(
        "--signed",
        action="store_true",
        default=None,
        help="Twos-complement signed output (default)",
    )
    value_group.add_argument(
        "--unsigned",
        action="store_true",
        help="Raw unsigned field values (no sign extension)",
    )
    p.add_argument(
        "--value-type",
        choices=("signed", "unsigned"),
        default=None,
        help="Explicit value type (overrides --signed/--unsigned)",
    )
    return p


def resolve_signed_flag(args: argparse.Namespace) -> bool:
    if args.value_type is not None:
        return args.value_type == "signed"
    if args.unsigned:
        return False
    if args.signed:
        return True
    return VALUE_TYPE == "signed"


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        parse_adcdump_inputs(
            args.input_csv,
            args.output or "",
            preset=args.preset,
            signed=resolve_signed_flag(args),
            recursive=args.recursive,
        )
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
