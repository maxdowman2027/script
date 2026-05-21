#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recursively find CSV files under folders whose names match a glob or regex pattern.

Optionally copy or move matched CSVs to a flat target directory (--copy-dir / --move-dir).
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shutil
from dataclasses import dataclass
from typing import Iterator, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class CsvHit:
    """One CSV file found under a matched folder."""

    matched_folder: str
    folder_name: str
    csv_path: str
    csv_name: str


@dataclass
class TransferStats:
    """Result of copy or move operations."""

    ok: int = 0
    skipped: int = 0
    errors: int = 0


def _name_matches(name: str, pattern: str, use_regex: bool) -> bool:
    if use_regex:
        return re.match(pattern, name) is not None
    return fnmatch.fnmatch(name, pattern)


def iter_matched_folder_paths(
    root_search_path: str,
    folder_pattern: str,
    *,
    use_regex_folder: bool = False,
) -> Iterator[Tuple[str, str]]:
    """
    Yield (dir_path, folder_basename) for every directory under root whose
    basename matches folder_pattern.
    """
    root = os.path.abspath(root_search_path)
    if not os.path.isdir(root):
        raise FileNotFoundError(f"Search root does not exist or is not a directory: {root}")

    for dir_path, _, _ in os.walk(root):
        base = os.path.basename(dir_path)
        if _name_matches(base, folder_pattern, use_regex_folder):
            yield dir_path, base


def find_csv_in_matched_folders(
    root_search_path: str,
    folder_pattern: str,
    csv_pattern: str = "*.csv",
    *,
    use_regex_folder: bool = False,
    use_regex_csv: bool = False,
    recursive_under_match: bool = True,
) -> List[CsvHit]:
    """
    1. Recursively scan root_search_path for folders matching folder_pattern.
    2. Under each matched folder, find CSV files (optionally in all subfolders).

    Returns a list of CsvHit sorted by csv_path.
    """
    hits: List[CsvHit] = []

    for folder_path, folder_name in iter_matched_folder_paths(
        root_search_path, folder_pattern, use_regex_folder=use_regex_folder
    ):
        if recursive_under_match:
            dir_walk = os.walk(folder_path)
        else:
            try:
                dir_walk = [(folder_path, [], os.listdir(folder_path))]
            except OSError:
                continue

        for sub_dir, _, file_names in dir_walk:
            for file_name in file_names:
                if not file_name.lower().endswith(".csv"):
                    continue
                if not _name_matches(file_name, csv_pattern, use_regex_csv):
                    continue
                csv_path = os.path.join(sub_dir, file_name)
                hits.append(
                    CsvHit(
                        matched_folder=folder_path,
                        folder_name=folder_name,
                        csv_path=os.path.abspath(csv_path),
                        csv_name=file_name,
                    )
                )

    hits.sort(key=lambda h: h.csv_path)
    return hits


def _dest_basename(hit: CsvHit, *, use_subpath_prefix: bool) -> str:
    if not use_subpath_prefix:
        return hit.csv_name
    rel = os.path.relpath(hit.csv_path, hit.matched_folder)
    return rel.replace("\\", "_").replace("/", "_")


def _resolve_dest_path(
    dest_dir: str,
    base_name: str,
    *,
    overwrite: bool,
    reserved: set,
) -> Optional[str]:
    """Pick a non-conflicting path under dest_dir; update reserved set on success."""
    dest_dir = os.path.abspath(dest_dir)
    target = os.path.join(dest_dir, base_name)

    if not overwrite and target in reserved:
        stem, ext = os.path.splitext(base_name)
        n = 1
        while True:
            candidate = f"{stem}_{n}{ext}"
            target = os.path.join(dest_dir, candidate)
            if target not in reserved and not os.path.exists(target):
                base_name = candidate
                break
            n += 1
    elif not overwrite and os.path.exists(target):
        stem, ext = os.path.splitext(base_name)
        n = 1
        while True:
            candidate = f"{stem}_{n}{ext}"
            target = os.path.join(dest_dir, candidate)
            if target not in reserved and not os.path.exists(target):
                base_name = candidate
                break
            n += 1

    reserved.add(target)
    return target


