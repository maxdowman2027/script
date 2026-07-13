#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RX IQ imbalance (image rejection) from dump I/Q CSV.

Logic aligned with Xian ``myplot.psd_plot_rx_cal``:
  - Welch PSD (Fs MHz, NFFT=Fs/0.1)
  - Locate main-tone and mirror-tone bins from bw / chan / freqcw offset
  - IQ suppression [dB] = main_tone_pwr_db - mirror_tone_pwr_db

Input: dump CSV with I/Q columns (sample_i/q or ch0_sample_i/q).
Test params (bw, chan, freqcw) are set in the script config block, not parsed from filenames.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import welch

from plot_psd_2462 import PSD_NFFT_STEP_MHZ, read_iq_data

# =============================================================================
# Config（直接改这里可免命令行；不从文件名解析 phymd/chan/freqcw）
# =============================================================================
INPUT_CSV = r"D:\test_data\rls4\260713_dpd\iladata_adc_tone.csv"
INPUT_DIR = ""  # 非空时批量处理目录（优先于 INPUT_CSV 时需命令行传参）
INPUT_GLOB = "*.csv"
OUTPUT_SUMMARY = ""  # empty -> beside input / input_dir

# RX 测试参数（对应 myplot.psd_plot_rx_cal 的 bw / ch_freq / freqcw）
BW_MHZ = 20  # phymd 信道带宽 MHz：20 / 40 / 80 / 160 / 320
CH_FREQ_MHZ = 5180  # 信道中心频率 MHz
FREQCW_MHZ = 5140  # CW 单音频率 MHz

MAX_ROWS = 65536
IQ_MODE = "auto"  # auto | single | 2ant
USE_CH = 0  # 0 or 1 for 2ant
BIT_WIDTH = 11  # ADC bits for sig_pwr; 0 = data already normalized float
ADC_NORM_SHIFT = 11  # myplot uses 2**11 for sig_pwr when data is float in [-1,1]
SIG_PWR_FULL_SCALE = 4096  # myplot divisor
TONE_BIN_SPAN = 2  # peak search ±N bins around estimated tone index
SAVE_PDF = True


@dataclass
class RxTestParams:
    bw_mhz: int
    ch_freq_mhz: int
    freqcw_mhz: int

    @property
    def diff_freq_mhz(self) -> int:
        return abs(self.freqcw_mhz - self.ch_freq_mhz)

    @property
    def ori_signal_right(self) -> bool:
        return self.freqcw_mhz > self.ch_freq_mhz


@dataclass
class IqImbalanceResult:
    file: str
    bw_mhz: int
    ch_freq_mhz: int
    freqcw_mhz: int
    sample_freq_mhz: float
    all_freq_mhz: float
    diff_freq_mhz: int
    ori_tone_pwr_db: float
    mir_tone_pwr_db: float
    iq_suppression_db: float
    sig_pwr_db: float
    frequency_ori_mhz: float
    frequency_mir_mhz: float
    ori_signal_pos: int
    mir_signal_pos: int

    def as_dict(self) -> Dict[str, Union[str, int, float]]:
        return {
            "file": self.file,
            "bw_mhz": self.bw_mhz,
            "ch_freq_mhz": self.ch_freq_mhz,
            "freqcw_mhz": self.freqcw_mhz,
            "sample_freq_mhz": self.sample_freq_mhz,
            "all_freq_mhz": self.all_freq_mhz,
            "diff_freq_mhz": self.diff_freq_mhz,
            "ori_tone_pwr_db": round(self.ori_tone_pwr_db, 4),
            "mir_tone_pwr_db": round(self.mir_tone_pwr_db, 4),
            "iq_suppression_db": round(self.iq_suppression_db, 4),
            "sig_pwr_db": round(self.sig_pwr_db, 4),
            "frequency_ori_mhz": round(self.frequency_ori_mhz, 4),
            "frequency_mir_mhz": round(self.frequency_mir_mhz, 4),
            "ori_signal_pos": self.ori_signal_pos,
            "mir_signal_pos": self.mir_signal_pos,
        }


