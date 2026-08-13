#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Read ILA dump CSV for static DPD training.

Supported layouts (header row required):

1) feedback/ref (importfile20 style)::

     adc_i, adc_q, feedback_q, feedback_i, ref_i, ref_q

2) DAC dump::

     adc_i, adc_q, dac_i, dac_q

Returns complex columns after optional decimate (::K), matching MATLAB (1:2:end)
when ``decimate=2``. Hex cells (e.g. Vivado ``3fc``) are accepted.

Oversampling helpers (``resample_iq_to_osr``) convert between dump OSR labels
(e.g. pkt_out 2x vs ref 4x) before TX/RX compare.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np
import pandas as pd

PathLike = Union[str, Path]

# MATLAB importfile20 defaults: rows 2..16385 inclusive (1-based with header)
DEFAULT_START_ROW = 2
DEFAULT_END_ROW = 16385


def _parse_numeric_cell(val) -> float:
    """Parse decimal or hex cell."""
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


def _series_to_complex(i_col: np.ndarray, q_col: np.ndarray) -> np.ndarray:
    return (
        np.asarray(i_col, dtype=float) + 1j * np.asarray(q_col, dtype=float)
    ).reshape(-1, 1)


def _zeros_like_n(n: int) -> np.ndarray:
    return np.zeros((n, 1), dtype=np.complex128)


def resample_iq_to_osr(
    x: np.ndarray,
    src_osr: int,
    work_osr: int,
) -> np.ndarray:
    """
    Resample complex IQ from ``src_osr`` to ``work_osr`` (integer ratios preferred).

    - ``src_osr == work_osr``: unchanged
    - ``src_osr`` multiple of ``work_osr``: decimate ``src/work`` (take every K-th)
    - ``work_osr`` multiple of ``src_osr``: ``resample_poly`` upsample
    - else: ``resample_poly(work_osr, src_osr)``
    """
    x = np.asarray(x, dtype=np.complex128).reshape(-1)
    s = int(src_osr)
    w = int(work_osr)
    if s <= 0 or w <= 0:
        raise ValueError(f"osr must be positive, got src={src_osr} work={work_osr}")
    if s == w or x.size == 0:
        return x.reshape(-1, 1)
    if s % w == 0:
        return x[:: (s // w)].reshape(-1, 1)
    from scipy.signal import resample_poly

    if w % s == 0:
        y = resample_poly(x, w // s, 1)
    else:
        y = resample_poly(x, w, s)
    return np.asarray(y, dtype=np.complex128).reshape(-1, 1)


def read_data(
    csv_path: PathLike,
    *,
    start_row: int = DEFAULT_START_ROW,
    end_row: int = DEFAULT_END_ROW,
    decimate: int = 2,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Load ILA CSV and build complex baseband channels.

    Returns
    -------
    ref, feedback, adc, dac : complex (N, 1)
        Missing channels are all-zero vectors of length N (after decimate).
        Layout is auto-detected from the header.
    """
    path = Path(csv_path)
    nrows = int(end_row) - int(start_row) + 1
    i0 = max(int(start_row) - 2, 0)  # 0-based index into data rows

    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.iloc[i0 : i0 + nrows].copy()
    if df.empty:
        raise ValueError(f"no data rows in {path} for rows {start_row}..{end_row}")

    for c in df.columns:
        df[c] = df[c].map(_parse_numeric_cell)

    def get_iq(i_name: str, q_name: str) -> Optional[np.ndarray]:
        if i_name in df.columns and q_name in df.columns:
            return _series_to_complex(df[i_name].to_numpy(), df[q_name].to_numpy())
        return None

    adc = get_iq("adc_i", "adc_q")
    dac = get_iq("dac_i", "dac_q")
    fb = get_iq("feedback_i", "feedback_q")
    ref = get_iq("ref_i", "ref_q")

    if dac is not None and ref is None and fb is None:
        layout = "dac"
    elif ref is not None or fb is not None:
        layout = "feedback_ref"
    else:
        layout = "unknown"
        if adc is None:
            raise ValueError(
                f"unrecognized CSV columns in {path}: {list(df.columns)}; "
                "need adc_* and (ref_*/feedback_* or dac_*)"
            )

    n = len(df)
    if adc is None:
        adc = _zeros_like_n(n)
    if dac is None:
        dac = _zeros_like_n(n)
    if fb is None:
        fb = _zeros_like_n(n)
    if ref is None:
        ref = _zeros_like_n(n)

    if decimate > 1:
        ref = ref[::decimate]
        fb = fb[::decimate]
        adc = adc[::decimate]
        dac = dac[::decimate]

    print(f"[CSV] layout={layout}  cols={list(df.columns)}")
    return ref, fb, adc, dac


def read_data_legacy(
    csv_path: PathLike,
    *,
    start_row: int = DEFAULT_START_ROW,
    end_row: int = DEFAULT_END_ROW,
    decimate: int = 2,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Backward-compatible 3-tuple: (ref, feedback, adc). """
    ref, fb, adc, _dac = read_data(
        csv_path, start_row=start_row, end_row=end_row, decimate=decimate
    )
    return ref, fb, adc


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
        if sample_rate is not None and sample_rate >= 1.5e8:
            st = 2
        else:
            st = 1
    if st > 1:
        iq = iq[::st]
    return iq.reshape(-1, 1)
