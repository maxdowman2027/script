#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RX sensitivity calculation (same algorithm as wifiRxPlot.py), CSV output only.

Interpolates sensitivity (dBm) at PER 8% (11b) or 10% (other) vs rfpwr sweep per rate.
"""

from __future__ import annotations

import glob
import math
import os
import re
from collections import defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import pandas as pd

_MLD_EN_RE = re.compile(r"mld_en(\d+)", re.I)
_CUR_DEGREE_RE = re.compile(r"cur_degree(\d+)", re.I)


def parse_testcase_folder_params(
    testcase_folder: Optional[str],
) -> Tuple[str, str]:
    """
    Extract mld_en and cur_degree from testcase folder basename.

    Example: wifi_txrx_test_RXSens_..._mld_en0_cur_degree45 -> ("0", "45")
    """
    if not testcase_folder:
        return "", ""
    mld = _MLD_EN_RE.search(testcase_folder)
    deg = _CUR_DEGREE_RE.search(testcase_folder)
    return (mld.group(1) if mld else "", deg.group(1) if deg else "")


def testcase_params_from_path_config(path_config: Mapping[str, Any]) -> Tuple[str, str]:
    """mld_en / cur_degree from path_config, with fallback parse on testcase_folder."""
    mld = str(path_config.get("mld_en") or "").strip()
    deg = str(path_config.get("cur_degree") or "").strip()
    if mld and deg:
        return mld, deg
    return parse_testcase_folder_params(path_config.get("testcase_folder"))


def _strip_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def _require_columns(df: pd.DataFrame, names: Sequence[str]) -> None:
    missing = [n for n in names if n not in df.columns]
    if missing:
        raise ValueError(f"RX CSV missing columns {missing}; have {list(df.columns)}")


def infer_testcase_label(df: pd.DataFrame, testcase_folder: Optional[str], wifi_format: Optional[str]) -> str:
    """Guess 11b vs other for PER threshold (wifiRxPlot uses '11b' in testcase name)."""
    blob = " ".join(
        [
            str(testcase_folder or ""),
            str(wifi_format or ""),
            " ".join(str(x) for x in df.get("rate", pd.Series(dtype=object)).dropna().unique()),
        ]
    ).lower()
    if "11b" in blob or "dsss" in blob:
        return "11b"
    return wifi_format or testcase_folder or "default"


def calc_sensitivity_dbm(
    per: Sequence[float],
    power: Sequence[float],
    *,
    testcase: str,
    is_acr: bool,
    sens_accuracy: int = 100,
) -> float:
    """
    One rate column: interpolate power at target PER (wifiRxPlot logic).
    Returns sensitivity in dBm; 0 if not found.
    """
    per_list = list(per)
    pow_list = list(power)
    n = len(per_list)
    if n == 0:
        return 0.0

    is_11b = "11b" in testcase.lower()
    pow_sens_result = 0.0

    for i in range(n):
        if is_11b:
            if is_acr:
                if per_list[i] > 0.08:
                    if i == 0:
                        return 0.0
                    if per_list[i - 1] == 0:
                        delta_per = (math.log10(per_list[i]) - 0.0001) / sens_accuracy
                    else:
                        delta_per = (math.log10(per_list[i]) - math.log10(per_list[i - 1])) / sens_accuracy
                    per_sens = math.log10(per_list[i])
                    pow_sens = float(pow_list[i])
                    for _ in range(sens_accuracy):
                        per_sens -= delta_per
                        pow_sens -= 1.0 / sens_accuracy
                        if per_sens <= -1.096:
                            pow_sens_result = pow_sens
                            break
                    break
            else:
                if per_list[i] < 0.08:
                    if per_list[i] == 0:
                        if i == 0:
                            return 0.0
                        delta_per = (math.log10(per_list[i - 1]) + 10) / sens_accuracy
                        per_sens = -10.0
                    else:
                        if i == 0:
                            return 0.0
                        delta_per = (math.log10(per_list[i - 1]) - math.log10(per_list[i])) / sens_accuracy
                        per_sens = math.log10(per_list[i])
                    pow_sens = float(pow_list[i])
                    for _ in range(sens_accuracy):
                        per_sens += delta_per
                        pow_sens -= 1.0 / sens_accuracy
                        if per_sens >= -1.096:
                            pow_sens_result = pow_sens
                            break
                    break
        else:
            if is_acr:
                if per_list[i] > 0.1:
                    if i == 0:
                        return 0.0
                    if per_list[i - 1] == 0:
                        delta_per = (math.log10(per_list[i]) + 2) / sens_accuracy
                    else:
                        delta_per = (math.log10(per_list[i]) - math.log10(per_list[i - 1])) / sens_accuracy
                    per_sens = math.log10(per_list[i])
                    pow_sens = float(pow_list[i])
                    for _ in range(sens_accuracy):
                        per_sens -= delta_per
                        pow_sens -= 1.0 / sens_accuracy
                        if per_sens <= -1.0:
                            pow_sens_result = pow_sens
                            break
                    break
            else:
                if per_list[i] < 0.1:
                    if per_list[i] == 0:
                        if i == 0:
                            return 0.0
                        if per_list[i - 1] == 0:
                            delta_per = 0.0
                            per_sens = -10.0
                        else:
                            delta_per = (math.log10(per_list[i - 1]) + 10) / sens_accuracy
                            per_sens = -10.0
                    else:
                        if i == 0:
                            return 0.0
                        delta_per = (math.log10(per_list[i - 1]) - math.log10(per_list[i])) / sens_accuracy
                        per_sens = math.log10(per_list[i])
                    pow_sens = float(pow_list[i])
                    for _ in range(sens_accuracy):
                        per_sens += delta_per
                        pow_sens -= 1.0 / sens_accuracy
                        if per_sens >= -1.0:
                            pow_sens_result = pow_sens
                            break
                    break

    return round(pow_sens_result, 2)


def load_rx_session_dataframe(session_dir: str, csv_glob: str = "*.csv") -> pd.DataFrame:
    """Merge all RX CSV files in one directory (same as wifiRxPlot per testcase folder)."""
    paths = sorted(glob.glob(os.path.join(session_dir, csv_glob)))
    if not paths:
        raise FileNotFoundError(f"No CSV in session dir: {session_dir}")

    frames = []
    for p in paths:
        frames.append(pd.read_csv(p, index_col=False))
    df = pd.concat(frames, ignore_index=True)
    return _strip_columns(df)


def sensitivity_rows_for_session(
    session_dir: str,
    path_config: Mapping[str, Any],
    *,
    pak_num: int = 1000,
    sens_accuracy: int = 100,
    csv_glob: str = "*.csv",
) -> List[Dict[str, Any]]:
    """
    Compute one row per (rx_chan, rate) with path config + sensitivity_dbm.
    """
    df = load_rx_session_dataframe(session_dir, csv_glob=csv_glob)
    _require_columns(df, ["rx_chan", "rxnum", "rfpwr", "rate"])

    testcase = infer_testcase_label(
        df,
        path_config.get("testcase_folder"),
        path_config.get("wifi_format"),
    )
    is_acr = "acr" in testcase.lower() or "aci" in testcase.lower()

    df = df.copy()
    df["per"] = df["rxnum"].map(lambda x: 1 - min(float(x), pak_num) / pak_num)

    index_col = "acr" if is_acr else "rfpwr"
    if index_col not in df.columns and is_acr:
        raise ValueError(f"ACR testcase but column 'acr' missing in {session_dir}")

    mld_en, cur_degree = testcase_params_from_path_config(path_config)
    rows: List[Dict[str, Any]] = []
    base = {
        "band": path_config.get("band") or "",
        "phymode": path_config.get("phymd") or "",
        "bandwidth": path_config.get("bandwidth") or "",
        "coding": path_config.get("coding") or "",
        "wifi_format": path_config.get("wifi_format") or "",
        "testcase_folder": path_config.get("testcase_folder") or "",
        "mld_en": mld_en,
        "cur_degree": cur_degree,
        "config_tag": path_config.get("config_tag") or "",
        "rx_session_dir": os.path.abspath(session_dir),
        "testcase_label": testcase,
    }

    for chan in sorted(df["rx_chan"].dropna().unique(), key=lambda x: str(x)):
        df_chan = df[df["rx_chan"] == chan]
        table = pd.pivot_table(df_chan, index=[index_col], columns=["rate"], values=["per"], aggfunc="mean")
        column_convert = [col[1] if isinstance(col, tuple) else col for col in table.columns]
        table.columns = column_convert

        for rate in column_convert:
            per4pow = table[rate]
            sens = calc_sensitivity_dbm(
                per4pow.values,
                per4pow.index,
                testcase=testcase,
                is_acr=is_acr,
                sens_accuracy=sens_accuracy,
            )
            row = dict(base)
            row["rx_chan"] = chan
            row["rate"] = rate
            row["sensitivity_dbm"] = sens
            rows.append(row)

    return rows


def write_sensitivity_csv(rows: Sequence[Dict[str, Any]], out_path: str) -> None:
    """Write sensitivity result table."""
    columns = [
        "band",
        "phymode",
        "bandwidth",
        "coding",
        "wifi_format",
        "testcase_folder",
        "mld_en",
        "cur_degree",
        "config_tag",
        "rx_session_dir",
        "rx_chan",
        "testcase_label",
        "rate",
        "sensitivity_dbm",
    ]
    parent = os.path.dirname(os.path.abspath(out_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    frame = pd.DataFrame(rows)
    for col in columns:
        if col not in frame.columns:
            frame[col] = ""
    frame = frame[columns]
    frame.to_csv(out_path, index=False, encoding="utf-8-sig")


def _safe_filename_part(value: Any, default: str = "na") -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        return default
    return re.sub(r"[^\w\-.]+", "_", text)[:80]


def _radar_mld_filename_tag(mld_values: Sequence[str]) -> str:
    """Filename tag for compared mld_en series on one chart."""
    ordered = sorted({str(m).strip() for m in mld_values if str(m).strip() != ""}, key=lambda x: (len(x), x))
    if not ordered:
        return "mld_na"
    if ordered == ["0", "1"]:
        return "mld0v1"
    return "mld" + "_".join(ordered)


def plot_sensitivity_radar(
    rows: Sequence[Dict[str, Any]],
    out_dir: str,
) -> List[str]:
    """
    Polar (radar) charts: angle = cur_degree (°), radius = -sensitivity_dbm (larger = more sensitive).

    One PNG per (band, phymode, bandwidth, coding, wifi_format, rx_chan, rate), with each
    mld_en (e.g. 0 and 1) overlaid on the same axes for comparison.
    """
    import matplotlib.pyplot as plt
    import numpy as np

    # config_key -> mld_en -> rows
    groups: Dict[Tuple[Any, ...], Dict[str, List[Dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        deg = str(row.get("cur_degree") or "").strip()
        sens = row.get("sensitivity_dbm")
        if not deg or sens in (None, "", 0, 0.0):
            continue
        try:
            float(deg)
            float(sens)
        except (TypeError, ValueError):
            continue
        mld_en = str(row.get("mld_en") or "").strip() or "na"
        config_key = (
            row.get("band"),
            row.get("phymode"),
            row.get("bandwidth"),
            row.get("coding"),
            row.get("wifi_format"),
            row.get("rx_chan"),
            row.get("rate"),
        )
        groups[config_key][mld_en].append(row)

    if not groups:
        return []

    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    written: List[str] = []
    series_colors = plt.cm.tab10.colors

    for config_key, by_mld in sorted(groups.items(), key=lambda kv: str(kv[0])):
        (
            band,
            phymode,
            bandwidth,
            coding,
            wifi_format,
            rx_chan,
            rate,
        ) = config_key

        fig, ax = plt.subplots(figsize=(9, 9), subplot_kw={"projection": "polar"})
        all_degrees: set = set()
        mld_keys = sorted(by_mld.keys(), key=lambda x: (x == "na", x))

        for idx, mld_en in enumerate(mld_keys):
            grp = by_mld[mld_en]
            pts = sorted(
                [(float(r["cur_degree"]), float(r["sensitivity_dbm"])) for r in grp],
                key=lambda x: x[0],
            )
            if not pts:
                continue
            degrees = [p[0] for p in pts]
            sens_dbm = [p[1] for p in pts]
            all_degrees.update(degrees)
            theta = np.deg2rad(degrees)
            radius = [-s for s in sens_dbm]
            theta_closed = np.append(theta, theta[0])
            radius_closed = np.append(radius, radius[0])
            color = series_colors[idx % len(series_colors)]
            label = f"mld_en={mld_en}"
            ax.plot(
                theta_closed,
                radius_closed,
                "o-",
                linewidth=2,
                markersize=6,
                color=color,
                label=label,
            )
            ax.fill(theta_closed, radius_closed, alpha=0.12, color=color)

        if not all_degrees:
            plt.close(fig)
            continue

        deg_list = sorted(all_degrees)
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_thetagrids(deg_list, labels=[f"{int(d)}°" for d in deg_list])
        mld_tag = _radar_mld_filename_tag(mld_keys)
        ax.set_title(
            "RX sensitivity vs angle (mld_en compare)\n"
            f"{band} {phymode} {bandwidth} {coding} {wifi_format} | "
            f"ch={rx_chan} rate={rate}\n"
            f"(radius = −sensitivity_dbm, larger = more sensitive)",
            pad=20,
            fontsize=10,
        )
        ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=9)

        fname = (
            f"radar_{_safe_filename_part(band)}_{_safe_filename_part(phymode)}"
            f"_{_safe_filename_part(bandwidth)}_{_safe_filename_part(coding)}"
            f"_{_safe_filename_part(wifi_format)}_{mld_tag}"
            f"_ch{_safe_filename_part(rx_chan)}_rate{_safe_filename_part(rate)}.png"
        )
        out_path = os.path.join(out_dir, fname)
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        written.append(out_path)

    return written
