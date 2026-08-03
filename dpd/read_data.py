#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Read ILA dump CSV for static DPD training.

Port of read_data.m + importfile19.m.

CSV columns (header skipped):
  adc_i, adc_q, feedback_q, feedback_i, ref_i, ref_q

Returns complex TX/RX/ADC after 2:1 decimate (::2), matching MATLAB (1:2:end).
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple, Union

import numpy as np
import pandas as pd

PathLike = Union[str, Path]

# MATLAB importfile19 defaults: rows 2..16385 inclusive (1-based with header)
DEFAULT_START_ROW = 2
DEFAULT_END_ROW = 16385


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
        Path to ILA CSV (same layout as gain168_test_data_3.csv).
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
        adc = adc_i + 1j*adc_q
    """
    path = Path(csv_path)
    # pandas: skip header, then take rows [start_row-2 : end_row-1] in 0-based data index
    # After skiprows=1 (header), first data row is MATLAB row 2 → index 0.
    nrows = int(end_row) - int(start_row) + 1
    skip = max(int(start_row) - 2, 0)  # extra data rows to skip after header
    df = pd.read_csv(
        path,
        skiprows=1 + skip,
        nrows=nrows,
        header=None,
        names=["adc_i", "adc_q", "feedback_q", "feedback_i", "ref_i", "ref_q"],
    )
    arr = df.to_numpy(dtype=float)
    tx0 = arr[:, 4] + 1j * arr[:, 5]
    rx0 = arr[:, 3] + 1j * arr[:, 2]
    adc0 = arr[:, 0] + 1j * arr[:, 1]

    if decimate > 1:
        tx0 = tx0[::decimate]
        rx0 = rx0[::decimate]
        adc0 = adc0[::decimate]

    # Match MATLAB column vectors
    return (
        tx0.reshape(-1, 1),
        rx0.reshape(-1, 1),
        adc0.reshape(-1, 1),
    )
