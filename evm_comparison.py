import pandas as pd
import matplotlib.pyplot as plt
import os

def compare_evm_per_mcs(separate_plots=False):
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
    required_cols = ['tx_power_set(dBm)', 'evm_nss0', 'evm_nss1', 'rate']
    for col in required_cols:
        if col not in df_off.columns or col not in df_on.columns:
            print(f"文件缺少必要的列: {col}")
            return

    # 获取所有 MCS
    mcs_off = sorted(df_off['rate'].unique())
    mcs_on = sorted(df_on['rate'].unique())

    # 计算所有唯一的 MCS
    all_mcs = sorted(list(set(mcs_off + mcs_on)))

    print(f"发现的 MCS: {all_mcs}")

    # 设置颜色和标记
    colors = ['#FF0000', '#0000FF', '#00FF00', '#FF00FF', '#00FFFF', '#FF8800', '#8800FF', '#0088FF']
    markers = ['o', 's', '^', 'D', 'p', '*', 'h', '+']

    if separate_plots:
        # 每个 MCS 单独一个图，保存为 PDF 文件
        num_mcs = len(all_mcs)
        from matplotlib.backends.backend_pdf import PdfPages

        output_file = os.path.join(r"D:\users\gxu\e22_tx\260311", 'evm_comparison_per_mcs_separate.pdf')

        with PdfPages(output_file) as pdf:
            for i, mcs in enumerate(all_mcs):
                # 创建更大的图表
                plt.figure(dpi=150, figsize=(12, 8))

                # 处理 mag tracking off 的数据（NSS0 和 NSS1）
                df_off_mcs = df_off[(df_off['rate'] == mcs) & df_off['evm_nss0'].notna() & df_off['evm_nss1'].notna()]
                if not df_off_mcs.empty:
                    df_off_pivot_nss0 = df_off_mcs.pivot_table(index=['tx_power_set(dBm)'], values=['evm_nss0'])
                    df_off_pivot_nss1 = df_off_mcs.pivot_table(index=['tx_power_set(dBm)'], values=['evm_nss1'])

                    plt.plot(df_off_pivot_nss0.index, df_off_pivot_nss0['evm_nss0'],
                            marker=markers[0], linestyle='-', color=colors[0],
                            label=f'Mag Tracking OFF (NSS0)', linewidth=2)
                    plt.plot(df_off_pivot_nss1.index, df_off_pivot_nss1['evm_nss1'],
                            marker=markers[0], linestyle='--', color=colors[1],
                            label=f'Mag Tracking OFF (NSS1)', linewidth=2)

                # 处理 mag tracking on 的数据（NSS0 和 NSS1）
                df_on_mcs = df_on[(df_on['rate'] == mcs) & df_on['evm_nss0'].notna() & df_on['evm_nss1'].notna()]
                if not df_on_mcs.empty:
                    df_on_pivot_nss0 = df_on_mcs.pivot_table(index=['tx_power_set(dBm)'], values=['evm_nss0'])
                    df_on_pivot_nss1 = df_on_mcs.pivot_table(index=['tx_power_set(dBm)'], values=['evm_nss1'])

                    plt.plot(df_on_pivot_nss0.index, df_on_pivot_nss0['evm_nss0'],
                            marker=markers[1], linestyle='-', color=colors[2],
                            label=f'Mag Tracking ON (NSS0)', linewidth=2)
                    plt.plot(df_on_pivot_nss1.index, df_on_pivot_nss1['evm_nss1'],
                            marker=markers[1], linestyle='--', color=colors[3],
                            label=f'Mag Tracking ON (NSS1)', linewidth=2)

                # 图表设置
                plt.ylim([-45, -18])
                plt.xlim([-12, 20])
                plt.xlabel('tx_power_set (dBm)', fontsize=12)
                plt.ylabel('EVM (dB)', fontsize=12)
                plt.title(f'EVM Comparison: MCS {mcs}', fontsize=14, pad=20)
                plt.grid(True, alpha=0.3)
                plt.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=11)
                plt.tight_layout()

                # 添加到 PDF 文件
                pdf.savefig(bbox_inches='tight')
                plt.close()  # 关闭图表，释放内存

        print(f"PDF 文件已保存到: {output_file}")

    else:
        # 所有 MCS 在一个图上
        plt.figure(dpi=100, figsize=(15, 10))

        # 处理 mag tracking off 的数据（每个 MCS 的 NSS0 和 NSS1）
        for i, mcs in enumerate(all_mcs):
            df_off_mcs = df_off[(df_off['rate'] == mcs) & df_off['evm_nss0'].notna() & df_off['evm_nss1'].notna()]
            if not df_off_mcs.empty:
                df_off_pivot_nss0 = df_off_mcs.pivot_table(index=['tx_power_set(dBm)'], values=['evm_nss0'])
                df_off_pivot_nss1 = df_off_mcs.pivot_table(index=['tx_power_set(dBm)'], values=['evm_nss1'])

                plt.plot(df_off_pivot_nss0.index, df_off_pivot_nss0['evm_nss0'],
                        marker=markers[i % len(markers)], linestyle='-', color=colors[i % len(colors)],
                        label=f'Mag Tracking OFF (MCS {mcs}, NSS0)', linewidth=1.5)
                plt.plot(df_off_pivot_nss1.index, df_off_pivot_nss1['evm_nss1'],
                        marker=markers[i % len(markers)], linestyle='--', color=colors[i % len(colors)],
                        label=f'Mag Tracking OFF (MCS {mcs}, NSS1)', linewidth=1.5)

        # 处理 mag tracking on 的数据（每个 MCS 的 NSS0 和 NSS1）
        for i, mcs in enumerate(all_mcs):
            df_on_mcs = df_on[(df_on['rate'] == mcs) & df_on['evm_nss0'].notna() & df_on['evm_nss1'].notna()]
            if not df_on_mcs.empty:
                df_on_pivot_nss0 = df_on_mcs.pivot_table(index=['tx_power_set(dBm)'], values=['evm_nss0'])
                df_on_pivot_nss1 = df_on_mcs.pivot_table(index=['tx_power_set(dBm)'], values=['evm_nss1'])

                plt.plot(df_on_pivot_nss0.index, df_on_pivot_nss0['evm_nss0'],
                        marker=markers[(i + len(all_mcs)) % len(markers)], linestyle='-',
                        color=colors[(i + len(all_mcs)) % len(colors)],
                        label=f'Mag Tracking ON (MCS {mcs}, NSS0)', linewidth=1.5)
                plt.plot(df_on_pivot_nss1.index, df_on_pivot_nss1['evm_nss1'],
                        marker=markers[(i + len(all_mcs)) % len(markers)], linestyle='--',
                        color=colors[(i + len(all_mcs)) % len(colors)],
                        label=f'Mag Tracking ON (MCS {mcs}, NSS1)', linewidth=1.5)

        # 图表设置
        plt.ylim([-45, -18])
        plt.xlim([-12, 20])
        plt.xlabel('tx_power_set (dBm)')
        plt.ylabel('EVM (dB)')
        plt.title('EVM Comparison by MCS: Mag Tracking OFF vs ON')
        plt.grid(True, alpha=0.3)
        plt.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=9)
        plt.tight_layout()

        output_file = os.path.join(r"D:\users\gxu\e22_tx\260311", 'evm_comparison_per_mcs_combined.png')
        plt.savefig(output_file, dpi=100, bbox_inches='tight')
        print(f"图表已保存到: {output_file}")

    # 显示图表
    plt.show()

    # 输出每个 MCS 的统计信息
    print("\n--- Mag Tracking OFF 统计 ---")
    for mcs in all_mcs:
        df_off_mcs = df_off[(df_off['rate'] == mcs) & df_off['evm_nss0'].notna() & df_off['evm_nss1'].notna()]

        if not df_off_mcs.empty:
            power_range = (df_off_mcs['tx_power_set(dBm)'].min(), df_off_mcs['tx_power_set(dBm)'].max())
            evm_nss0_range = (df_off_mcs['evm_nss0'].min(), df_off_mcs['evm_nss0'].max())
            evm_nss1_range = (df_off_mcs['evm_nss1'].min(), df_off_mcs['evm_nss1'].max())

            print(f"MCS {mcs}:")
            print(f"  Power range: {power_range[0]} to {power_range[1]} dBm")
            print(f"  EVM NSS0: {evm_nss0_range[0]:.2f} to {evm_nss0_range[1]:.2f} dB")
            print(f"  EVM NSS1: {evm_nss1_range[0]:.2f} to {evm_nss1_range[1]:.2f} dB")

    print("\n--- Mag Tracking ON 统计 ---")
    for mcs in all_mcs:
        df_on_mcs = df_on[(df_on['rate'] == mcs) & df_on['evm_nss0'].notna() & df_on['evm_nss1'].notna()]

        if not df_on_mcs.empty:
            power_range = (df_on_mcs['tx_power_set(dBm)'].min(), df_on_mcs['tx_power_set(dBm)'].max())
            evm_nss0_range = (df_on_mcs['evm_nss0'].min(), df_on_mcs['evm_nss0'].max())
            evm_nss1_range = (df_on_mcs['evm_nss1'].min(), df_on_mcs['evm_nss1'].max())

            print(f"MCS {mcs}:")
            print(f"  Power range: {power_range[0]} to {power_range[1]} dBm")
            print(f"  EVM NSS0: {evm_nss0_range[0]:.2f} to {evm_nss0_range[1]:.2f} dB")
            print(f"  EVM NSS1: {evm_nss1_range[0]:.2f} to {evm_nss1_range[1]:.2f} dB")

if __name__ == "__main__":
    # 设置是否按MCS分成多个图，或者所有MCS在一个图上
    separate = True  # False表示所有MCS在一个图上，True表示每个MCS一个图

    compare_evm_per_mcs(separate)
