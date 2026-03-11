import csv
import sys

def main():
    file_path = r"D:\users\gxu\chip_test\chip_tx\eagletest\py_script_rls3p0_chip\Log\wifi_tx\chip3_2G_he_40m_nss2_ldpc\enb_amp0\risc_wifitx_40m_hesu_nss2_stbc0_fec_coding1_channel11_enb_amp0_2026-0311-112640.csv"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            print("CSV文件列名:")
            for i, col in enumerate(header):
                print(f"{i}: {col}")

        print(f"\n总列数: {len(header)}")

    except Exception as e:
        print(f"读取文件时出错: {e}")
        return

    return

if __name__ == "__main__":
    main()