def bw_to_sample_rates(bw_mhz: int) -> Tuple[float, float]:
    """Map channel bandwidth (MHz) to Welch Fs and full span (myplot.psd_plot_rx_cal)."""
    if bw_mhz == 20:
        return 40.0, 40.0
    if bw_mhz == 40:
        return 80.0, 80.0
    if bw_mhz == 80:
        return 160.0, 160.0
    return 320.0, 320.0


def config_test_params(
    bw_mhz: int = BW_MHZ,
    ch_freq_mhz: int = CH_FREQ_MHZ,
    freqcw_mhz: int = FREQCW_MHZ,
) -> RxTestParams:
    """Build test params from script config or explicit overrides."""
    return RxTestParams(
        bw_mhz=int(bw_mhz),
        ch_freq_mhz=int(ch_freq_mhz),
        freqcw_mhz=int(freqcw_mhz),
    )


def welch_psd_db(
    i_data: np.ndarray,
    q_data: np.ndarray,
    sample_freq_mhz: float,
    *,
    nfft_step_mhz: float = PSD_NFFT_STEP_MHZ,
) -> Tuple[np.ndarray, np.ndarray]:
    """Welch PSD; return shifted freq [MHz] and power [dB] = 10*log10(|P|)."""
    cv_data = i_data.astype(np.complex128) + 1j * q_data.astype(np.complex128)
    n = len(cv_data)
    nfft = int(sample_freq_mhz / nfft_step_mhz)
    nfft = min(max(nfft, 8), n)
    if nfft < 8:
        raise ValueError(f"too few samples for Welch: n={n}")

    overlap = nfft // 2
    win = np.hanning(nfft)
    freq_mhz, pxx = welch(
        cv_data,
        sample_freq_mhz,
        win,
        noverlap=overlap,
        nfft=nfft,
        return_onesided=False,
        detrend=False,
    )
    freq_mhz = np.fft.fftshift(freq_mhz)
    pwr_db = 10 * np.log10(np.maximum(np.abs(np.fft.fftshift(pxx)), 1e-30))
    return freq_mhz, pwr_db


def compute_sig_pwr_db(
    i_data: np.ndarray,
    q_data: np.ndarray,
    *,
    bit_width: int = BIT_WIDTH,
    adc_norm_shift: int = ADC_NORM_SHIFT,
    full_scale: float = SIG_PWR_FULL_SCALE,
) -> float:
    """Time-domain signal power [dB], same convention as myplot.psd_plot_rx_cal."""
    if bit_width > 0:
        i_scaled = i_data.astype(float)
        q_scaled = q_data.astype(float)
        mean_sq = float(np.mean(i_scaled ** 2 + q_scaled ** 2))
        denom = float(2 ** (bit_width - 1))
    else:
        i_codes = np.trunc(i_data.astype(float) * (2 ** adc_norm_shift)).astype(np.int64)
        q_codes = np.trunc(q_data.astype(float) * (2 ** adc_norm_shift)).astype(np.int64)
        mean_sq = float(np.mean(i_codes ** 2 + q_codes ** 2))
        denom = full_scale
    if mean_sq <= 0:
        return float("nan")
    return 20.0 * math.log10(math.sqrt(mean_sq) / denom)


def estimate_tone_indices(
    pwr_len: int,
    diff_freq_mhz: float,
    all_freq_mhz: float,
    ori_signal_right: bool,
) -> Tuple[int, int]:
    """Main-tone and mirror-tone bin indices (myplot.psd_plot_rx_cal)."""
    half = pwr_len / 2.0
    offset = (diff_freq_mhz / all_freq_mhz) * pwr_len
    if ori_signal_right:
        ori_pos = int(half + offset)
        mir_pos = int(half - offset)
    else:
        ori_pos = int(half - offset)
        mir_pos = int(half + offset)
    ori_pos = min(max(ori_pos, 0), pwr_len - 1)
    mir_pos = min(max(mir_pos, 0), pwr_len - 1)
    return ori_pos, mir_pos


def peak_pwr_near(pwr_db: np.ndarray, center: int, span: int = TONE_BIN_SPAN) -> float:
    """Max PSD [dB] in [center-span, center+span]."""
    lo = max(0, center - span)
    hi = min(len(pwr_db), center + span + 1)
    return float(np.max(pwr_db[lo:hi]))


