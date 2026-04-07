import math
import random
import os

def calculate_nsym(ru_allocation, apep_len, ul_mcs=0, ul_nss=1, ul_dcm=0, ul_coding=1, ul_stbc=0):
    os.system('cls' if os.name == 'nt' else 'clear')

    ru_alloc_list = [26, 52, 106, 242, 484, 996, 1992]

    ul_ru = ru_alloc_list.index(ru_allocation)

    nsd_1lax = [
        [24, 48, 102, 234, 468, 980, 1960],
        [12, 24, 51, 117, 234, 490, 980]
    ]

    nsd_short = [
        [6, 12, 24, 60, 120, 240, 492],
        [2, 6, 12, 30, 60, 120, 246]
    ]

    n_bpscs = [1, 2, 2, 4, 4, 6, 6, 6, 8, 8, 10, 10]
    r_x12 = [6, 6, 9, 6, 9, 8, 9, 10, 9, 10, 9, 10]

    n_dbps = math.floor(nsd_1lax[ul_dcm][ul_ru] * r_x12[ul_mcs] * n_bpscs[ul_mcs] / 12 * ul_nss)
    n_cbps = nsd_1lax[ul_dcm][ul_ru] * n_bpscs[ul_mcs] * ul_nss
    n_cbps_short = nsd_short[ul_dcm][ul_ru] * n_bpscs[ul_mcs] * ul_nss
    n_dbps_short = n_cbps_short * r_x12[ul_mcs] / 12

    m_stbc = 2 if ul_stbc == 1 else 1

    if ul_coding:
        numerator = 8 * apep_len + 16
        n_sym_init = math.ceil(numerator / (m_stbc * n_dbps)) * m_stbc
        n_excess = numerator % (m_stbc * n_dbps)
    else:
        numerator = 8 * apep_len + 16 + 6
        n_sym_init = math.ceil(numerator / (m_stbc * n_dbps)) * m_stbc
        n_excess = numerator % (m_stbc * n_dbps)

    if n_excess == 0:
        a_init = 4
    else:
        a_init = min(4, math.ceil(n_excess / (m_stbc * n_dbps_short)))

    if a_init == 4:
        n_dbps_last_init = n_dbps
        n_cbps_last_init = n_cbps
    else:
        n_dbps_last_init = a_init * n_dbps_short
        n_cbps_last_init = a_init * n_cbps_short

    n_pld = (n_sym_init - m_stbc) * n_dbps + m_stbc * n_dbps_last_init
    n_avbits = (n_sym_init - m_stbc) * n_cbps + m_stbc * n_cbps_last_init

    if n_avbits <= 648:
        n_cw = 1
    elif n_avbits <= 1296:
        n_cw = 1
    elif n_avbits <= 1944:
        n_cw = 1
    elif n_avbits <= 2592:
        n_cw = 2
    else:
        n_cw = math.ceil(n_pld / (1944 * r_x12[ul_mcs] / 12))

    temp_val = n_pld + 912 * (12 - r_x12[ul_mcs]) / 12

    if temp_val > n_avbits and temp_val <= 648:
        l_ldpc = 648
        l_ldpc_code = 0
    elif temp_val <= n_avbits and n_avbits <= 648:
        l_ldpc = 1296
        l_ldpc_code = 1
    elif n_avbits > 648 and n_avbits < (n_pld + 1464 * (12 - r_x12[ul_mcs]) / 12):
        l_ldpc = 1296
        l_ldpc_code = 1
    elif (n_pld + 1464 * (12 - r_x12[ul_mcs]) / 12) <= n_avbits and n_avbits <= 1944:
        l_ldpc = 1944
        l_ldpc_code = 2
    elif n_avbits > 1944 and n_avbits < (n_pld + 2916 * (12 - r_x12[ul_mcs]) / 12):
        l_ldpc = 1296
        l_ldpc_code = 1
    elif n_avbits >= (n_pld + 2916 * (12 - r_x12[ul_mcs]) / 12):
        l_ldpc = 1944
        l_ldpc_code = 2

    n_short = max(0, n_cw * l_ldpc * r_x12[ul_mcs] / 12 - n_pld)
    n_punc = max(0, n_cw * l_ldpc - n_avbits - n_short)

    ldpc_extra_sym = 0
    threshold1 = 0.1 * n_cw * l_ldpc * (12 - r_x12[ul_mcs]) / 12
    threshold2 = 1.2 * n_punc * r_x12[ul_mcs] / (12 - r_x12[ul_mcs])
    threshold3 = 0.3 * n_cw * l_ldpc * (12 - r_x12[ul_mcs]) / 12

    if n_punc > threshold1 and n_short < threshold2:
        ldpc_extra_sym = 1
        if a_init == 3:
            n_avbits += m_stbc * (n_cbps - 3 * n_cbps_short)
            n_punc = max(0, n_cw * l_ldpc - n_avbits - n_short)
        else:
            n_avbits += m_stbc * n_cbps_short
            n_punc = max(0, n_cw * l_ldpc - n_avbits - n_short)
    elif n_punc > threshold3:
        ldpc_extra_sym = 1
        if a_init == 3:
            n_avbits += m_stbc * (n_cbps - 3 * n_cbps_short)
            n_punc = max(0, n_cw * l_ldpc - n_avbits - n_short)
        else:
            n_avbits += m_stbc * n_cbps_short
            n_punc = max(0, n_cw * l_ldpc - n_avbits - n_short)

    if ul_coding and ldpc_extra_sym:
        if a_init == 4:
            n_sym = n_sym_init + m_stbc
            a_factor = 1
        else:
            n_sym = n_sym_init
            a_factor = a_init + 1
    else:
        n_sym = n_sym_init
        a_factor = a_init

    return n_sym

# 目标 ru_allocation 值
target_ru_list = [52, 242, 484, 996, 1992]
target_nsym = 340

print(f"查找使 n_sym = {target_nsym} 的配置：")
print("=" * 60)

for ru in target_ru_list:
    print(f"\n正在查找 ru_allocation = {ru} 的配置...")

    # 遍历可能的 apep_len 值（步长为 4，因为 last_mpdu_len 要求是 4 的倍数）
    found = False
    for apep_len in range(1000, 100000, 4):
        n_sym = calculate_nsym(ru, apep_len)

        if n_sym == target_nsym:
            # last_mpdu_len 应该是 <= apep_len 且是 4 的倍数
            last_mpdu_len = apep_len if apep_len % 4 == 0 else apep_len - (apep_len % 4)
            print(f"  找到配置:")
            print(f"    ru_allocation = {ru}")
            print(f"    apep_len = {apep_len}")
            print(f"    last_mpdu_len = {last_mpdu_len}")
            print(f"    n_sym = {n_sym}")
            found = True
            break

        if n_sym > target_nsym:
            break

    if not found:
        print(f"  未找到使 n_sym = {target_nsym} 的配置")
