#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RX IQ calibration PSD — 1:1 port of Xian myplot.psd_plot_rx_cal.

Diff vs original myplot.py:
  - bw / ch_freq / freqcw from config (not parsed from fname regex)
  - real_data / image_data loaded from specified CSV (12-bit signed → float normalize)
  - CLI input may be a single CSV or a directory of CSVs (batch)
  - I/Q column names configurable via COL_I/COL_Q (or --col-i/--col-q)

12-bit signed input:
  - normalize: code / 2**(ADC_BIT_WIDTH-1)  (12-bit → /2048)
  - sig_pwr: int(norm * 2**(N-1))**2 averaged, / 2**N  (same as myplot 2**11 & 4096)
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from scipy.signal import welch

# =============================================================================
# Config（替代 myplot 从 fname 正则提取的 bw / chan / freqcw）
# =============================================================================
INPUT_CSV = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\rftest_data\dump_adc_0x200_raw\FPGA752_0x_20260722\result"
OUTPUT_PDF = ""  # 空 → <INPUT_CSV stem>.pdf（同 myplot: fname + '.pdf'）

BW_MHZ = 20  # phymd
CH_FREQ_MHZ = 2412  # chan
FREQCW_MHZ = 2417 # freqcw

# Welch 采样率 MHz：须与 dump 实际 ADC 采样率一致，频谱横轴与 tone 定位共用
# 0 = myplot 按 BW 映射（20→40）；ILA 全速率 20MHz 带宽常用 160
SAMPLE_FREQ_MHZ = 80

# 数据重复时先做 2 抽 1（I/Q 各取 [::2]），Welch 有效 Fs = SAMPLE_FREQ_MHZ / DECIMATE_FACTOR
DECIMATE_FACTOR = 1  # 1 = 不抽取

MAX_ROWS = 65536  # 0 = read all
IQ_MODE = "single"  # auto | single | 2ant
USE_CH = 0

# 输入为 12-bit 有符号 ADC 码（如 ILA [11:0]）；归一化除数 2**(N-1)=2048
ADC_BIT_WIDTH = 12

# I/Q 列名（可按 CSV 实际表头改；匹配时忽略大小写与首尾空格）
COL_I = "sample_i"
COL_Q = "sample_q"
# 2ant 布局列名（mode=2ant / auto 检测到双天线时使用）
COL_CH0_I = "ch0_sample_i"
COL_CH0_Q = "ch0_sample_q"
COL_CH1_I = "ch1_sample_i"
COL_CH1_Q = "ch1_sample_q"


def signed_adc_scale(adc_bit_width: int = ADC_BIT_WIDTH) -> int:
    """Full-scale for signed N-bit: 2**(N-1)."""
    return 2 ** (int(adc_bit_width) - 1)


def signed_adc_full_scale(adc_bit_width: int = ADC_BIT_WIDTH) -> int:
    """sig_pwr denominator for signed N-bit: 2**N."""
    return 2 ** int(adc_bit_width)


def bw_to_sample_freq_mhz(bw: int) -> float:
    """myplot: Welch Fs / all_freq from phymd bandwidth only."""
    bw = int(bw)
    if bw == 20:
        return 40.0
    if bw == 40:
        return 80.0
    if bw == 80:
        return 160.0
    return 320.0


def resolve_sample_freq_mhz(bw: int, sample_freq_mhz: float = 0) -> float:
    """Use explicit SAMPLE_FREQ_MHZ when >0; else myplot bw mapping."""
    if sample_freq_mhz and sample_freq_mhz > 0:
        return float(sample_freq_mhz)
    return bw_to_sample_freq_mhz(bw)


def decimate_iq(
    real_data: np.ndarray,
    image_data: np.ndarray,
    factor: int = DECIMATE_FACTOR,
) -> Tuple[np.ndarray, np.ndarray]:
    """2 抽 1: I/Q 各取 [::factor]。"""
    if factor <= 1:
        return real_data, image_data
    return real_data[::factor], image_data[::factor]


def effective_sample_freq_mhz(
    bw: int,
    sample_freq_mhz: float,
    decimate_factor: int = DECIMATE_FACTOR,
) -> float:
    """Welch Fs after optional decimation."""
    fs = resolve_sample_freq_mhz(bw, sample_freq_mhz)
    if decimate_factor > 1:
        return fs / float(decimate_factor)
    return fs


