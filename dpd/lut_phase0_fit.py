#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Force DPD LUT AM-PM through phase 0, then poly-smooth amplitude/phase.

Typical use: hardware ``dpd_lut_read`` dump (``lut_data_map_lut*.txt``) has
noisy Q / outliers; fit amp & phase vs LUT index with **no constant term**
so ``amp(0)=0`` and ``phase(0)=0``, rebuild I/Q, write a new map.

CLI::

  python dpd/lut_phase0_fit.py INPUT_lut_data_map.txt -o OUT_DIR
  python dpd/lut_phase0_fit.py INPUT.txt --deg-amp 4 --deg-ph 4 --exclude 2
"""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np

PathLike = Union[str, Path]

DEFAULT_N_PTS = 33
DEFAULT_DEG_AMP = 4
DEFAULT_DEG_PH = 4
DEFAULT_EXCLUDE = (2,)  # common bad bin after hw readback
DEFAULT_EARLY_W = 1.0
DEFAULT_LATE_W = 200.0
DEFAULT_EARLY_BINS = 3


def parse_lut_data_map(text: str, *, map_name: Optional[str] = None) -> Dict[int, Tuple[int, int]]:
    """
    Parse ``lut_data_map_lutN = { ... }`` from a text/py dump.

    Returns
    -------
    dict index -> (i, q) as ints
    """
    if map_name:
        start_re = re.compile(rf"{re.escape(map_name)}\s*=\s*\{{")
    else:
        start_re = re.compile(r"lut_data_map_lut\d+\s*=\s*\{")
    m = start_re.search(text)
    if not m:
        raise ValueError("no lut_data_map_lut* dict found in text")
    i0 = m.end() - 1  # position of '{'
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
    """Return (i, q) float arrays length n_pts; missing keys → 0."""
    ii = np.zeros(n_pts, dtype=float)
    qq = np.zeros(n_pts, dtype=float)
    for k, (i_v, q_v) in lut_map.items():
        if 0 <= int(k) < n_pts:
            ii[int(k)] = float(i_v)
            qq[int(k)] = float(q_v)
    return ii, qq


def poly_through_zero(
    x: np.ndarray,
    y: np.ndarray,
    deg: int,
    *,
    w: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Weighted LS: ``y ≈ sum_{k=1..deg} c_k * x^k`` (no constant → y(0)=0).

    Returns coefficient vector ``c`` length ``deg`` (c[0] multiplies x^1).
    """
    deg = int(deg)
    if deg < 1:
        raise ValueError("deg must be >= 1")
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    if x.size != y.size:
        raise ValueError("x/y length mismatch")
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


def default_weights(
    n_pts: int,
    *,
    early_bins: int = DEFAULT_EARLY_BINS,
    early_w: float = DEFAULT_EARLY_W,
    late_w: float = DEFAULT_LATE_W,
) -> np.ndarray:
    """Same idea as MATLAB ``polyfit_for_lut`` Q diagonal."""
    w = np.full(n_pts, float(late_w), dtype=float)
    w[: max(0, int(early_bins))] = float(early_w)
    return w


def fit_lut_phase0(
    lut_i: Sequence[float],
    lut_q: Sequence[float],
    *,
    deg_amp: int = DEFAULT_DEG_AMP,
    deg_ph: int = DEFAULT_DEG_PH,
    exclude: Iterable[int] = DEFAULT_EXCLUDE,
    force_index1_real: bool = True,
    early_bins: int = DEFAULT_EARLY_BINS,
    early_w: float = DEFAULT_EARLY_W,
    late_w: float = DEFAULT_LATE_W,
) -> dict:
    """
    Fit amplitude & unwrapped phase vs LUT index through the origin; rebuild I/Q.

    Parameters
    ----------
    lut_i, lut_q :
        Length-N fixed-point LUT (typically N=33, index 0 is zero pad).
    deg_amp, deg_ph :
        Polynomial degrees for amp / phase (terms x^1 .. x^deg only).
    exclude :
        LUT indices excluded from the fit (e.g. known outliers).
    force_index1_real :
        After rebuild, set ``q[1]=0`` and keep ``|z[1]|`` on I (phase 0 at first bin).

    Returns
    -------
    dict with keys:
      ``i_out``, ``q_out`` (int arrays),
      ``amp_fit``, ``phase_fit`` (float),
      ``coef_amp``, ``coef_ph``,
      ``exclude``, ``n_pts``
    """
    ii = np.asarray(lut_i, dtype=float).reshape(-1)
    qq = np.asarray(lut_q, dtype=float).reshape(-1)
    if ii.size != qq.size:
        raise ValueError("lut_i / lut_q length mismatch")
    n = int(ii.size)
    z = ii + 1j * qq
    amp = np.abs(z)
    ph = np.unwrap(np.angle(z))
    x = np.arange(n, dtype=float)

    excl = {int(e) for e in exclude}
    fit_mask = np.array([(k not in excl) and (amp[k] > 0.0) for k in range(n)], dtype=bool)
    if int(np.count_nonzero(fit_mask)) < max(deg_amp, deg_ph) + 1:
        raise ValueError(
            f"too few fit points ({int(np.count_nonzero(fit_mask))}) "
            f"for deg_amp={deg_amp} deg_ph={deg_ph}"
        )

    w_full = default_weights(n, early_bins=early_bins, early_w=early_w, late_w=late_w)
    xf = x[fit_mask]
    w = w_full[fit_mask]
    coef_amp = poly_through_zero(xf, amp[fit_mask], deg_amp, w=w)
    coef_ph = poly_through_zero(xf, ph[fit_mask], deg_ph, w=w)

    amp_fit = eval_through_zero(x, coef_amp)
    ph_fit = eval_through_zero(x, coef_ph)
    amp_fit[0] = 0.0
    ph_fit[0] = 0.0

    z_new = amp_fit * np.exp(1j * ph_fit)
    if force_index1_real and n > 1:
        z_new[1] = abs(z_new[1]) + 0j

    i_out = np.rint(np.real(z_new)).astype(int)
    q_out = np.rint(np.imag(z_new)).astype(int)
    i_out[0] = 0
    q_out[0] = 0
    if force_index1_real and n > 1:
        q_out[1] = 0
        i_out[1] = int(np.rint(abs(complex(i_out[1], 0))))

    return {
        "n_pts": n,
        "i_out": i_out,
        "q_out": q_out,
        "amp_orig": amp,
        "phase_orig": ph,
        "amp_fit": amp_fit,
        "phase_fit": ph_fit,
        "coef_amp": coef_amp,
        "coef_ph": coef_ph,
        "exclude": sorted(excl),
        "fit_mask": fit_mask,
    }


