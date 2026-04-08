
with open(r'D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx\20260407\vht_ht_2\evm_comparison_results\evm_comparison_report.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查旧版本文件路径
old_path = r'D:/chip_test/dev/chip_tx/eagletest/py_script_fpga_tx_wifi7/Log/wifi_tx/20260407/vht_ht_old/merged_tx_result.xlsx'
if old_path in content:
    print(f"旧版本文件路径正确: {old_path}")
else:
    print(f"旧版本文件路径不正确")

# 检查新版本文件路径
new_path = r'D:/chip_test/dev/xian_test/Xian-Esp-Test-Scripts/py_script_fpga_tx_wifi7/Log/wifi_tx/20260407/vht_ht_2/merged_tx_result.xlsx'
if new_path in content:
    print(f"新版本文件路径正确: {new_path}")
else:
    print(f"新版本文件路径不正确")
