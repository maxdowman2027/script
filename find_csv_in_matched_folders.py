#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recursively find CSV files under folders whose names match a glob or regex pattern.

Parses rftest_data-style path tiers (band / phymd / bw / coding / format, …).
Optionally copy or move matched CSVs to a flat target directory.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import os
import re
import shutil
import time
from collections import OrderedDict
from dataclasses import dataclass, replace
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

import wifi_rx_sensitivity as wrx_sens


# =============================================================================
# 配置区（直接改这里即可；命令行参数会覆盖同名字段）
# =============================================================================
# 1. 递归检索的根目录
ROOT_SEARCH_PATH = (
    r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\2G"
)

# 2. 要匹配的文件夹名（basename 通配符；正则模式时设 USE_REGEX_FOLDER=True）
FOLDER_PATTERN = "wifi_txrx_test_RXSens_*_mld_en*_cur_degree*"

# 3. 匹配文件夹内的 CSV 文件名（通配符）
CSV_PATTERN = "*.csv"

# 4. 复制 / 移动目标（二选一；不需要落盘时两项都设为 None）
COPY_DIR = None
MOVE_DIR = None
# MOVE_DIR = (
#     r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts"
# )

# 其它常用开关（一般保持默认即可）
USE_REGEX_FOLDER = False
USE_REGEX_CSV = False
OVERWRITE = False
USE_SUBPATH_PREFIX = False
USE_CONFIG_PREFIX = True  # 落盘时在文件名前加 2G_phymd20_20m_ldpc_he_ 等
LIST_OUT_FILE = None  # 例如 r"D:\path\to\matched_csv_list.txt"
LIST_OUT_WITH_CONFIG = True  # --list-out 时写 TSV（含路径层级解析列）
VERBOSE = True
PATHS_ONLY = False

# 5. 灵敏度（算法同 wifiRxPlot.py，按 rx_* 会话目录合并 CSV 后计算）
RUN_SENSITIVITY = True
SENSITIVITY_OUT_CSV = None  # None → 在 ROOT_SEARCH_PATH 下 sensitivity_summary_YYYYMMDD_HHMMSS.csv
PAK_NUM = 1000
SENS_ACCURACY = 100
# 6. 灵敏度雷达图（角度 = cur_degree，半径 = -sensitivity_dbm，越大越灵敏）
RUN_SENSITIVITY_RADAR = True
SENSITIVITY_RADAR_DIR = None  # None → 与灵敏度 CSV 同目录下的 <csv_stem>_radar/
# =============================================================================

_BAND_RE = re.compile(r"^(2G|5G|6G)$", re.I)
_PHYMD_RE = re.compile(r"^phymd(\d+)$", re.I)
_BW_RE = re.compile(r"^(\d+)m$", re.I)
_CODING_RE = re.compile(r"^(ldpc|bcc)$", re.I)
_FORMAT_RE = re.compile(
    r"^(he|vht|ax|be|hesu|eht|11b|11g|11n|11ac|11ax|11be)$", re.I
)
_TESTCASE_RE = re.compile(r"^wifi_txrx", re.I)
PATH_CONFIG_FIELDS = (
    "band",
    "phymd",
    "bandwidth",
    "coding",
    "wifi_format",
    "testcase_folder",
    "mld_en",
    "cur_degree",
)


@dataclass(frozen=True)
class PathConfig:
    """RF test directory layout inferred from CSV path under search root."""

    band: Optional[str] = None
    phymd: Optional[str] = None
    bandwidth: Optional[str] = None
    coding: Optional[str] = None
    wifi_format: Optional[str] = None
    testcase_folder: Optional[str] = None
    mld_en: Optional[str] = None
    cur_degree: Optional[str] = None
    relative_parts: Tuple[str, ...] = ()

    def config_tag(self, sep: str = "_") -> str:
        """Compact tag for filenames: 2G_phymd20_20m_ldpc_he."""
        keys = (self.band, self.phymd, self.bandwidth, self.coding, self.wifi_format)
        parts = [p for p in keys if p]
        return sep.join(parts) if parts else "unknown_cfg"

    def summary(self) -> str:
        """Human-readable key=value list."""
        items = []
        for name in PATH_CONFIG_FIELDS:
            val = getattr(self, name)
            if val:
                items.append(f"{name}={val}")
        return ", ".join(items) if items else "(no tier labels parsed)"


