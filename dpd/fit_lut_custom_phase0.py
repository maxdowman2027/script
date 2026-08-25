#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
260825 3lut fit: amp-poly on master; preserve phase trend; slaves passthrough.

Phase lesson
------------
Through-zero *phase* poly pulls the mid-band down when trained φ sits at ~3–8°
(260825 lut0). Keep repaired original phase (only interpolate excluded bins).
Amp still uses no-constant poly to fix index2 collapse and smooth AM.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lut_phase0_fit import run_multi

SRC = Path(r"D:\test_data\AP\260825_dpd\3lut_multi_frame_training\original_coefficients")
OUT = Path(r"D:\test_data\AP\260825_dpd\3lut_multi_frame_training\fit_coefficients")
MASTER = 0


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    run_multi(
        SRC,
        OUT,
        method="poly",
        deg_amp=4,
        exclude="auto",
        master_lut=MASTER,
        scope="all",
        slave_method="passthrough",
    )
    print(f"[OK] amp-poly + phase-preserve master, slaves passthrough -> {OUT}")


if __name__ == "__main__":
    main()