def _col_map(columns: Sequence[str]) -> dict:
    return {str(c).strip().lower(): str(c).strip() for c in columns}


def _resolve_col(lower: dict, name: str, *, kind: str) -> str:
    key = str(name).strip().lower()
    if key not in lower:
        raise ValueError(
            f"missing {kind} column {name!r}; available={sorted(lower.values())}"
        )
    return lower[key]


def load_real_image_from_csv(
    csv_file: Union[str, Path],
    *,
    max_rows: int = MAX_ROWS,
    mode: str = IQ_MODE,
    use_ch: int = USE_CH,
    adc_bit_width: int = ADC_BIT_WIDTH,
    decimate_factor: int = DECIMATE_FACTOR,
    col_i: str = COL_I,
    col_q: str = COL_Q,
    col_ch0_i: str = COL_CH0_I,
    col_ch0_q: str = COL_CH0_Q,
    col_ch1_i: str = COL_CH1_I,
    col_ch1_q: str = COL_CH1_Q,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Read signed I/Q CSV and normalize for psd_plot_rx_cal:
      real_data = I / 2**(ADC_BIT_WIDTH-1)
      image_data = Q / 2**(ADC_BIT_WIDTH-1)
      optional 2:1 decimate [::2] when data has duplicates
      truncate to 2**floor(log2(N)) samples (adc_dump ll = 2**int(log2(data_ll)))

    Column names are configurable (COL_I / COL_Q or CLI --col-i / --col-q).
    """
    csv_path = Path(csv_file)
    head = pd.read_csv(csv_path, nrows=0)
    lower = _col_map(list(head.columns))

    # Prefer explicit single-stream columns when present / mode=single
    has_single = (
        str(col_i).strip().lower() in lower and str(col_q).strip().lower() in lower
    )
    has_2ant = all(
        str(n).strip().lower() in lower
        for n in (col_ch0_i, col_ch0_q, col_ch1_i, col_ch1_q)
    )

    layout = str(mode).lower()
    if layout == "auto":
        if has_2ant and not has_single:
            layout = "2ant"
        elif has_single:
            layout = "single"
        elif has_2ant:
            layout = "2ant"
        else:
            raise ValueError(
                f"cannot find I/Q columns in {csv_path.name}: "
                f"need {col_i!r}/{col_q!r} or "
                f"{col_ch0_i!r}/{col_ch0_q!r}/{col_ch1_i!r}/{col_ch1_q!r}; "
                f"available={sorted(lower.values())}"
            )

    if layout == "single":
        ci = _resolve_col(lower, col_i, kind="I")
        cq = _resolve_col(lower, col_q, kind="Q")
        usecols = [ci, cq]
        read_kwargs = {"usecols": usecols}
        if max_rows and max_rows > 0:
            read_kwargs["nrows"] = int(max_rows)
        df = pd.read_csv(csv_path, **read_kwargs)
        i_raw = df[ci].to_numpy()
        q_raw = df[cq].to_numpy()
        print(f"[COLS] single I={ci!r} Q={cq!r} N={len(i_raw)}")
    elif layout == "2ant":
        c0i = _resolve_col(lower, col_ch0_i, kind="ch0_i")
        c0q = _resolve_col(lower, col_ch0_q, kind="ch0_q")
        c1i = _resolve_col(lower, col_ch1_i, kind="ch1_i")
        c1q = _resolve_col(lower, col_ch1_q, kind="ch1_q")
        usecols = [c0i, c0q, c1i, c1q]
        read_kwargs = {"usecols": usecols}
        if max_rows and max_rows > 0:
            read_kwargs["nrows"] = int(max_rows)
        df = pd.read_csv(csv_path, **read_kwargs)
        if use_ch == 1:
            i_raw, q_raw = df[c1i].to_numpy(), df[c1q].to_numpy()
            print(f"[COLS] 2ant ch1 I={c1i!r} Q={c1q!r} N={len(i_raw)}")
        else:
            i_raw, q_raw = df[c0i].to_numpy(), df[c0q].to_numpy()
            print(f"[COLS] 2ant ch0 I={c0i!r} Q={c0q!r} N={len(i_raw)}")
    else:
        raise ValueError(f"unsupported mode={mode!r}")

    divisor = float(signed_adc_scale(adc_bit_width))
    real_data = i_raw.astype(float) / divisor
    image_data = q_raw.astype(float) / divisor

    if decimate_factor > 1:
        real_data, image_data = decimate_iq(real_data, image_data, decimate_factor)
        print(f"decimate {decimate_factor}:1 -> {len(real_data)} samples")

    data_ll = len(real_data)
    if data_ll == 0:
        raise ValueError("empty I/Q data")
    ll = 2 ** int(np.log2(data_ll))
    return real_data[0:ll], image_data[0:ll]


def psd_plot_rx_cal(
    real_data,
    image_data,
    bw,
    ch_freq,
    freqcw,
    fname,
    adc_bit_width: int = ADC_BIT_WIDTH,
    sample_freq_mhz: float = 0,
    decimate_factor: int = DECIMATE_FACTOR,
):
    """
    myplot.psd_plot_rx_cal with explicit bw/ch_freq/freqcw.
    sample_freq_mhz: nominal Welch Fs before decimate; 0 → myplot bw mapping.
    Effective Welch Fs = sample_freq_mhz / decimate_factor.
    Returns [ori_tone_pwr, mir_tone_pwr, sig_pwr].
    """
    ch_freq = int(ch_freq)
    freqcw = int(freqcw)
    bw = int(bw)

    sample_freq_mhz = effective_sample_freq_mhz(bw, sample_freq_mhz, decimate_factor)
    all_freq = sample_freq_mhz

    diff_freq = abs(freqcw - ch_freq)
    if freqcw > ch_freq:
        ori_signal_right = 1
    else:
        ori_signal_right = 0

    print(f"Welch Fs={sample_freq_mhz} MHz, all_freq={all_freq} MHz, diff_freq={diff_freq} MHz")

    pp = PdfPages(fname + ".pdf")
    cv_data = [real_data[i] + image_data[i] * 1j for i in range(0, len(real_data))]
    code_scale = signed_adc_scale(adc_bit_width)
    full_scale = float(signed_adc_full_scale(adc_bit_width))
    squared_read = [int(num * code_scale) ** 2 for num in real_data]
    squared_imag = [int(num * code_scale) ** 2 for num in image_data]
    mean_squared_real = sum(squared_read) / len(squared_read)
    mean_squared_imag = sum(squared_imag) / len(squared_imag)
    sig_pwr = 20 * math.log10(math.sqrt(mean_squared_real + mean_squared_imag) / full_scale)
    print(
        f"mean_squared_real is {mean_squared_real}, mean_squared_imag is {mean_squared_imag}, "
        f"sig_pwr is {sig_pwr}"
    )

    NFFT = sample_freq_mhz / 0.1
    overlap = NFFT / 2
    win = np.hanning(NFFT)

    F, P = welch(
        cv_data,
        sample_freq_mhz,
        win,
        noverlap=overlap,
        nfft=NFFT,
        return_onesided=False,
        detrend=False,
    )
    pwr = 10 * np.log10(np.abs(np.fft.fftshift(P)))
    pwr_len = len(pwr)
    print(
        f"================================diff_freq:{diff_freq} ,all_freq:{all_freq} "
        f",pwr_len:{pwr_len}====================================="
    )
    if ori_signal_right == 1:
        ori_signal_pos = int((pwr_len / 2) + ((diff_freq / all_freq) * pwr_len))
        mir_signal_pos = int((pwr_len / 2) - ((diff_freq / all_freq) * pwr_len))
    else:
        ori_signal_pos = int((pwr_len / 2) - ((diff_freq / all_freq) * pwr_len))
        mir_signal_pos = int((pwr_len / 2) + ((diff_freq / all_freq) * pwr_len))

    if mir_signal_pos >= pwr_len:
        mir_signal_pos = pwr_len - 1
    if ori_signal_pos >= pwr_len:
        ori_signal_pos = pwr_len - 1
    print(
        f"bw: {bw}, ch_freq: {ch_freq}, freqcw: {freqcw}, pwr_len: {pwr_len}, "
        f"ori_signal_pos:{ori_signal_pos}, mir_signal_pos:{mir_signal_pos}"
    )
    frequency = np.fft.fftshift(F)
    frequency_ori = frequency[ori_signal_pos]
    frequency_mir = frequency[mir_signal_pos]
    frequency_0 = frequency[int(pwr_len / 2)]
    pwr_0 = pwr[0]
    print(
        f"============================frequency_ori:{frequency_ori},frequency_mir:{frequency_mir} "
        f",frequency_0:{frequency_0}, pwr_0:{pwr_0}:len_freq:{len(F)}"
        f"======================================"
    )

    mir_signal_pos_2 = mir_signal_pos + 1
    mir_signal_pos_3 = mir_signal_pos - 1
    ori_signal_pos_2 = ori_signal_pos + 1
    ori_signal_pos_3 = ori_signal_pos - 1
    mir_signal_pos_4 = mir_signal_pos + 2
    mir_signal_pos_5 = mir_signal_pos - 2
    ori_signal_pos_4 = ori_signal_pos + 2
    ori_signal_pos_5 = ori_signal_pos - 2

    ori_tone_pwr_1 = pwr[ori_signal_pos]
    mir_tone_pwr_1 = pwr[mir_signal_pos]
    ori_tone_pwr_2 = pwr[ori_signal_pos_2]
    mir_tone_pwr_2 = pwr[mir_signal_pos_2]
    ori_tone_pwr_3 = pwr[ori_signal_pos_3]
    mir_tone_pwr_3 = pwr[mir_signal_pos_3]
    ori_tone_pwr_4 = pwr[ori_signal_pos_4]
    mir_tone_pwr_4 = pwr[mir_signal_pos_4]
    ori_tone_pwr_5 = pwr[ori_signal_pos_5]
    mir_tone_pwr_5 = pwr[mir_signal_pos_5]

    ori_tone_pwr = max(
        ori_tone_pwr_1, ori_tone_pwr_2, ori_tone_pwr_3, ori_tone_pwr_4, ori_tone_pwr_5
    )
    mir_tone_pwr = max(
        mir_tone_pwr_1, mir_tone_pwr_2, mir_tone_pwr_3, mir_tone_pwr_4, mir_tone_pwr_5
    )
    iq_pwr_diff = ori_tone_pwr - mir_tone_pwr

    with plt.ioff():
        x2 = plt.figure()
        freq_axis = np.fft.fftshift(F)
        psd_db = 10 * np.log10(np.abs(np.fft.fftshift(P)))
        plt.plot(freq_axis, psd_db, "b-")
        plt.axvline(
            frequency_ori,
            color="C2",
            linestyle="--",
            linewidth=1,
            label=f"main {frequency_ori:.2f}MHz ({ori_tone_pwr:.2f}dB)",
        )
        plt.axvline(
            frequency_mir,
            color="C3",
            linestyle="--",
            linewidth=1,
            label=f"mirror {frequency_mir:.2f}MHz ({mir_tone_pwr:.2f}dB)",
        )
        plt.title(
            f"{fname}\nFs={sample_freq_mhz}MHz bw={bw} tone offset={diff_freq}MHz\n"
            f"main pwr={ori_tone_pwr:.2f} dB  mirror pwr={mir_tone_pwr:.2f} dB  "
            f"Δ(main−mirror)={iq_pwr_diff:.2f} dB",
            fontsize=10,
        )
        plt.xlabel("Freq(MHz)")
        plt.ylabel("power density (dB)")
        plt.legend(loc="best", fontsize=8)
        plt.grid()
        plt.figtext(
            0.99,
            0.02,
            f"IQ suppression (main−mirror) = {iq_pwr_diff:.2f} dB",
            ha="right",
            va="bottom",
            fontsize=9,
            bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "gray", "pad": 4},
        )
    pp.savefig(x2)
    plt.close()
    pp.close()

    return [ori_tone_pwr, mir_tone_pwr, sig_pwr]


def run_from_csv(
    csv_file: Union[str, Path],
    bw: int = BW_MHZ,
    ch_freq: int = CH_FREQ_MHZ,
    freqcw: int = FREQCW_MHZ,
    *,
    fname: str = "",
    max_rows: int = MAX_ROWS,
    mode: str = IQ_MODE,
    use_ch: int = USE_CH,
    adc_bit_width: int = ADC_BIT_WIDTH,
    sample_freq_mhz: float = SAMPLE_FREQ_MHZ,
    decimate_factor: int = DECIMATE_FACTOR,
    col_i: str = COL_I,
    col_q: str = COL_Q,
    col_ch0_i: str = COL_CH0_I,
    col_ch0_q: str = COL_CH0_Q,
    col_ch1_i: str = COL_CH1_I,
    col_ch1_q: str = COL_CH1_Q,
) -> List[float]:
    """Load signed CSV → normalize → decimate → psd_plot_rx_cal."""
    csv_path = Path(csv_file)
    if not fname:
        fname = str(csv_path.with_suffix(""))

    real_data, image_data = load_real_image_from_csv(
        csv_path,
        max_rows=max_rows,
        mode=mode,
        use_ch=use_ch,
        adc_bit_width=adc_bit_width,
        decimate_factor=decimate_factor,
        col_i=col_i,
        col_q=col_q,
        col_ch0_i=col_ch0_i,
        col_ch0_q=col_ch0_q,
        col_ch1_i=col_ch1_i,
        col_ch1_q=col_ch1_q,
    )
    return psd_plot_rx_cal(
        real_data,
        image_data,
        bw,
        ch_freq,
        freqcw,
        fname,
        adc_bit_width=adc_bit_width,
        sample_freq_mhz=sample_freq_mhz,
        decimate_factor=decimate_factor,
    )


def is_result_csv(path: Path) -> bool:
    """Skip previously generated summary CSVs when scanning a directory."""
    name = path.name.lower()
    return name.endswith("_iq_cal_result.csv")


def collect_csv_inputs(
    input_path: Union[str, Path],
    *,
    recursive: bool = False,
) -> List[Path]:
    """
    Resolve input path to a list of I/Q CSV files.

    - File: that single CSV
    - Directory: all *.csv under it (non-recursive by default; --recursive for rglob)
      Skips *_iq_cal_result.csv products.
    """
    path = Path(input_path)
    if path.is_file():
        return [path]
    if path.is_dir():
        pattern = "**/*.csv" if recursive else "*.csv"
        csvs = sorted(p for p in path.glob(pattern) if p.is_file() and not is_result_csv(p))
        return csvs
    return []


def process_one_csv(
    csv_path: Path,
    args: argparse.Namespace,
    *,
    fname: str,
    decimate: int,
) -> dict:
    """Run IQ-cal PSD for one CSV; write PDF + per-file result CSV; return summary row."""
    result = run_from_csv(
        csv_path,
        args.bw,
        args.chan,
        args.freqcw,
        fname=fname,
        max_rows=args.max_rows,
        mode=args.mode,
        use_ch=args.ch,
        adc_bit_width=args.bit_width,
        sample_freq_mhz=args.sample_freq_mhz,
        decimate_factor=decimate,
        col_i=args.col_i,
        col_q=args.col_q,
        col_ch0_i=args.col_ch0_i,
        col_ch0_q=args.col_ch0_q,
        col_ch1_i=args.col_ch1_i,
        col_ch1_q=args.col_ch1_q,
    )
    ori_tone_pwr, mir_tone_pwr, sig_pwr = result
    fs_used = effective_sample_freq_mhz(args.bw, args.sample_freq_mhz, decimate)
    print(
        f"[RESULT] {csv_path.name}  Fs={fs_used}MHz decimate={decimate} "
        f"bit_width={args.bit_width} "
        f"ori_tone_pwr={ori_tone_pwr:.6f} mir_tone_pwr={mir_tone_pwr:.6f} "
        f"diff={ori_tone_pwr - mir_tone_pwr:.6f} sig_pwr={sig_pwr:.6f}"
    )
    print(f"[PDF] {fname}.pdf")

    row = {
        "file": csv_path.name,
        "path": str(csv_path),
        "bw_mhz": args.bw,
        "ch_freq_mhz": args.chan,
        "freqcw_mhz": args.freqcw,
        "adc_bit_width": args.bit_width,
        "sample_freq_mhz": fs_used,
        "decimate_factor": decimate,
        "nominal_sample_freq_mhz": resolve_sample_freq_mhz(args.bw, args.sample_freq_mhz),
        "ori_tone_pwr_db": ori_tone_pwr,
        "mir_tone_pwr_db": mir_tone_pwr,
        "iq_suppression_db": ori_tone_pwr - mir_tone_pwr,
        "sig_pwr_db": sig_pwr,
        "pdf": fname + ".pdf",
    }
    out_csv = csv_path.with_name(csv_path.stem + "_iq_cal_result.csv")
    pd.DataFrame([row]).to_csv(out_csv, index=False)
    print(f"[CSV] {out_csv}")
    return row


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="myplot.psd_plot_rx_cal with config + CSV/dir input"
    )
    p.add_argument(
        "input",
        nargs="?",
        default=INPUT_CSV,
        help="I/Q CSV file, or a directory of CSV dumps",
    )
    p.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="When input is a directory, also search CSV in subfolders",
    )
    p.add_argument("--bw", type=int, default=BW_MHZ, help="phymd bandwidth MHz")
    p.add_argument("--chan", type=int, default=CH_FREQ_MHZ, help="channel center MHz")
    p.add_argument("--freqcw", type=int, default=FREQCW_MHZ, help="CW tone MHz")
    p.add_argument(
        "-o",
        "--output-pdf",
        default=OUTPUT_PDF,
        help="Single-file: PDF stem (no .pdf). "
        "Directory mode: optional output directory for PDFs/results",
    )
    p.add_argument("--max-rows", type=int, default=MAX_ROWS)
    p.add_argument("--mode", choices=("auto", "single", "2ant"), default=IQ_MODE)
    p.add_argument("--ch", type=int, default=USE_CH, choices=(0, 1))
    p.add_argument(
        "--col-i",
        default=COL_I,
        help=f"I column name for single-stream CSV (default: {COL_I})",
    )
    p.add_argument(
        "--col-q",
        default=COL_Q,
        help=f"Q column name for single-stream CSV (default: {COL_Q})",
    )
    p.add_argument("--col-ch0-i", default=COL_CH0_I, help="2ant ch0 I column")
    p.add_argument("--col-ch0-q", default=COL_CH0_Q, help="2ant ch0 Q column")
    p.add_argument("--col-ch1-i", default=COL_CH1_I, help="2ant ch1 I column")
    p.add_argument("--col-ch1-q", default=COL_CH1_Q, help="2ant ch1 Q column")
    p.add_argument(
        "--sample-freq-mhz",
        type=float,
        default=SAMPLE_FREQ_MHZ,
        help="Nominal Welch Fs MHz before decimate (0=myplot bw map)",
    )
    p.add_argument(
        "--decimate",
        type=int,
        default=DECIMATE_FACTOR,
        help="Decimation factor (2 = 2抽1 [::2]); effective Fs /= decimate",
    )
    p.add_argument("--no-decimate", action="store_true", help="Same as --decimate 1")
    p.add_argument(
        "--bit-width",
        type=int,
        default=ADC_BIT_WIDTH,
        help="signed ADC bit width (default 12: norm /2^11, sig_pwr /2^12)",
    )
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.input)
    csv_list = collect_csv_inputs(input_path, recursive=args.recursive)
    if not csv_list:
        if not input_path.exists():
            print(f"[ERROR] path not found: {input_path}")
        else:
            print(f"[ERROR] no CSV found under: {input_path}")
        return 1

    decimate = 1 if args.no_decimate else args.decimate
    is_dir = input_path.is_dir()
    out_dir: Optional[Path] = None
    if is_dir and args.output_pdf:
        out_dir = Path(args.output_pdf)
        out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] {len(csv_list)} CSV(s) from {input_path}")
    rows: List[dict] = []
    failed = 0
    for csv_path in csv_list:
        try:
            if out_dir is not None:
                fname = str(out_dir / csv_path.stem)
            elif (not is_dir) and args.output_pdf:
                fname = args.output_pdf
            else:
                fname = str(csv_path.with_suffix(""))
            row = process_one_csv(csv_path, args, fname=fname, decimate=decimate)
            rows.append(row)
        except Exception as exc:
            failed += 1
            print(f"[ERROR] {csv_path.name}: {exc}")

    if is_dir and rows:
        batch_csv = (out_dir if out_dir is not None else input_path) / "iq_cal_batch_summary.csv"
        pd.DataFrame(rows).to_csv(batch_csv, index=False)
        print(f"[BATCH] {batch_csv}  ({len(rows)} ok, {failed} failed)")

    return 1 if failed and not rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