def psd_plot_rx_cal(
    i_data: np.ndarray,
    q_data: np.ndarray,
    params: RxTestParams,
    *,
    tone_bin_span: int = TONE_BIN_SPAN,
    bit_width: int = BIT_WIDTH,
) -> Tuple[IqImbalanceResult, np.ndarray, np.ndarray]:
    """
    Core RX IQ calibration (mirror rejection) from I/Q arrays.

    Returns result struct and (freq_mhz, pwr_db) for optional plotting.
    """
    sample_freq_mhz, all_freq_mhz = bw_to_sample_rates(params.bw_mhz)
    freq_mhz, pwr_db = welch_psd_db(i_data, q_data, sample_freq_mhz)
    pwr_len = len(pwr_db)

    ori_pos, mir_pos = estimate_tone_indices(
        pwr_len,
        float(params.diff_freq_mhz),
        all_freq_mhz,
        params.ori_signal_right,
    )

    ori_tone_pwr = peak_pwr_near(pwr_db, ori_pos, tone_bin_span)
    mir_tone_pwr = peak_pwr_near(pwr_db, mir_pos, tone_bin_span)
    sig_pwr = compute_sig_pwr_db(i_data, q_data, bit_width=bit_width)

    result = IqImbalanceResult(
        file="",
        bw_mhz=params.bw_mhz,
        ch_freq_mhz=params.ch_freq_mhz,
        freqcw_mhz=params.freqcw_mhz,
        sample_freq_mhz=sample_freq_mhz,
        all_freq_mhz=all_freq_mhz,
        diff_freq_mhz=params.diff_freq_mhz,
        ori_tone_pwr_db=ori_tone_pwr,
        mir_tone_pwr_db=mir_tone_pwr,
        iq_suppression_db=ori_tone_pwr - mir_tone_pwr,
        sig_pwr_db=sig_pwr,
        frequency_ori_mhz=float(freq_mhz[ori_pos]),
        frequency_mir_mhz=float(freq_mhz[mir_pos]),
        ori_signal_pos=ori_pos,
        mir_signal_pos=mir_pos,
    )
    return result, freq_mhz, pwr_db


def load_iq_from_csv(
    csv_path: Path,
    *,
    max_rows: int = MAX_ROWS,
    mode: str = IQ_MODE,
    use_ch: int = USE_CH,
) -> Tuple[np.ndarray, np.ndarray]:
    iq = read_iq_data(str(csv_path), max_rows=max_rows, mode=mode)
    if iq is None:
        raise ValueError(f"failed to read IQ from {csv_path}")
    if iq.mode == "2ant":
        if use_ch == 1:
            return iq.ch1_i.astype(float), iq.ch1_q.astype(float)
        return iq.ch0_i.astype(float), iq.ch0_q.astype(float)
    return iq.ch0_i.astype(float), iq.ch0_q.astype(float)


