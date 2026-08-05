#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Read ILA dump CSV for static DPD training.

Port of read_data.m + importfile20.m (20260804_3_data).

CSV columns (header skipped):
  adc_i, adc_q, feedback_q, feedback_i, ref_i, ref_q

importfile20 skips the first two (adc) columns via ``%*s%*s``; this loader
still returns adc when present, and tolerates hex cells (e.g. Vivado ``3fc``).

Returns complex TX/RX/(ADC) after 2:1 decimate (::2), matching MATLAB (1:2:end).
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple, Union

import numpy as np
import pandas as pd

PathLike = Union[str, Path]

# MATLAB importfile20 defaults: rows 2..16385 inclusive (1-based with header)
DEFAULT_START_ROW = 2
DEFAULT_END_ROW = 16385


def _parse_numeric_cell(val) -> float:
    """Parse decimal or hex cell (importfile20 is decimal-only on fb/ref)."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return np.nan
    if isinstance(val, (int, np.integer)):
        return float(val)
    if isinstance(val, (float, np.floating)):
        return float(val)
    s = str(val).strip().lower()
    if not s or s in ("nan", "none"):
        return np.nan
    try:
        return float(s)
    except ValueError:
        if s.startswith("0x"):
            s = s[2:]
        return float(int(s, 16))


def read_data(
    csv_path: PathLike,
    *,
    start_row: int = DEFAULT_START_ROW,
    end_row: int = DEFAULT_END_ROW,
    decimate: int = 2,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Load training CSV and build complex baseband.

    Parameters
    ----------
    csv_path :
        Path to ILA CSV (adc + feedback + ref).
    start_row, end_row :
        1-based inclusive row indices as in MATLAB textscan HeaderLines /
        endRow (header is row 1; data starts at row 2).
    decimate :
        Keep every N-th sample (MATLAB 2抽1 → 2).

    Returns
    -------
    tx_data, rx_data, adc_data : complex column vectors (N, 1)
        tx = ref_i + 1j*ref_q
        rx = feedback_i + 1j*feedback_q
        adc = adc_i + 1j*adc_q  (zeros if columns missing)
    """
    path = Path(csv_path)
    nrows = int(end_row) - int(start_row) + 1
    skip = max(int(start_row) - 2, 0)
    df = pd.read_csv(
        path,
        skiprows=1 + skip,
        nrows=nrows,
        header=None,
        names=["adc_i", "adc_q", "feedback_q", "feedback_i", "ref_i", "ref_q"],
        converters={
            "adc_i": _parse_numeric_cell,
            "adc_q": _parse_numeric_cell,
            "feedback_q": _parse_numeric_cell,
            "feedback_i": _parse_numeric_cell,
            "ref_i": _parse_numeric_cell,
            "ref_q": _parse_numeric_cell,
        },
    )
    arr = df.to_numpy(dtype=float)
    # importfile20 column order after skip: fb_q, fb_i, ref_i, ref_q
    tx0 = arr[:, 4] + 1j * arr[:, 5]
    rx0 = arr[:, 3] + 1j * arr[:, 2]
    adc0 = arr[:, 0] + 1j * arr[:, 1]

    if decimate > 1:
        tx0 = tx0[::decimate]
        rx0 = rx0[::decimate]
        adc0 = adc0[::decimate]

    return (
        tx0.reshape(-1, 1),
        rx0.reshape(-1, 1),
        adc0.reshape(-1, 1),
    )


def load_iqxel_txt(
    txt_path: PathLike,
    *,
    stride: int = 1,
) -> np.ndarray:
    """
    Load LitePoint iQxel I/Q capture as complex column vector.

    Supports:
      - headerless ``I,Q`` lines (older exports)
      - LitePoint header ending with ``Idata,Qdata`` then numeric rows
    """
    path = Path(txt_path)
    skip = 0
    sample_rate = None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            s = line.strip()
            if s.lower().startswith("samplingrate:"):
                try:
                    sample_rate = float(s.split(":", 1)[1].strip())
                except ValueError:
                    pass
            if s.lower() in ("idata,qdata", "i,q", "i_data,q_data"):
                skip = i + 1
                break
            # first numeric CSV line → no header (or header ended)
            if s and (s[0].isdigit() or s[0] in "+-"):
                parts = s.split(",")
                if len(parts) >= 2:
                    try:
                        float(parts[0])
                        float(parts[1])
                        skip = i
                        break
                    except ValueError:
                        pass

    data = np.loadtxt(path, delimiter=",", skiprows=skip)
    if data.ndim == 1:
        raise ValueError(f"unexpected 1-D data in {path}")
    if data.shape[1] < 2:
        raise ValueError(f"need >=2 columns I,Q in {path}")
    iq = data[:, 0] + 1j * data[:, 1]
    st = int(stride)
    if st <= 0:
        # auto: 160 Msps → match ~80 Msps ILA after 2:1
        if sample_rate is not None and sample_rate >= 1.5e8:
            st = 2
        else:
            st = 1
    if st > 1:
        iq = iq[::st]
    return iq.reshape(-1, 1)