@dataclass(frozen=True)
class CsvHit:
    """One CSV file found under a matched folder."""

    matched_folder: str
    folder_name: str
    csv_path: str
    csv_name: str
    path_config: PathConfig


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


def _classify_segment(seg: str, cfg: PathConfig) -> PathConfig:
    if _BAND_RE.match(seg) and not cfg.band:
        return replace(cfg, band=seg.upper())
    if _PHYMD_RE.match(seg) and not cfg.phymd:
        return replace(cfg, phymd=seg.lower())
    m = _BW_RE.match(seg)
    if m and not cfg.bandwidth:
        return replace(cfg, bandwidth=f"{m.group(1)}m")
    if _CODING_RE.match(seg) and not cfg.coding:
        return replace(cfg, coding=seg.lower())
    if _FORMAT_RE.match(seg) and not cfg.wifi_format:
        return replace(cfg, wifi_format=seg.lower())
    if _TESTCASE_RE.match(seg) and not cfg.testcase_folder:
        return replace(cfg, testcase_folder=seg)
    return cfg


def _apply_positional_tiers(dir_parts: Sequence[str], cfg: PathConfig) -> PathConfig:
    """Fallback: after band, typical layout is phymd* / Nm / ldpc|bcc / he|vht|..."""
    idx = 0
    if cfg.band and idx < len(dir_parts) and dir_parts[idx].upper() == cfg.band:
        idx += 1

    updates = {}
    if not cfg.phymd and idx < len(dir_parts) and _PHYMD_RE.match(dir_parts[idx]):
        updates["phymd"] = dir_parts[idx]
        idx += 1
    if not cfg.bandwidth and idx < len(dir_parts) and _BW_RE.match(dir_parts[idx]):
        m = _BW_RE.match(dir_parts[idx])
        updates["bandwidth"] = f"{m.group(1)}m"
        idx += 1
    if not cfg.coding and idx < len(dir_parts) and _CODING_RE.match(dir_parts[idx]):
        updates["coding"] = dir_parts[idx].lower()
        idx += 1
    if not cfg.wifi_format and idx < len(dir_parts) and _FORMAT_RE.match(dir_parts[idx]):
        updates["wifi_format"] = dir_parts[idx].lower()
        idx += 1

    return replace(cfg, **updates) if updates else cfg


def extract_path_config(csv_path: str, root_search_path: str) -> PathConfig:
    """
    Parse band / phymd / bandwidth / coding / wifi_format from path under root.

    Example (root = .../rftest_data/2G):
      phymd20/20m/ldpc/he/wifi_txrx_test_.../FPGA.../rx_.../RX_*.csv
      -> 2G, phymd20, 20m, ldpc, he
    """
    csv_abs = os.path.abspath(csv_path)
    root_abs = os.path.abspath(root_search_path)
    rel = os.path.relpath(csv_abs, root_abs)
    parts = tuple(p for p in rel.split(os.sep) if p)
    if not parts:
        return PathConfig()

    dir_parts = parts[:-1]
    cfg = PathConfig(relative_parts=parts)

    root_base = os.path.basename(root_abs.rstrip("\\/"))
    if _BAND_RE.match(root_base):
        cfg = replace(cfg, band=root_base.upper())

    for seg in dir_parts:
        cfg = _classify_segment(seg, cfg)

    cfg = _apply_positional_tiers(dir_parts, cfg)

    if not cfg.band:
        for seg in dir_parts:
            if _BAND_RE.match(seg):
                cfg = replace(cfg, band=seg.upper())
                break

    return _apply_testcase_folder_params(cfg)


