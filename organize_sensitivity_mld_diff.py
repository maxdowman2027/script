#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整理已有灵敏度 *_result.csv：mld_en 宽表合并 + 差值 xlsx 着色。

核心逻辑在 wifi_rx_sensitivity.py（与 find_csv_in_matched_folders 灵敏度流程共用）。
find_csv 计算灵敏度后会自动写出 *_mld_wide.csv/.xlsx 并用差值画雷达图。

本脚本用于对目录下已生成的长表 CSV 做离线宽表整理。
"""

from __future__ import annotations

import argparse
import glob
import os
from typing import List, Tuple

import wifi_rx_sensitivity as wrx_sens

DEFAULT_INPUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "output",
    "sensitivity_out",
    "result",
)


def process_csv_file(
    input_path: str,
    output_csv_path: str,
    output_xlsx_path: str,
) -> Tuple[int, int, int]:
    import pandas as pd

    df = pd.read_csv(input_path)
    n_in = len(df)
    wide = wrx_sens.merge_mld_sensitivity_rows(df)
    n_out = len(wide)
    if n_out:
        wrx_sens.write_mld_wide_outputs(wide, output_csv_path, output_xlsx_path)
    return n_in, n_out, n_in - 2 * n_out


def collect_input_files(input_dir: str, pattern: str) -> List[str]:
    path = os.path.join(input_dir, pattern)
    return sorted(f for f in glob.glob(path) if os.path.isfile(f))


def main():
    parser = argparse.ArgumentParser(
        description="Offline: merge mld_en=0/1 in sensitivity *_result.csv to wide table."
    )
    parser.add_argument("--input_dir", default=DEFAULT_INPUT_DIR)
    parser.add_argument("--pattern", default="*_result.csv")
    parser.add_argument("--output_dir", default=None)
    parser.add_argument("--combined", default=None)
    parser.add_argument("--inplace", action="store_true")
    parser.add_argument(
        "--radar-dir",
        default=None,
        help="Also plot mld-diff radar PNGs into this directory",
    )
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input_dir)
    output_dir = (
        input_dir
        if args.inplace
        else os.path.abspath(args.output_dir or os.path.join(input_dir, "organized"))
    )

    files = collect_input_files(input_dir, args.pattern)
    if not files:
        print(f"No files matching {args.pattern} in {input_dir}")
        return

    import pandas as pd

    combined_parts: List[pd.DataFrame] = []
    print(f"Input: {input_dir} ({len(files)} file(s))")
    if not args.inplace:
        print(f"Output: {output_dir}")

    for fp in files:
        base = os.path.basename(fp)
        stem, _ = os.path.splitext(base)
        if args.inplace:
            csv_fp = os.path.splitext(fp)[0] + "_mld_wide.csv"
            xlsx_fp = os.path.splitext(fp)[0] + "_mld_wide.xlsx"
        else:
            csv_fp = os.path.join(output_dir, f"{stem}_mld_wide.csv")
            xlsx_fp = os.path.join(output_dir, f"{stem}_mld_wide.xlsx")

        n_in, n_out, n_drop = process_csv_file(fp, csv_fp, xlsx_fp)
        print(
            f"  {base}: {n_in} rows -> {n_out} merged rows "
            f"({n_drop} input rows not in full 0+1 pairs)"
        )

        if args.radar_dir and n_out:
            wide = pd.read_csv(csv_fp)
            pngs = wrx_sens.plot_sensitivity_mld_diff_radar(
                wide.to_dict(orient="records"),
                args.radar_dir,
            )
            print(f"    radar: {len(pngs)} PNG(s) -> {args.radar_dir}")

        if args.combined and n_out:
            combined_parts.append(pd.read_csv(csv_fp))

    if args.combined and combined_parts:
        comb_path = os.path.abspath(args.combined)
        parent = os.path.dirname(comb_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        pd.concat(combined_parts, ignore_index=True).to_csv(comb_path, index=False)
        print(f"Combined: {comb_path} ({sum(len(p) for p in combined_parts)} rows)")


if __name__ == "__main__":
    main()
