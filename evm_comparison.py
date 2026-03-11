import pandas as pd
import matplotlib.pyplot as plt
import os
import re

def compare_evm():
    # 文件路径
    mag_off_file = r"D:\users\gxu\chip_test\chip_tx\eagletest\py_script_rls3p0_chip\Log\wifi_tx\chip3_2G_he_40m_nss2_ldpc\enb_amp0\risc_wifitx_40m_hesu_nss2_stbc0_fec_coding1_channel11_enb_amp0_2026-0311-112640.csv"
    mag_on_file = r"D:\users\gxu\chip_test\chip_tx\eagletest\py_script_rls3p0_chip\Log\wifi_tx\chip3_2G_he_40m_nss2_ldpc\enb_amp1\risc_wifitx_40m_hesu_nss2_stbc0_fec_coding1_channel11_enb_amp1_2026-0311-103340.csv"

    # 读取数据
    try:
        df_off = pd.read_csv(mag_off_file)
        df_on = pd.read_csv(mag_on_file)
        print("数据读取成功")
    except Exception as e:
        print(f"读取文件失败: {e}")
        return

    # 检查是否包含必要的列
    required_cols = ['tx_power_set(dBm)', 'evm_nss0', 'evm_nss1']
    for col in required_cols:
        if col not in df_off.columns or col not in df_on.columns:
            print(f"文件缺少必要的列: {col}")
            return

    # 绘制图表
    plt.figure(dpi=100, figsize=(10, 6))

    # 处理 mag tracking off 的数据
    df_off_filtered = df_off.dropna(subset=['tx_power_set(dBm)', 'evm_nss0', 'evm_nss1'])

    # 计算每个功率级别的平均 EVM（NSS0 和 NSS1 的平均值）
    df_off_filtered['avg_evm'] = (df_off_filtered['evm_nss0'] + df_off_filtered['evm_nss1']) / 2
    df_off_pivot = df_off_filtered.pivot_table(index=['tx_power_set(dBm)'], values=['avg_evm'])
    plt.plot(df_off_pivot.index, df_off_pivot['avg_evm'], 'o-', color='#FF0000', label='Mag Tracking OFF', linewidth=2)

    # 处理 mag tracking on 的数据
    df_on_filtered = df_on.dropna(subset=['tx_power_set(dBm)', 'evm_nss0', 'evm_nss1'])

    # 计算每个功率级别的平均 EVM（NSS0 和 NSS1 的平均值）
    df_on_filtered['avg_evm'] = (df_on_filtered['evm_nss0'] + df_on_filtered['evm_nss1']) / 2
    df_on_pivot = df_on_filtered.pivot_table(index=['tx_power_set(dBm)'], values=['avg_evm'])
    plt.plot(df_on_pivot.index, df_on_pivot['avg_evm'], 's-', color='#0000FF', label='Mag Tracking ON', linewidth=2)

    # 图表设置
    plt.ylim([-45, -18])
    plt.xlim([-12, 20])
    plt.xlabel('tx_power_set (dBm)')
    plt.ylabel('EVM (dB)')
    plt.title('EVM Comparison: Mag Tracking OFF vs ON')
    plt.grid(True, alpha=0.3)
    plt.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=10)
    plt.tight_layout()

    # 保存图表
    output_dir = r"D:\users\gxu\scripts"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_file = os.path.join(output_dir, 'evm_comparison.png')
    plt.savefig(output_file, dpi=100, bbox_inches='tight')
    print(f"图表已保存到: {output_file}")

    # 显示图表
    plt.show()

    # 输出简单的统计信息
    print("\n--- Mag Tracking OFF 统计 ---")
    print(f"Power range: {df_off['tx_power_set(dBm)'].min()} to {df_off['tx_power_set(dBm)'].max()} dBm")
    print(f"EVM range: {df_off['evm'].min():.2f} to {df_off['evm'].max():.2f} dB")

    print("\n--- Mag Tracking ON 统计 ---")
    print(f"Power range: {df_on['tx_power_set(dBm)'].min()} to {df_on['tx_power_set(dBm)'].max()} dBm")
    print(f"EVM range: {df_on['evm'].min():.2f} to {df_on['evm'].max():.2f} dB")

if __name__ == "__main__":
    compare_evm()
