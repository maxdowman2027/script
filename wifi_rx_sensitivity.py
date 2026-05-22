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
from typing import Any, Dict, List, Mapping, Optional, Sequence

import pandas as pd


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

    rows: List[Dict[str, Any]] = []
    base = {
        "band": path_config.get("band") or "",
        "phymode": path_config.get("phymd") or "",
        "bandwidth": path_config.get("bandwidth") or "",
        "coding": path_config.get("coding") or "",
        "wifi_format": path_config.get("wifi_format") or "",
        "testcase_folder": path_config.get("testcase_folder") or "",
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