def transfer_csv_hits(
    hits: Sequence[CsvHit],
    dest_dir: str,
    *,
    move: bool,
    overwrite: bool = False,
    use_subpath_prefix: bool = False,
) -> TransferStats:
    """
    Copy or move each hit into dest_dir (flat layout).
    use_subpath_prefix: name files as <relative_path_under_matched_folder> with separators -> '_'.
    """
    stats = TransferStats()
    dest_dir = os.path.abspath(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    reserved: set = set()
    op = shutil.move if move else shutil.copy2
    op_name = "move" if move else "copy"

    for hit in hits:
        base_name = _dest_basename(hit, use_subpath_prefix=use_subpath_prefix)
        target = _resolve_dest_path(
            dest_dir, base_name, overwrite=overwrite, reserved=reserved
        )
        try:
            op(hit.csv_path, target)
            stats.ok += 1
            print(f"  OK {op_name}: {hit.csv_path} -> {target}")
        except PermissionError:
            stats.errors += 1
            print(f"  ERROR permission: {hit.csv_path}")
        except FileNotFoundError:
            stats.errors += 1
            print(f"  ERROR missing: {hit.csv_path}")
        except OSError as e:
            stats.errors += 1
            print(f"  ERROR {op_name} {hit.csv_path}: {e}")

    return stats


def _write_list_file(hits: Sequence[CsvHit], list_file: str) -> None:
    parent = os.path.dirname(os.path.abspath(list_file))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(list_file, "w", encoding="utf-8") as f:
        for h in hits:
            f.write(h.csv_path + "\n")


def _print_report(
    hits: Sequence[CsvHit],
    root_search_path: str,
    folder_pattern: str,
    csv_pattern: str,
    *,
    verbose: bool,
) -> None:
    folders = sorted({h.matched_folder for h in hits})
    print(f"Search root: {os.path.abspath(root_search_path)}")
    print(f"Folder pattern: {folder_pattern}")
    print(f"CSV pattern: {csv_pattern}")
    print(f"Matched folders: {len(folders)}")
    print(f"Matched CSV files: {len(hits)}")

    if verbose:
        for fp in folders:
            print(f"\n--- folder: {fp} ---")
            for h in hits:
                if h.matched_folder == fp:
                    print(f"  {h.csv_path}")
    elif hits:
        print("\nCSV paths (first 20; use -v for full tree or --list-out):")
        for h in hits[:20]:
            print(f"  {h.csv_path}")
        if len(hits) > 20:
            print(f"  ... and {len(hits) - 20} more")


def _print_transfer_summary(stats: TransferStats, dest_dir: str, *, move: bool) -> None:
    action = "Moved" if move else "Copied"
    print(f"\n=================== {action} summary ===================")
    print(f"Target directory: {os.path.abspath(dest_dir)}")
    print(f"Success: {stats.ok}")
    print(f"Skipped: {stats.skipped}")
    print(f"Errors: {stats.errors}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Recursively find CSV files under folders matching a name pattern."
    )
    parser.add_argument(
        "--root",
        "-r",
        default=r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\2G",
        help="Root directory to search recursively",
    )
    parser.add_argument(
        "--folder-pattern",
        "-f",
        default="wifi_txrx_test_RXSens_*_mld_en0_cur_degree0",
        help="Folder basename glob (default) or regex when --regex-folder",
    )
    parser.add_argument(
        "--csv-pattern",
        "-c",
        default="*.csv",
        help="CSV filename glob (default) or regex when --regex-csv",
    )
    parser.add_argument(
        "--regex-folder",
        action="store_true",
        help="Treat --folder-pattern as a regex anchored at start of basename",
    )
    parser.add_argument(
        "--regex-csv",
        action="store_true",
        help="Treat --csv-pattern as a regex anchored at start of filename",
    )
    parser.add_argument(
        "--list-out",
        "-o",
        metavar="FILE",
        help="Write one absolute CSV path per line to this file",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print every matched folder and CSV path",
    )
    parser.add_argument(
        "--paths-only",
        action="store_true",
        help="Print only CSV paths (one per line), no summary",
    )
    dest = parser.add_mutually_exclusive_group()
    dest.add_argument(
        "--copy-dir",
        metavar="DIR",
        help="Copy matched CSV files into this directory (flat layout)",
    )
    dest.add_argument(
        "--move-dir",
        metavar="DIR",
        help="Move matched CSV files into this directory (flat layout)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files in --copy-dir / --move-dir (default: auto-rename)",
    )
    parser.add_argument(
        "--use-subpath-prefix",
        action="store_true",
        help="Dest filename = relative path under matched folder with '_' separators",
    )
    args = parser.parse_args(argv)

    try:
        hits = find_csv_in_matched_folders(
            args.root,
            args.folder_pattern,
            args.csv_pattern,
            use_regex_folder=args.regex_folder,
            use_regex_csv=args.regex_csv,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    if args.list_out:
        _write_list_file(hits, args.list_out)
        if not args.paths_only:
            print(f"Wrote {len(hits)} path(s) to {os.path.abspath(args.list_out)}")

    dest_dir = args.copy_dir or args.move_dir
    if dest_dir and hits:
        print(f"\n{'Moving' if args.move_dir else 'Copying'} {len(hits)} file(s) to {dest_dir} ...")
        stats = transfer_csv_hits(
            hits,
            dest_dir,
            move=bool(args.move_dir),
            overwrite=args.overwrite,
            use_subpath_prefix=args.use_subpath_prefix,
        )
        if not args.paths_only:
            _print_transfer_summary(stats, dest_dir, move=bool(args.move_dir))

    if args.paths_only:
        for h in hits:
            print(h.csv_path)
    elif not args.list_out or args.verbose or dest_dir:
        if not dest_dir or args.verbose:
            _print_report(
                hits,
                args.root,
                args.folder_pattern,
                args.csv_pattern,
                verbose=args.verbose,
            )
    elif args.list_out:
        _print_report(
            hits,
            args.root,
            args.folder_pattern,
            args.csv_pattern,
            verbose=False,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
