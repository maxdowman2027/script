#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DPD LUT phase-through-0 smooth (single / multi LUT, optional master).

Methods
-------
* ``poly``   — **default**: amp no-constant weighted poly + **preserve phase trend**
  (only interpolate excluded bins; do not poly-fit phase — through-zero phase poly
  warps mid-band when trained φ sits at ~3–8°). Multi-LUT: slaves default
  **passthrough**; keep master ``|z[1]|``. Judge by EVM, not maxerr.
* ``iqpoly`` — I/Q through-zero poly (MATLAB ``polyfit_for_lut`` style)
* ``smooth`` — blended MA (phase more than amp) + amp clamp
* ``repair`` — outlier fix + master phase align only
* ``ma``     — full moving-average on amp/phase
* ``poly_ph`` — legacy: amp+phase both no-constant poly (260821 1lut style)

Bad bins
--------
By default ``exclude=auto``. No manual ``--exclude 2``.

CLI::

  python dpd/lut_phase0_fit.py DIR -o OUT --master-lut 0 --scope all
  python dpd/lut_phase0_fit.py DIR -o OUT --method poly --deg-amp 4
  python dpd/lut_phase0_fit.py DIR -o OUT --method poly_ph --deg-amp 4 --deg-ph 4
"""

from __future__ import annotations

import argparse
import ast
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np

PathLike = Union[str, Path]

DEFAULT_N_PTS = 33
DEFAULT_DEG_AMP = 4
DEFAULT_DEG_PH = 4
DEFAULT_EXCLUDE = "auto"  # auto | none | comma indices
DEFAULT_EARLY_W = 1.0
DEFAULT_LATE_W = 200.0
DEFAULT_EARLY_BINS = 3
DEFAULT_MA_WIN = 5
# poly = 260821 Cursor fit (amp/phase no-constant WLS); default for board EVM gain
DEFAULT_METHOD = "poly"
DEFAULT_MIX_AMP_MASTER = 0.50
DEFAULT_MIX_PH_MASTER = 0.80
DEFAULT_MIX_AMP_SLAVE = 0.35
DEFAULT_MIX_PH_SLAVE = 0.65
DEFAULT_MAX_AMP_DEV = 0.10  # max |amp-amp_rep|/amp_rep after blend

# Auto outlier thresholds (must match lut_phase0_fit.c)
AUTO_AMP_NEIGH_MIN = 200.0
AUTO_AMP_REL_THR = 0.40
AUTO_AMP_DIP_FACTOR = 0.60
AUTO_AMP_SPIKE_FACTOR = 1.80
AUTO_PHASE_THR_RAD = math.radians(40.0)
AUTO_AMP_MIN_FOR_PHASE = 300.0
AUTO_PHASE_REL_THR = 0.25


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def parse_lut_data_map(text: str, *, map_name: Optional[str] = None) -> Dict[int, Tuple[int, int]]:
    """Parse ``lut_data_map_lutN = { ... }`` from text."""
    if map_name:
        start_re = re.compile(rf"{re.escape(map_name)}\s*=\s*\{{")
    else:
        start_re = re.compile(r"lut_data_map_lut\d+\s*=\s*\{")
    m = start_re.search(text)
    if not m:
        raise ValueError("no lut_data_map_lut* dict found in text")
    i0 = m.end() - 1
    depth = 0
    i1 = None
    for i in range(i0, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                i1 = i + 1
                break
    if i1 is None:
        raise ValueError("unbalanced braces in lut_data_map dict")
    raw = ast.literal_eval(text[i0:i1])
    out: Dict[int, Tuple[int, int]] = {}
    for k, v in raw.items():
        out[int(k)] = (int(v["i"]), int(v["q"]))
    return out


def load_lut_data_map(path: PathLike, *, map_name: Optional[str] = None) -> Dict[int, Tuple[int, int]]:
    return parse_lut_data_map(Path(path).read_text(encoding="utf-8"), map_name=map_name)


def map_to_arrays(
    lut_map: Dict[int, Tuple[int, int]],
    *,
    n_pts: int = DEFAULT_N_PTS,
) -> Tuple[np.ndarray, np.ndarray]:
    ii = np.zeros(n_pts, dtype=float)
    qq = np.zeros(n_pts, dtype=float)
    for k, (i_v, q_v) in lut_map.items():
        if 0 <= int(k) < n_pts:
            ii[int(k)] = float(i_v)
            qq[int(k)] = float(q_v)
    return ii, qq


def discover_lut_maps(path: PathLike) -> List[Tuple[Path, int]]:
    """
    If ``path`` is a file → [(path, lut_sel)].
    If directory → all ``lut_data_map_lut*.txt`` sorted by lut index.
    """
    p = Path(path)
    if p.is_file():
        m = re.search(r"lut_data_map_lut(\d+)", p.name)
        sel = int(m.group(1)) if m else 0
        return [(p, sel)]
    if not p.is_dir():
        raise FileNotFoundError(path)
    found: List[Tuple[Path, int]] = []
    for f in sorted(p.glob("lut_data_map_lut*.txt")):
        m = re.search(r"lut_data_map_lut(\d+)", f.name)
        if not m:
            continue
        found.append((f, int(m.group(1))))
    if not found:
        raise FileNotFoundError(f"no lut_data_map_lut*.txt under {p}")
    return found


def format_lut_data_map(
    i_out: Sequence[int],
    q_out: Sequence[int],
    *,
    lut_sel: int = 0,
    header_lines: Optional[List[str]] = None,
) -> str:
    lines: List[str] = list(header_lines or [])
    if lines and lines[-1] != "":
        lines.append("")
    lines.append(f"lut_data_map_lut{int(lut_sel)} = {{")
    n = min(len(i_out), len(q_out))
    for k in range(n):
        lines.append(f'    {k}: {{"i": {int(i_out[k])}, "q": {int(q_out[k])}}},')
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def write_lut_data_map(
    path: PathLike,
    i_out: Sequence[int],
    q_out: Sequence[int],
    *,
    lut_sel: int = 0,
    header_lines: Optional[List[str]] = None,
) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        format_lut_data_map(i_out, q_out, lut_sel=lut_sel, header_lines=header_lines),
        encoding="utf-8",
    )
    return out


def write_iq_csv(path: PathLike, i_arr: Sequence[int], q_arr: Sequence[int]) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["index,i,q"]
    for k in range(min(len(i_arr), len(q_arr))):
        lines.append(f"{k},{int(i_arr[k])},{int(q_arr[k])}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Core math
# ---------------------------------------------------------------------------

def default_weights(
    n_pts: int,
    *,
    early_bins: int = DEFAULT_EARLY_BINS,
    early_w: float = DEFAULT_EARLY_W,
    late_w: float = DEFAULT_LATE_W,
) -> np.ndarray:
    w = np.full(n_pts, float(late_w), dtype=float)
    w[: max(0, int(early_bins))] = float(early_w)
    return w


def poly_through_zero(
    x: np.ndarray,
    y: np.ndarray,
    deg: int,
    *,
    w: Optional[np.ndarray] = None,
) -> np.ndarray:
    deg = int(deg)
    if deg < 1:
        raise ValueError("deg must be >= 1")
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    A = np.column_stack([x ** k for k in range(1, deg + 1)])
    if w is None:
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    else:
        sw = np.sqrt(np.asarray(w, dtype=float).reshape(-1))
        coef, *_ = np.linalg.lstsq(A * sw[:, None], y * sw, rcond=None)
    return coef


def eval_through_zero(x: np.ndarray, coef: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    y = np.zeros_like(x, dtype=float)
    for k, c in enumerate(np.asarray(coef, dtype=float).reshape(-1), start=1):
        y = y + c * (x ** k)
    return y


def moving_average(y: np.ndarray, win: int) -> np.ndarray:
    """Centered boxcar; odd win; edge replicate. Chip cost O(N·W)."""
    y = np.asarray(y, dtype=float).reshape(-1)
    w = int(win)
    if w < 3:
        return y.copy()
    if w % 2 == 0:
        w += 1
    pad = w // 2
    yp = np.pad(y, (pad, pad), mode="edge")
    ker = np.ones(w, dtype=float) / float(w)
    return np.convolve(yp, ker, mode="valid")


def _interp_exclude(y: np.ndarray, exclude: Iterable[int]) -> np.ndarray:
    """Replace excluded indices by linear interpolation from neighbors."""
    out = np.asarray(y, dtype=float).copy()
    n = out.size
    good = np.ones(n, dtype=bool)
    for e in exclude:
        if 0 <= int(e) < n:
            good[int(e)] = False
    if not np.any(good):
        return out
    x = np.arange(n, dtype=float)
    out[~good] = np.interp(x[~good], x[good], out[good])
    return out


def detect_lut_outliers(
    amp: Sequence[float],
    phase: Sequence[float],
    *,
    amp_neigh_min: float = AUTO_AMP_NEIGH_MIN,
    amp_rel_thr: float = AUTO_AMP_REL_THR,
    amp_dip_factor: float = AUTO_AMP_DIP_FACTOR,
    amp_spike_factor: float = AUTO_AMP_SPIKE_FACTOR,
    phase_thr_rad: float = AUTO_PHASE_THR_RAD,
    amp_min_for_phase: float = AUTO_AMP_MIN_FOR_PHASE,
    phase_rel_thr: float = AUTO_PHASE_REL_THR,
) -> List[int]:
    """
    Auto-detect bad LUT bins (chip-friendly, O(N)).

    For each interior index ``k``, require both neighbors to have amplitude
    ``>= amp_neigh_min`` (avoids false hits on slave early zeros). Flag when
    amp is a dip/spike vs neighbor mean beyond ``amp_rel_thr``, optionally
    reinforced by a large unwrapped phase jump.
    """
    a = np.asarray(amp, dtype=float).reshape(-1)
    p = np.asarray(phase, dtype=float).reshape(-1)
    if a.size != p.size:
        raise ValueError("amp / phase length mismatch")
    n = int(a.size)
    bad: List[int] = []
    for k in range(1, n - 1):
        a_l = float(a[k - 1])
        a_c = float(a[k])
        a_r = float(a[k + 1])
        if a_l < amp_neigh_min or a_r < amp_neigh_min:
            continue
        pred = 0.5 * (a_l + a_r)
        rel = abs(a_c - pred) / max(pred, 1.0)
        is_dip = a_c < amp_dip_factor * min(a_l, a_r)
        is_spike = a_c > amp_spike_factor * max(a_l, a_r)
        ph_err = abs(float(p[k]) - 0.5 * (float(p[k - 1]) + float(p[k + 1])))
        is_ph = ph_err > phase_thr_rad and pred >= amp_min_for_phase
        if (is_dip or is_spike) and rel >= amp_rel_thr:
            bad.append(k)
        elif is_ph and rel >= phase_rel_thr and (is_dip or is_spike):
            bad.append(k)
    return bad


def resolve_exclude(
    exclude: Union[str, int, Iterable[int], None],
    amp: Sequence[float],
    phase: Sequence[float],
) -> Tuple[List[int], str]:
    """
    Resolve exclude spec → (indices, mode_label).

    * ``\"auto\"`` / ``None`` → ``detect_lut_outliers``
    * ``\"none\"`` / empty → no exclude
    * int / iterable of int → manual list
    * ``\"2,5\"`` → manual list from CSV string
    """
    if exclude is None:
        mode = "auto"
    elif isinstance(exclude, str):
        s = exclude.strip().lower()
        if s in ("", "none", "off", "disable", "disabled"):
            return [], "none"
        if s in ("auto", "detect", "default"):
            mode = "auto"
        else:
            idxs = sorted({int(x) for x in s.split(",") if str(x).strip() != ""})
            return idxs, "manual"
    elif isinstance(exclude, (int, np.integer)):
        return [int(exclude)], "manual"
    else:
        idxs = sorted({int(e) for e in exclude})
        if not idxs:
            return [], "none"
        return idxs, "manual"

    detected = detect_lut_outliers(amp, phase)
    return detected, "auto"


def _pick_phase_ref(amp: np.ndarray, *, prefer_index: int = 1, amp_min: float = 1.0) -> int:
    """Reference bin for global phase align (prefer index1 on master)."""
    n = int(amp.size)
    pref = int(prefer_index)
    if 0 <= pref < n and float(amp[pref]) >= amp_min:
        return pref
    for k in range(n):
        if float(amp[k]) >= amp_min:
            return k
    return 0


def _clamp_amp_dev(amp_fit: np.ndarray, amp_ref: np.ndarray, max_rel: float) -> np.ndarray:
    """Limit relative amp change vs reference (repaired) curve."""
    out = np.asarray(amp_fit, dtype=float).copy()
    ref = np.asarray(amp_ref, dtype=float)
    max_rel = float(max_rel)
    if max_rel <= 0.0:
        return out
    for k in range(out.size):
        r = float(ref[k])
        if r < 1.0:
            continue
        lo = r * (1.0 - max_rel)
        hi = r * (1.0 + max_rel)
        if out[k] < lo:
            out[k] = lo
        elif out[k] > hi:
            out[k] = hi
    return out


def _apply_master_phase_align(z_new: np.ndarray, *, do_force1: bool) -> np.ndarray:
    z = np.asarray(z_new, dtype=complex).copy()
    z[0] = 0.0 + 0.0j
    if do_force1 and z.size > 1 and abs(z[1]) >= 1.0:
        z = z * np.exp(-1j * np.angle(z[1]))
        z[1] = abs(z[1]) + 0j
    return z


def fit_lut_phase0(
    lut_i: Sequence[float],
    lut_q: Sequence[float],
    *,
    method: str = DEFAULT_METHOD,
    deg_amp: int = DEFAULT_DEG_AMP,
    deg_ph: int = DEFAULT_DEG_PH,
    ma_win: int = DEFAULT_MA_WIN,
    exclude: Union[str, int, Iterable[int], None] = DEFAULT_EXCLUDE,
    force_index1_real: bool = True,
    early_bins: int = DEFAULT_EARLY_BINS,
    early_w: float = DEFAULT_EARLY_W,
    late_w: float = DEFAULT_LATE_W,
    mix_amp: Optional[float] = None,
    mix_ph: Optional[float] = None,
    max_amp_dev: float = DEFAULT_MAX_AMP_DEV,
) -> dict:
    """
    Repair/smooth LUT and force phase through 0; rebuild fixed-point I/Q.

    method
      * ``poly``    — amp poly + preserve phase trend (default)
      * ``poly_ph`` — amp+phase both through-zero poly (legacy 1lut)
      * ``iqpoly`` / ``smooth`` / ``repair`` / ``ma`` — alternatives
    """
    method_l = str(method).strip().lower()
    if method_l not in ("smooth", "repair", "ma", "poly", "poly_ph", "iqpoly"):
        raise ValueError(
            f"unknown method={method!r} (use smooth|repair|ma|poly|poly_ph|iqpoly)"
        )

    ii = np.asarray(lut_i, dtype=float).reshape(-1)
    qq = np.asarray(lut_q, dtype=float).reshape(-1)
    if ii.size != qq.size:
        raise ValueError("lut_i / lut_q length mismatch")
    n = int(ii.size)
    z = ii + 1j * qq
    amp = np.abs(z)
    ph = np.unwrap(np.angle(z))
    x = np.arange(n, dtype=float)
    excl_raw, excl_mode = resolve_exclude(exclude, amp, ph)
    excl = sorted({int(e) for e in excl_raw if 0 <= int(e) < n})
    excl_set = set(excl)

    coef_amp = coef_ph = None
    ma_win_out = None
    mix_amp_out = mix_ph_out = None

    is_master = bool(force_index1_real)
    if mix_amp is None:
        mix_amp_v = DEFAULT_MIX_AMP_MASTER if is_master else DEFAULT_MIX_AMP_SLAVE
    else:
        mix_amp_v = float(mix_amp)
    if mix_ph is None:
        mix_ph_v = DEFAULT_MIX_PH_MASTER if is_master else DEFAULT_MIX_PH_SLAVE
    else:
        mix_ph_v = float(mix_ph)
    mix_amp_v = min(max(mix_amp_v, 0.0), 1.0)
    mix_ph_v = min(max(mix_ph_v, 0.0), 1.0)

    amp_w = _interp_exclude(amp, excl)
    ph_w = _interp_exclude(ph, excl)
    do_force1 = bool(force_index1_real) and n > 1 and (float(amp_w[1]) >= 1.0)

    if method_l == "repair":
        z_new = z.copy()
        for e in excl:
            z_new[e] = amp_w[e] * np.exp(1j * ph_w[e])
        z_new = _apply_master_phase_align(z_new, do_force1=do_force1)
        amp_fit = np.abs(z_new)
        ph_fit = np.unwrap(np.angle(z_new))

    elif method_l == "smooth":
        ma_win_out = int(ma_win)
        mix_amp_out, mix_ph_out = mix_amp_v, mix_ph_v
        amp_s = moving_average(amp_w, ma_win_out)
        ph_s = moving_average(ph_w, ma_win_out)
        amp_fit = (1.0 - mix_amp_v) * amp_w + mix_amp_v * amp_s
        ph_fit = (1.0 - mix_ph_v) * ph_w + mix_ph_v * ph_s
        amp_fit = _clamp_amp_dev(amp_fit, amp_w, float(max_amp_dev))
        amp_fit = np.maximum(amp_fit, 0.0)
        amp_fit[0] = 0.0
        # Keep master index1 amplitude (often HW gain anchor); phase still aligned below.
        if do_force1:
            amp_fit[1] = float(amp_w[1])
        z_new = amp_fit * np.exp(1j * ph_fit)
        z_new = _apply_master_phase_align(z_new, do_force1=do_force1)
        amp_fit = np.abs(z_new)
        ph_fit = np.unwrap(np.angle(z_new))

    elif method_l == "iqpoly":
        ii_w = _interp_exclude(ii, excl)
        qq_w = _interp_exclude(qq, excl)
        fit_mask = np.array([k not in excl_set for k in range(n)], dtype=bool)
        if int(np.count_nonzero(fit_mask)) < int(deg_amp) + 1:
            raise ValueError("too few fit points for iqpoly degree")
        w_full = default_weights(n, early_bins=early_bins, early_w=early_w, late_w=late_w)
        xf = x[fit_mask]
        ww = w_full[fit_mask]
        deg = max(int(deg_amp), int(deg_ph), 1)
        coef_amp = poly_through_zero(xf, ii_w[fit_mask], deg, w=ww)
        coef_ph = poly_through_zero(xf, qq_w[fit_mask], deg, w=ww)
        i_fit = eval_through_zero(x, coef_amp)
        q_fit = eval_through_zero(x, coef_ph)
        z_new = i_fit + 1j * q_fit
        z_new = _apply_master_phase_align(z_new, do_force1=do_force1)
        if do_force1 and abs(z[1]) >= 1.0:
            z_new[1] = abs(z[1]) + 0j
        elif not do_force1:
            keep_zero_thr = 50.0
            for k in range(n):
                if float(amp[k]) < keep_zero_thr:
                    z_new[k] = z[k]
        amp_fit = np.abs(z_new)
        ph_fit = np.unwrap(np.angle(z_new))

    else:
        if method_l == "ma":
            ma_win_out = int(ma_win)
            amp_fit = moving_average(amp_w, ma_win_out)
            ph_fit = moving_average(ph_w, ma_win_out)
        elif method_l == "poly_ph":
            # Legacy: amp + phase both no-constant poly (ok when mid φ≈0)
            fit_mask = np.array([(k not in excl_set) and (amp[k] > 0.0) for k in range(n)])
            if int(np.count_nonzero(fit_mask)) < max(deg_amp, deg_ph) + 1:
                raise ValueError("too few fit points for poly_ph degree")
            w_full = default_weights(n, early_bins=early_bins, early_w=early_w, late_w=late_w)
            xf = x[fit_mask]
            ww = w_full[fit_mask]
            coef_amp = poly_through_zero(xf, amp[fit_mask], deg_amp, w=ww)
            coef_ph = poly_through_zero(xf, ph[fit_mask], deg_ph, w=ww)
            amp_fit = eval_through_zero(x, coef_amp)
            ph_fit = eval_through_zero(x, coef_ph)
        else:
            # poly (default): amp through-zero poly; keep repaired phase trend.
            # Through-zero phase poly systematically pulls mid-band down when the
            # trained AM-PM sits at ~3–8° (260825 3lut lut0).
            fit_mask = np.array([(k not in excl_set) and (amp[k] > 0.0) for k in range(n)])
            if int(np.count_nonzero(fit_mask)) < int(deg_amp) + 1:
                raise ValueError("too few fit points for poly amp degree")
            w_full = default_weights(n, early_bins=early_bins, early_w=early_w, late_w=late_w)
            xf = x[fit_mask]
            ww = w_full[fit_mask]
            coef_amp = poly_through_zero(xf, amp[fit_mask], deg_amp, w=ww)
            amp_fit = eval_through_zero(x, coef_amp)
            # Keep repaired phase exactly (no MA) — mid-band trend is trained DPD
            ph_fit = ph_w.copy()

        amp_fit = np.maximum(amp_fit, 0.0)
        amp_fit[0] = 0.0
        if do_force1:
            # Subtract φ[1] so index1 is real; preserves relative phase shape
            ph_fit = ph_fit - float(ph_fit[1] if amp_fit[1] >= 1.0 else ph_fit[0])
        z_new = amp_fit * np.exp(1j * ph_fit)
        near0 = amp_fit < 1.0
        z_new[near0] = 0.0
        if do_force1:
            if abs(z[1]) >= 1.0:
                z_new[1] = abs(z[1]) + 0j
            else:
                z_new[1] = abs(z_new[1]) + 0j
            if abs(z_new[1]) >= 1.0 and abs(np.angle(z_new[1])) > 1e-12:
                z_new = z_new * np.exp(-1j * np.angle(z_new[1]))
                z_new[1] = abs(z_new[1]) + 0j
        else:
            keep_zero_thr = 50.0
            for k in range(n):
                if float(amp[k]) < keep_zero_thr:
                    z_new[k] = z[k]
        amp_fit = np.abs(z_new)
        ph_fit = np.unwrap(np.angle(z_new))

    i_out = np.rint(np.real(z_new)).astype(int)
    q_out = np.rint(np.imag(z_new)).astype(int)
    i_out[0] = 0
    q_out[0] = 0
    if do_force1:
        q_out[1] = 0
        # Prefer exact original index1 amp after rounding
        if abs(z[1]) >= 1.0:
            i_out[1] = int(round(abs(z[1])))
        else:
            i_out[1] = int(abs(i_out[1]))

    return {
        "n_pts": n,
        "method": method_l,
        "i_out": i_out,
        "q_out": q_out,
        "amp_orig": amp,
        "phase_orig": ph,
        "amp_fit": np.abs(i_out.astype(float) + 1j * q_out.astype(float)),
        "phase_fit": np.unwrap(np.angle(i_out.astype(float) + 1j * q_out.astype(float))),
        "coef_amp": coef_amp,
        "coef_ph": coef_ph,
        "exclude": excl,
        "exclude_mode": excl_mode,
        "ma_win": ma_win_out,
        "mix_amp": mix_amp_out,
        "mix_ph": mix_ph_out,
        "max_amp_dev": float(max_amp_dev) if method_l == "smooth" else None,
        "force_index1_real": do_force1,
    }


# ---------------------------------------------------------------------------
# Plot / run
# ---------------------------------------------------------------------------

def plot_fit_result(result: dict, save_path: PathLike, *, title: str = "") -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = int(result["n_pts"])
    x = np.arange(n)
    i_out = result["i_out"]
    q_out = result["q_out"]
    z_out = i_out.astype(float) + 1j * q_out.astype(float)
    amp_out = np.abs(z_out)
    ph_out = np.unwrap(np.angle(z_out))

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    ax = axes[0, 0]
    ax.plot(x, result["amp_orig"], "o:", label="orig amp")
    ax.plot(x, result["amp_fit"], "-", lw=2, label=f"fit amp ({result['method']})")
    ax.plot(x, amp_out, "s-", ms=3, label="out amp")
    for e in result["exclude"]:
        ax.scatter([e], [result["amp_orig"][e]], c="r", s=60, zorder=5)
    ax.set_title("AM vs LUT index")
    ax.grid(True, alpha=0.35)
    ax.legend(fontsize=8)

    ax = axes[0, 1]
    ax.plot(x, np.degrees(result["phase_orig"]), "o:", label="orig phase")
    ax.plot(x, np.degrees(result["phase_fit"]), "-", lw=2, label="fit phase")
    ax.plot(x, np.degrees(ph_out), "s-", ms=3, label="out phase")
    ax.axhline(0, color="k", lw=0.8, alpha=0.5)
    ax.set_title("Phase (deg), forced through 0")
    ax.grid(True, alpha=0.35)
    ax.legend(fontsize=8)

    ax = axes[1, 0]
    ax.plot(x, np.real(result["amp_orig"] * np.exp(1j * result["phase_orig"])), "o:", label="orig I")
    ax.plot(x, i_out, "s-", ms=3, label="new I")
    ax.set_title("I")
    ax.grid(True, alpha=0.35)
    ax.legend(fontsize=8)

    ax = axes[1, 1]
    ax.plot(x, np.imag(result["amp_orig"] * np.exp(1j * result["phase_orig"])), "o:", label="orig Q")
    ax.plot(x, q_out, "s-", ms=3, label="new Q")
    ax.set_title("Q")
    ax.grid(True, alpha=0.35)
    ax.legend(fontsize=8)

    fig.suptitle(title or "LUT phase-through-0 fit", fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = Path(save_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def run_file(
    input_path: PathLike,
    output_dir: PathLike,
    *,
    lut_sel: int = 0,
    map_name: Optional[str] = None,
    method: str = DEFAULT_METHOD,
    deg_amp: int = DEFAULT_DEG_AMP,
    deg_ph: int = DEFAULT_DEG_PH,
    ma_win: int = DEFAULT_MA_WIN,
    exclude: Union[str, int, Iterable[int], None] = DEFAULT_EXCLUDE,
    force_index1_real: bool = True,
    mix_amp: Optional[float] = None,
    mix_ph: Optional[float] = None,
    max_amp_dev: float = DEFAULT_MAX_AMP_DEV,
    plot: bool = True,
    copy_only: bool = False,
    write_hw_names: bool = True,
) -> dict:
    """Load one map → fit (or copy) → write outputs."""
    inp = Path(input_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    lut_map = load_lut_data_map(inp, map_name=map_name)
    ii, qq = map_to_arrays(lut_map)

    if copy_only:
        i_out = np.rint(ii).astype(int)
        q_out = np.rint(qq).astype(int)
        result = {
            "n_pts": int(ii.size),
            "method": "copy",
            "i_out": i_out,
            "q_out": q_out,
            "amp_orig": np.abs(ii + 1j * qq),
            "phase_orig": np.unwrap(np.angle(ii + 1j * qq)),
            "amp_fit": np.abs(ii + 1j * qq),
            "phase_fit": np.unwrap(np.angle(ii + 1j * qq)),
            "coef_amp": None,
            "coef_ph": None,
            "exclude": [],
            "exclude_mode": "none",
            "ma_win": None,
            "force_index1_real": False,
        }
        stem = inp.stem + "_passthrough"
        header = [
            f"# Passthrough (not smoothed) from {inp.name}",
            f"# scope skipped this lut_sel={lut_sel}",
        ]
    else:
        result = fit_lut_phase0(
            ii,
            qq,
            method=method,
            deg_amp=deg_amp,
            deg_ph=deg_ph,
            ma_win=ma_win,
            exclude=exclude,
            force_index1_real=force_index1_real,
            mix_amp=mix_amp,
            mix_ph=mix_ph,
            max_amp_dev=max_amp_dev,
        )
        stem = inp.stem + f"_phase0_{result['method']}"
        header = [
            f"# Optimized by lut_phase0_fit.py from {inp.name}",
            f"# method={result['method']}; phase through 0 (global rotate / smooth)",
            f"# exclude_mode={result['exclude_mode']} exclude={list(result['exclude'])}; "
            f"ma_win={result['ma_win']}; mix_amp={result.get('mix_amp')} mix_ph={result.get('mix_ph')}; "
            f"max_amp_dev={result.get('max_amp_dev')}; deg_amp={deg_amp} deg_ph={deg_ph}; "
            f"force_i1_real={result['force_index1_real']}",
        ]

    txt_path = write_lut_data_map(
        out_dir / f"{stem}.txt",
        result["i_out"],
        result["q_out"],
        lut_sel=lut_sel,
        header_lines=header,
    )
    csv_path = write_iq_csv(out_dir / f"{stem}.csv", result["i_out"], result["q_out"])
    hw_path = None
    if write_hw_names:
        hw_header = list(header) + [f"# HW-ready copy: lut_data_map_lut{int(lut_sel)}.txt"]
        hw_path = write_lut_data_map(
            out_dir / f"lut_data_map_lut{int(lut_sel)}.txt",
            result["i_out"],
            result["q_out"],
            lut_sel=lut_sel,
            header_lines=hw_header,
        )
    png_path = None
    if plot and not copy_only:
        png_path = plot_fit_result(
            result, out_dir / f"{stem}.png", title=f"{inp.name}  [{result['method']}]"
        )

    excl_note = (
        f"exclude={result.get('exclude_mode', '?')}->{list(result.get('exclude', []))}"
        if not copy_only
        else "passthrough"
    )
    print(f"[OK] lut{lut_sel} method={result['method']} {excl_note} -> {txt_path.name}")
    if hw_path is not None:
        print(f"     HW map -> {hw_path.name}")
    result["txt_path"] = txt_path
    result["csv_path"] = csv_path
    result["hw_path"] = hw_path
    result["png_path"] = png_path
    result["lut_sel"] = int(lut_sel)
    return result


def run_multi(
    input_path: PathLike,
    output_dir: PathLike,
    *,
    method: str = DEFAULT_METHOD,
    master_lut: Optional[int] = None,
    scope: str = "all",
    slave_method: Optional[str] = None,
    deg_amp: int = DEFAULT_DEG_AMP,
    deg_ph: int = DEFAULT_DEG_PH,
    ma_win: int = DEFAULT_MA_WIN,
    exclude: Union[str, int, Iterable[int], None] = DEFAULT_EXCLUDE,
    mix_amp: Optional[float] = None,
    mix_ph: Optional[float] = None,
    max_amp_dev: float = DEFAULT_MAX_AMP_DEV,
    plot: bool = True,
    write_hw_names: bool = True,
) -> List[dict]:
    """
    Process one file or a directory of ``lut_data_map_lut*.txt``.

    scope
      * ``all`` — process every discovered LUT
      * ``master_only`` — process only ``master_lut``; others passthrough

    slave_method (when ``master_lut`` set and scope=all)
      * ``None`` / auto — for heavy methods (poly/iqpoly/ma) use ``passthrough``
        so memory taps are not rewritten; otherwise same as ``method``
      * ``passthrough`` / ``repair`` / ``smooth`` / ``poly`` / ... — explicit
    """
    scope_l = str(scope).strip().lower()
    if scope_l not in ("all", "master_only"):
        raise ValueError("scope must be all|master_only")
    if scope_l == "master_only" and master_lut is None:
        raise ValueError("master_lut is required when scope=master_only")

    method_l = str(method).strip().lower()
    if slave_method is None:
        if master_lut is not None and method_l in ("poly", "poly_ph", "iqpoly", "ma"):
            slave_method_l = "passthrough"
        else:
            slave_method_l = "same"
    else:
        slave_method_l = str(slave_method).strip().lower()

    items = discover_lut_maps(input_path)
    out_dir = Path(output_dir)
    results: List[dict] = []
    for path, sel in items:
        is_master = (master_lut is None) or (int(sel) == int(master_lut))
        do_copy = (scope_l == "master_only" and not is_master) or (
            (not is_master) and slave_method_l == "passthrough"
        )
        if is_master or do_copy:
            method_use = method_l
        elif slave_method_l == "same":
            method_use = method_l
        else:
            method_use = slave_method_l
        # Only force index1 real on master (or when master not specified)
        force1 = is_master
        r = run_file(
            path,
            out_dir,
            lut_sel=sel,
            method=method_use,
            deg_amp=deg_amp,
            deg_ph=deg_ph,
            ma_win=ma_win,
            exclude=exclude,
            force_index1_real=force1 and not do_copy,
            mix_amp=mix_amp,
            mix_ph=mix_ph,
            max_amp_dev=max_amp_dev,
            plot=plot,
            copy_only=do_copy,
            write_hw_names=write_hw_names,
        )
        r["master_lut"] = master_lut
        r["scope"] = scope_l
        results.append(r)

    # Combined map file for convenience
    combined = out_dir / f"lut_data_map_all_phase0_{method}.txt"
    lines = [
        f"# Combined LUT maps after phase0 fit  method={method} scope={scope_l} "
        f"master_lut={master_lut} slave_method={slave_method_l}",
        "",
    ]
    for r in results:
        lines.append(Path(r["txt_path"]).read_text(encoding="utf-8").rstrip())
        lines.append("")
    combined.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] combined -> {combined}")
    return results


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="LUT phase-through-0 fit (smooth|repair|ma|poly|iqpoly); multi-LUT / master."
    )
    p.add_argument("input", help="lut_data_map txt OR directory with lut_data_map_lut*.txt")
    p.add_argument("-o", "--output-dir", default="", help="output dir (default: input dir)")
    p.add_argument(
        "--method",
        choices=["smooth", "repair", "ma", "poly", "poly_ph", "iqpoly"],
        default=DEFAULT_METHOD,
        help="poly=amp poly + keep phase trend (default); poly_ph=amp+phase poly; "
        "iqpoly/smooth/repair/ma alternatives",
    )
    p.add_argument("--ma-win", type=int, default=DEFAULT_MA_WIN, help="MA window (odd, default 5)")
    p.add_argument(
        "--mix-amp",
        type=float,
        default=None,
        help="smooth: amp blend toward MA (default master 0.50 / slave 0.35)",
    )
    p.add_argument(
        "--mix-ph",
        type=float,
        default=None,
        help="smooth: phase blend toward MA (default master 0.80 / slave 0.65)",
    )
    p.add_argument(
        "--max-amp-dev",
        type=float,
        default=DEFAULT_MAX_AMP_DEV,
        help="smooth: max relative amp deviation vs repaired (default 0.10)",
    )
    p.add_argument("--deg-amp", type=int, default=DEFAULT_DEG_AMP)
    p.add_argument("--deg-ph", type=int, default=DEFAULT_DEG_PH)
    p.add_argument(
        "--exclude",
        default=DEFAULT_EXCLUDE,
        help="auto (default: detect dips/spikes) | none | comma indices e.g. 2,5",
    )
    p.add_argument(
        "--master-lut",
        type=int,
        default=None,
        help="optional master LUT index (reg_dpd_master_lut)",
    )
    p.add_argument(
        "--scope",
        choices=["all", "master_only"],
        default="all",
        help="all=process every LUT; master_only=process only --master-lut",
    )
    p.add_argument(
        "--slave-method",
        default="",
        help="when --master-lut set: passthrough|repair|smooth|poly|same|auto. "
        "auto (default): passthrough for poly/iqpoly/ma (protect memory taps)",
    )
    p.add_argument("--no-plot", action="store_true")
    p.add_argument(
        "--no-hw-names",
        action="store_true",
        help="do not also write lut_data_map_lutN.txt (HW-ready names)",
    )
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    inp = Path(args.input)
    out_dir = Path(args.output_dir) if args.output_dir else (inp if inp.is_dir() else inp.parent)
    run_multi(
        inp,
        out_dir,
        method=args.method,
        master_lut=args.master_lut,
        scope=args.scope,
        slave_method=(None if not str(args.slave_method).strip() else str(args.slave_method).strip()),
        deg_amp=int(args.deg_amp),
        deg_ph=int(args.deg_ph),
        ma_win=int(args.ma_win),
        exclude=str(args.exclude),
        mix_amp=args.mix_amp,
        mix_ph=args.mix_ph,
        max_amp_dev=float(args.max_amp_dev),
        plot=not args.no_plot,
        write_hw_names=not args.no_hw_names,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