def save_psd_pdf(
    out_pdf: Path,
    title: str,
    freq_mhz: np.ndarray,
    pwr_db: np.ndarray,
    result: IqImbalanceResult,
) -> None:
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(freq_mhz, pwr_db, "b-", linewidth=0.8, label="PSD")
    ax.axvline(result.frequency_ori_mhz, color="C2", linestyle="--", linewidth=1, label="main tone")
    ax.axvline(result.frequency_mir_mhz, color="C3", linestyle="--", linewidth=1, label="mirror tone")
    ax.set_title(
        f"{title}\nIQ supp={result.iq_suppression_db:.2f} dB "
        f"(main={result.ori_tone_pwr_db:.2f}, mir={result.mir_tone_pwr_db:.2f})"
    )
    ax.set_xlabel("Freq (MHz)")
    ax.set_ylabel("Power density (dB)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_pdf, dpi=150)
    plt.close(fig)


def analyze_one_file(
    csv_path: Path,
    params: RxTestParams,
    *,
    max_rows: int = MAX_ROWS,
    mode: str = IQ_MODE,
    use_ch: int = USE_CH,
    bit_width: int = BIT_WIDTH,
    save_pdf: bool = SAVE_PDF,
) -> IqImbalanceResult:
    i_data, q_data = load_iq_from_csv(
        csv_path, max_rows=max_rows, mode=mode, use_ch=use_ch
    )
    result, freq_mhz, pwr_db = psd_plot_rx_cal(
        i_data, q_data, params, bit_width=bit_width
    )
    result.file = csv_path.name

    print(
        f"[{csv_path.name}] bw={params.bw_mhz} ch={params.ch_freq_mhz} "
        f"cw={params.freqcw_mhz} diff={params.diff_freq_mhz}MHz "
        f"main={result.ori_tone_pwr_db:.2f}dB mir={result.mir_tone_pwr_db:.2f}dB "
        f"IQ_supp={result.iq_suppression_db:.2f}dB sig_pwr={result.sig_pwr_db:.2f}dB"
    )

    if save_pdf:
        pdf_path = csv_path.with_name(csv_path.stem + "_iq_cal.pdf")
        save_psd_pdf(pdf_path, csv_path.stem, freq_mhz, pwr_db, result)
        print(f"  PSD PDF -> {pdf_path}")

    return result


def collect_csv_files(input_path: Path, pattern: str) -> List[Path]:
    if input_path.is_file():
        return [input_path]
    return sorted(input_path.glob(pattern))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="RX IQ imbalance from dump CSV (psd_plot_rx_cal logic)"
    )
    p.add_argument(
        "input",
        nargs="?",
        default=INPUT_CSV if INPUT_CSV else INPUT_DIR,
        help="IQ dump CSV file or directory",
    )
    p.add_argument("-g", "--glob", default=INPUT_GLOB, help="Glob when input is directory")
    p.add_argument(
        "--bw",
        type=int,
        default=BW_MHZ,
        help=f"Channel bandwidth MHz (default config: {BW_MHZ})",
    )
    p.add_argument(
        "--chan",
        type=int,
        default=CH_FREQ_MHZ,
        help=f"Channel center frequency MHz (default config: {CH_FREQ_MHZ})",
    )
    p.add_argument(
        "--freqcw",
        type=int,
        default=FREQCW_MHZ,
        help=f"CW tone frequency MHz (default config: {FREQCW_MHZ})",
    )
    p.add_argument("-o", "--output", default=OUTPUT_SUMMARY, help="Summary CSV path")
    p.add_argument("--max-rows", type=int, default=MAX_ROWS, help="Max rows to read (0=all)")
    p.add_argument("--mode", choices=("auto", "single", "2ant"), default=IQ_MODE)
    p.add_argument("--ch", type=int, default=USE_CH, choices=(0, 1), help="2ant channel index")
    p.add_argument("--bit-width", type=int, default=BIT_WIDTH, help="ADC bit width for sig_pwr")
    p.add_argument("--no-pdf", action="store_true", help="Skip per-file PSD PDF")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] input not found: {input_path}")
        return 1

    params = config_test_params(args.bw, args.chan, args.freqcw)

    files = collect_csv_files(input_path, args.glob)
    if not files:
        print(f"[ERROR] no files matched {args.glob!r} under {input_path}")
        return 1

    max_rows = args.max_rows if args.max_rows > 0 else 0
    rows: List[Dict[str, Union[str, int, float]]] = []
    failed = 0

    for csv_path in files:
        try:
            result = analyze_one_file(
                csv_path,
                params,
                max_rows=max_rows,
                mode=args.mode,
                use_ch=args.ch,
                bit_width=args.bit_width,
                save_pdf=not args.no_pdf,
            )
            rows.append(result.as_dict())
        except Exception as exc:
            failed += 1
            print(f"[ERROR] {csv_path.name}: {exc}")

    if rows:
        summary = pd.DataFrame(rows)
        if args.output:
            out_csv = Path(args.output)
        elif input_path.is_file():
            out_csv = input_path.with_name(input_path.stem + "_iq_imbalance_summary.csv")
        else:
            out_csv = input_path / "iq_imbalance_summary.csv"
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        summary.to_csv(out_csv, index=False)
        print(f"[INFO] summary -> {out_csv} ({len(rows)} ok, {failed} failed)")
        print(summary.to_string(index=False))

    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