def format_lut_data_map(
    i_out: Sequence[int],
    q_out: Sequence[int],
    *,
    lut_sel: int = 0,
    header_lines: Optional[List[str]] = None,
) -> str:
    """Render ``lut_data_map_lut{N}`` text matching wifi_dpd_test_wifi7 style."""
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
    """Simple ``index,i,q`` CSV for the C tool."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["index,i,q"]
    for k in range(min(len(i_arr), len(q_arr))):
        lines.append(f"{k},{int(i_arr[k])},{int(q_arr[k])}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


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
    ax.plot(x, result["amp_fit"], "-", lw=2, label="fit amp")
    ax.plot(x, amp_out, "s-", ms=3, label="out amp")
    for e in result["exclude"]:
        if 0 <= e < n:
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

    # recover orig i/q from amp/phase for plot — use complex from fit inputs
    # Caller may not pass orig i/q; reconstruct from amp/phase only for phase plot.
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
    deg_amp: int = DEFAULT_DEG_AMP,
    deg_ph: int = DEFAULT_DEG_PH,
    exclude: Sequence[int] = DEFAULT_EXCLUDE,
    plot: bool = True,
) -> dict:
    """Load map → fit → write ``*_phase0fit.txt`` / csv / optional png."""
    inp = Path(input_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    lut_map = load_lut_data_map(inp, map_name=map_name)
    ii, qq = map_to_arrays(lut_map)
    result = fit_lut_phase0(
        ii, qq, deg_amp=deg_amp, deg_ph=deg_ph, exclude=exclude
    )

    stem = inp.stem + "_phase0fit"
    header = [
        f"# Optimized by lut_phase0_fit.py from {inp.name}",
        "# phase forced through 0: amp/phase polyfit vs LUT index, no constant term",
        f"# exclude={list(result['exclude'])}; index1 Q forced 0; "
        f"deg_amp={deg_amp} deg_ph={deg_ph}",
    ]
    txt_path = write_lut_data_map(
        out_dir / f"{stem}.txt",
        result["i_out"],
        result["q_out"],
        lut_sel=lut_sel,
        header_lines=header,
    )
    csv_path = write_iq_csv(out_dir / f"{stem}.csv", result["i_out"], result["q_out"])
    png_path = None
    if plot:
        png_path = plot_fit_result(
            result,
            out_dir / f"{stem}.png",
            title=f"LUT phase0 fit  ({inp.name})",
        )

    print(f"[OK] map  → {txt_path}")
    print(f"[OK] csv  → {csv_path}")
    if png_path:
        print(f"[OK] plot → {png_path}")
    print(
        f"[OK] phase@0={np.degrees(np.angle(complex(result['i_out'][0], result['q_out'][0]))):.3f} deg, "
        f"phase@1={np.degrees(np.angle(complex(result['i_out'][1], result['q_out'][1]))):.3f} deg"
    )
    result["txt_path"] = txt_path
    result["csv_path"] = csv_path
    result["png_path"] = png_path
    return result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Fit DPD LUT so AM-PM phase passes through 0 (no-constant poly)."
    )
    p.add_argument("input", help="lut_data_map_lut*.txt (or .py) from dpd_lut_read")
    p.add_argument(
        "-o",
        "--output-dir",
        default="",
        help="output directory (default: same as input)",
    )
    p.add_argument("--lut-sel", type=int, default=0, help="lut_data_map_lut{N} name index")
    p.add_argument("--map-name", default="", help="optional exact dict name to parse")
    p.add_argument("--deg-amp", type=int, default=DEFAULT_DEG_AMP)
    p.add_argument("--deg-ph", type=int, default=DEFAULT_DEG_PH)
    p.add_argument(
        "--exclude",
        default=",".join(str(x) for x in DEFAULT_EXCLUDE),
        help="comma-separated LUT indices to exclude (default: 2)",
    )
    p.add_argument("--no-plot", action="store_true")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    inp = Path(args.input)
    out_dir = Path(args.output_dir) if args.output_dir else inp.parent
    exclude = [int(s) for s in str(args.exclude).split(",") if str(s).strip() != ""]
    run_file(
        inp,
        out_dir,
        lut_sel=int(args.lut_sel),
        map_name=(args.map_name or None),
        deg_amp=int(args.deg_amp),
        deg_ph=int(args.deg_ph),
        exclude=exclude,
        plot=not args.no_plot,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
