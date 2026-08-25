Sample I/Q CSV for lut_phase0_fit.c / Python smoke tests.

Source: dig_gain1_66 lut_data_map_lut0 (index 2 is an intentional amp-collapse).

Default pipeline (exclude=auto, method=smooth):
  detect outliers -> interpolate -> blended MA (phase>amp) -> amp clamp
  -> master phase-align; keep master index1 amplitude.

Avoid full-table MA as the default on-chip path (hurts DPD / maxerr).
Use --method repair for max preserve, or --method ma/poly/iqpoly offline.