def _apply_testcase_folder_params(cfg: PathConfig) -> PathConfig:
    if not cfg.testcase_folder:
        return cfg
    mld_en, cur_degree = wrx_sens.parse_testcase_folder_params(cfg.testcase_folder)
    updates = {}
    if mld_en and not cfg.mld_en:
        updates["mld_en"] = mld_en
    if cur_degree and not cfg.cur_degree:
        updates["cur_degree"] = cur_degree
    return replace(cfg, **updates) if updates else cfg


def iter_matched_folder_paths(
    root_search_path: str,
    folder_pattern: str,
    *,
    use_regex_folder: bool = False,
) -> Iterator[Tuple[str, str]]:
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
    hits: List[CsvHit] = []
    root = os.path.abspath(root_search_path)

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
                csv_abs = os.path.abspath(csv_path)
                hits.append(
                    CsvHit(
                        matched_folder=folder_path,
                        folder_name=folder_name,
                        csv_path=csv_abs,
                        csv_name=file_name,
                        path_config=extract_path_config(csv_abs, root),
                    )
                )

    hits.sort(key=lambda h: h.csv_path)
    return hits


def _dest_basename(
    hit: CsvHit,
    *,
    use_subpath_prefix: bool,
    use_config_prefix: bool,
) -> str:
    name = hit.csv_name
    if use_config_prefix:
        tag = hit.path_config.config_tag()
        name = f"{tag}_{name}"
    if use_subpath_prefix:
        rel = os.path.relpath(hit.csv_path, hit.matched_folder)
        rel = rel.replace("\\", "_").replace("/", "_")
        if use_config_prefix:
            return f"{hit.path_config.config_tag()}_{rel}"
        return rel
    return name


