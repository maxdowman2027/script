import pandas as pd
import os
import glob

csv_files = glob.glob(r'D:/chip_test/dev/xian_test/Xian-Esp-Test-Scripts/py_script_fpga_tx_wifi7/Log/wifi_tx_rls4/regression_v1.0/risc_wifitx_*.csv')
has_spectrum_margin_nss1 = False

for csv_file in csv_files:
    try:
        df = pd.read_csv(csv_file, nrows=1)
        if 'spectrumMarginDb_nss1' in df.columns:
            has_spectrum_margin_nss1 = True
            print(f'文件 {os.path.basename(csv_file)} 包含 spectrumMarginDb_nss1 列')
            break
    except Exception as e:
        continue

if not has_spectrum_margin_nss1:
    print('所有CSV文件都不包含 spectrumMarginDb_nss1 列')
