import os
import csv
import glob

def check_wifi_formats():
    input_dir = "D:/chip_test/dev/xian_test/Xian-Esp-Test-Scripts/py_script_fpga_tx_wifi7/Log/wifi_tx_rls4/no_he"
    csv_files = glob.glob(os.path.join(input_dir, "*.csv"))

    wifi_formats = set()

    for csv_file in csv_files:
        try:
            with open(csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'wifi_format' in row:
                        if row['wifi_format']:
                            wifi_formats.add(row['wifi_format'])
        except Exception as e:
            print(f"Error reading {csv_file}: {e}")

    print("Found wifi_format values:")
    for format in sorted(wifi_formats):
        print(f"  - {format}")

    print(f"\nTotal unique formats: {len(wifi_formats)}")

if __name__ == "__main__":
    check_wifi_formats()