def _resolve_dest_path(
    dest_dir: str,
    base_name: str,
    *,
    overwrite: bool,
    reserved: set,
) -> str:
    dest_dir = os.path.abspath(dest_dir)
    target = os.path.join(dest_dir, base_name)

    if not overwrite and target in reserved:
        stem, ext = os.path.splitext(base_name)
        n = 1
        while True:
            candidate = f"{stem}_{n}{ext}"
            target = os.path.join(dest_dir, candidate)
            if target not in reserved and not os.path.exists(target):
                break
            n += 1
    elif not overwrite and os.path.exists(target):
        stem, ext = os.path.splitext(base_name)
        n = 1
        while True:
            candidate = f"{stem}_{n}{ext}"
            target = os.path.join(dest_dir, candidate)
            if target not in reserved and not os.path.exists(target):
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
    use_config_prefix: bool = False,
) -> TransferStats:
    stats = TransferStats()
    dest_dir = os.path.abspath(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    reserved: set = set()
    op = shutil.move if move else shutil.copy2
    op_name = "move" if move else "copy"

    for hit in hits:
        base_name = _dest_basename(
            hit,
            use_subpath_prefix=use_subpath_prefix,
            use_config_prefix=use_config_prefix,
        )
        target = _resolve_dest_path(
            dest_dir, base_name, overwrite=overwrite, reserved=reserved
        )
        try:
            op(hit.csv_path, target)
            stats.ok += 1
            print(
                f"  OK {op_name}: [{hit.path_config.config_tag()}] "
                f"{hit.csv_path} -> {target}"
            )
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


def _write_list_file(
    hits: Sequence[CsvHit],
    list_file: str,
    *,
    with_config: bool,
) -> None:
    parent = os.path.dirname(os.path.abspath(list_file))
    if parent:
        os.makedirs(parent, exist_ok=True)

    if with_config:
        header = ["csv_path", "config_tag", *PATH_CONFIG_FIELDS]
        with open(list_file, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(header)
            for h in hits:
                pc = h.path_config
                w.writerow(
                    [
                        h.csv_path,
                        pc.config_tag(),
                        pc.band or "",
                        pc.phymd or "",
                        pc.bandwidth or "",
                        pc.coding or "",
                        pc.wifi_format or "",
                        pc.testcase_folder or "",
                        pc.mld_en or "",
                        pc.cur_degree or "",
                    ]
                )
    else:
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
                    print(f"  [{h.path_config.config_tag()}] {h.path_config.summary()}")
                    print(f"    {h.csv_path}")
    elif hits:
        print("\nCSV + path config (first 20; use -v for full tree or --list-out):")
        for h in hits[:20]:
            print(f"  [{h.path_config.config_tag()}] {h.csv_name}")
            print(f"    {h.path_config.summary()}")
        if len(hits) > 20:
            print(f"  ... and {len(hits) - 20} more")


def path_config_to_dict(pc: PathConfig) -> Dict[str, Any]:
    """Path tiers for sensitivity CSV columns (phymode = phymd)."""
    d = {name: getattr(pc, name) or "" for name in PATH_CONFIG_FIELDS}
    d["config_tag"] = pc.config_tag()
    return d


def _default_sensitivity_out_path(root_search_path: str) -> str:
    ts = time.strftime("%Y%m%d_%H%M%S")
    return os.path.join(os.path.abspath(root_search_path), f"sensitivity_summary_{ts}.csv")


def _default_radar_out_dir(sensitivity_csv: str) -> str:
    base, _ = os.path.splitext(os.path.abspath(sensitivity_csv))
    return f"{base}_radar"


def run_sensitivity_for_hits(
    hits: Sequence[CsvHit],
    out_csv: str,
    *,
    pak_num: int = 1000,
    sens_accuracy: int = 100,
    run_radar: bool = True,
    radar_out_dir: Optional[str] = None,
) -> int:
    """
    Group hits by RX session directory (parent folder of CSV), merge logs, compute
    sensitivity per rx_chan and rate (wifiRxPlot algorithm).
    """
    sessions: OrderedDict[str, CsvHit] = OrderedDict()
    for h in hits:
        session_dir = os.path.dirname(h.csv_path)
        if session_dir not in sessions:
            sessions[session_dir] = h

    all_rows: List[Dict[str, Any]] = []
    ok_sessions = 0
    for session_dir, hit in sessions.items():
        try:
            rows = wrx_sens.sensitivity_rows_for_session(
                session_dir,
                path_config_to_dict(hit.path_config),
                pak_num=pak_num,
                sens_accuracy=sens_accuracy,
            )
            all_rows.extend(rows)
            ok_sessions += 1
            print(f"[OK] sensitivity: {session_dir} -> {len(rows)} rate point(s)")
        except Exception as ex:
            print(f"[WARN] sensitivity skipped {session_dir}: {ex}")

    if not all_rows:
        print("[WARN] No sensitivity rows computed")
        return 0

    wrx_sens.write_sensitivity_csv(all_rows, out_csv)
    print(
        f"[OK] Sensitivity CSV: {os.path.abspath(out_csv)} "
        f"({len(all_rows)} rows, {ok_sessions} session(s))"
    )

    if run_radar:
        radar_dir = radar_out_dir or _default_radar_out_dir(out_csv)
        try:
            pngs = wrx_sens.plot_sensitivity_radar(all_rows, radar_dir)
            if pngs:
                print(f"[OK] Sensitivity radar: {len(pngs)} chart(s) in {os.path.abspath(radar_dir)}")
            else:
                print("[WARN] No radar charts (need cur_degree and valid sensitivity_dbm)")
        except Exception as ex:
            print(f"[WARN] Radar plot skipped: {ex}")

    return len(all_rows)


def _print_transfer_summary(stats: TransferStats, dest_dir: str, *, move: bool) -> None:
    action = "Moved" if move else "Copied"
    print(f"\n=================== {action} summary ===================")
    print(f"Target directory: {os.path.abspath(dest_dir)}")
    print(f"Success: {stats.ok}")
    print(f"Skipped: {stats.skipped}")
    print(f"Errors: {stats.errors}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Recursively find CSV files under folders matching a name pattern. "
        "Parses rftest_data path tiers (2G/phymd20/20m/ldpc/he). "
        "Edit ROOT_SEARCH_PATH / FOLDER_PATTERN / MOVE_DIR at top of script."
    )
    parser.add_argument("--root", "-r", default=ROOT_SEARCH_PATH)
    parser.add_argument("--folder-pattern", "-f", default=FOLDER_PATTERN)
    parser.add_argument("--csv-pattern", "-c", default=CSV_PATTERN)
    parser.add_argument("--regex-folder", action="store_true", default=USE_REGEX_FOLDER)
    parser.add_argument("--regex-csv", action="store_true", default=USE_REGEX_CSV)
    parser.add_argument("--list-out", "-o", metavar="FILE", default=LIST_OUT_FILE)
    parser.add_argument(
        "--list-plain",
        action="store_true",
        help="With --list-out, write paths only (no config TSV columns)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", default=VERBOSE)
    parser.add_argument("--paths-only", action="store_true", default=PATHS_ONLY)
    dest = parser.add_mutually_exclusive_group()
    dest.add_argument("--copy-dir", metavar="DIR", default=COPY_DIR)
    dest.add_argument("--move-dir", metavar="DIR", default=MOVE_DIR)
    parser.add_argument("--overwrite", action="store_true", default=OVERWRITE)
    parser.add_argument("--use-subpath-prefix", action="store_true", default=USE_SUBPATH_PREFIX)
    parser.add_argument(
        "--use-config-prefix",
        action="store_true",
        default=USE_CONFIG_PREFIX,
        help="Prefix dest filename with band_phymd_bw_coding_format tag",
    )
    parser.add_argument(
        "--no-config-prefix",
        action="store_false",
        dest="use_config_prefix",
        help="Do not add path config tag to dest filenames",
    )
    parser.add_argument(
        "--sensitivity-out",
        metavar="CSV",
        default=SENSITIVITY_OUT_CSV,
        help="Sensitivity summary CSV path (default: under --root, timestamped name)",
    )
    parser.add_argument(
        "--no-sensitivity",
        action="store_true",
        help="Skip RX sensitivity calculation",
    )
    parser.add_argument(
        "--pak-num",
        type=int,
        default=PAK_NUM,
        help="Packet count for PER (wifiRxPlot PAK_NUM)",
    )
    parser.add_argument(
        "--sens-accuracy",
        type=int,
        default=SENS_ACCURACY,
        help="Interpolation steps for sensitivity (wifiRxPlot sens_accuracy)",
    )
    parser.add_argument(
        "--no-radar",
        action="store_true",
        help="Skip sensitivity vs cur_degree polar (radar) charts",
    )
    parser.add_argument(
        "--radar-dir",
        metavar="DIR",
        default=SENSITIVITY_RADAR_DIR,
        help="Output directory for radar PNGs (default: <sensitivity_csv_stem>_radar/)",
    )
    args = parser.parse_args(argv)

    if COPY_DIR and MOVE_DIR:
        print("Error: set only one of COPY_DIR and MOVE_DIR in the script config block.")
        return 1

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

    run_sens = RUN_SENSITIVITY and not args.no_sensitivity
    if run_sens and hits:
        sens_out = args.sensitivity_out or _default_sensitivity_out_path(args.root)
        print(f"\nComputing RX sensitivity (wifiRxPlot algorithm) -> {sens_out}")
        run_sensitivity_for_hits(
            hits,
            sens_out,
            pak_num=args.pak_num,
            sens_accuracy=args.sens_accuracy,
            run_radar=RUN_SENSITIVITY_RADAR and not args.no_radar,
            radar_out_dir=args.radar_dir,
        )

    list_with_config = LIST_OUT_WITH_CONFIG and not args.list_plain
    if args.list_out:
        _write_list_file(hits, args.list_out, with_config=list_with_config)
        if not args.paths_only:
            kind = "TSV with path config" if list_with_config else "paths"
            print(f"Wrote {len(hits)} row(s) ({kind}) to {os.path.abspath(args.list_out)}")

    dest_dir = args.copy_dir or args.move_dir
    if dest_dir and hits:
        print(f"\n{'Moving' if args.move_dir else 'Copying'} {len(hits)} file(s) to {dest_dir} ...")
        stats = transfer_csv_hits(
            hits,
            dest_dir,
            move=bool(args.move_dir),
            overwrite=args.overwrite,
            use_subpath_prefix=args.use_subpath_prefix,
            use_config_prefix=args.use_config_prefix,
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
