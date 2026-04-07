import math
import random
import os

os.system('cls' if os.name == 'nt' else 'clear')

# %% Input
ru_alloc_list = [26, 52, 106, 242, 484, 996, 1992]

# %% Input argv here
ul_bw = 3
ru_allocation = 26
ru_allocation_index = 16
apep_len = 21
last_mpdu_len = 17 
ul_mcs = 0
ul_nss = 1
ul_coding = 1
ul_gi_ltf = 1
ul_num_ltf = 1 #0/1/2/3/4 represents for 1/2/4/6/8 HE-LTFs
ul_dcm = 0
ul_stbc = 0
nominal_packet_padding = 16
bss_color = 32
txop = 127

# %% Tmp var
ul_ru = ru_alloc_list.index(ru_allocation)
print(f"ul_ru:{ul_ru}")
if (last_mpdu_len % 4) == 0:
    last_mpdu_padding = 0
else:
    last_mpdu_padding = 4 - (last_mpdu_len % 4)

if ul_gi_ltf == 0:
    he_ltf_txtime = 4.8
    sym_txtime = 14.4
    gi_type = 2
    ltf_type = 0
elif ul_gi_ltf == 1:
    he_ltf_txtime = 8
    sym_txtime = 14.4
    gi_type = 2
    ltf_type = 1
else:
    he_ltf_txtime = 16
    sym_txtime = 16
    gi_type = 3
    ltf_type = 2

if ul_num_ltf == 0:
    num_ltf = 1
elif ul_num_ltf == 1:
    num_ltf = 2
elif ul_num_ltf == 2:
    num_ltf = 4
elif ul_num_ltf == 3:
    num_ltf = 6
elif ul_num_ltf == 4:
    num_ltf = 8

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

# 关键计算：MATLAB使用1基索引，Python使用0基索引
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

l_ldpc = 0
l_ldpc_code = 0
temp_val = n_pld + 912 * (12 - r_x12[ul_mcs]) / 12

print(f"n_avbits:{n_avbits},temp_val:{temp_val} ,n_pld :{n_pld},(12 - r_x12[ul_mcs]) / 12:{(12 - r_x12[ul_mcs]) / 12}")
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
print(f"l_ldpc:{l_ldpc} ,l_ldpc_code:{l_ldpc_code}")
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
print(f"n_sym:{n_sym}")
t_preamble = 20 + 4 + 8 + 8 + num_ltf * he_ltf_txtime

if nominal_packet_padding == 0:
    t_pe = 0
elif nominal_packet_padding == 8:
    if a_factor < 3:
        t_pe = 0
    elif a_factor == 3:
        t_pe = 4
    else:
        t_pe = 8
elif nominal_packet_padding == 16:
    t_pe = 4 * a_factor
else:
    t_pe = 0

txtime = t_preamble + n_sym * sym_txtime + t_pe
print(f"txtime:{txtime} ,t_pe:{t_pe} ,sym_txtime:{sym_txtime}")
if 4 * (math.ceil((txtime - 20) / 4) - ((txtime - 20) / 4)) + t_pe >= sym_txtime:
    pe_disambiguity = 1
else:
    pe_disambiguity = 0
print(f"pe_disambiguity:{pe_disambiguity} ")
l_len = math.ceil((txtime - 20) / 4) * 3 - 3 - 2

if ul_coding:
    psdu_len = math.floor((n_pld - 16) / 8)
    pre_fec_padding_phy = int((n_pld - 16) % 8)
else:
    psdu_len = math.floor((n_pld - 16 - 6) / 8)
    pre_fec_padding_phy = int((n_pld - 16 - 6) % 8)

n_short_per_ncw = int(math.floor(n_short / n_cw))
n_short_mod_ncw = int(n_short % n_cw)

n_repeat = max(n_avbits - n_cw * l_ldpc * (12 - r_x12[ul_mcs]) / 12 - n_pld, 0)
ldpc_repeat_punc_ind = 1 if n_repeat > 0 else 0

if ldpc_repeat_punc_ind:
    n_repeat_punc_per_cw = int(math.floor(n_repeat / n_cw))
    n_repeat_punc_mod_cw = int(n_repeat % n_cw)
else:
    n_repeat_punc_per_cw = int(math.floor(n_punc / n_cw))
    n_repeat_punc_mod_cw = int(n_punc % n_cw)

pre_fec_padding_mac = psdu_len - apep_len
if pre_fec_padding_mac > last_mpdu_padding:
    pre_fec_padding_mac -= last_mpdu_padding
    pre_fec_padding_mac_ena = 1
else:
    pre_fec_padding_mac_ena = 0

# %% Print all reg_input
print(f'reg_faketb_a_factor={a_factor}')

# 0xc302249c - 与MATLAB完全一致
reg_249c = (1 << 31) | (0 << 23) | (0 << 22) | (0 << 21) | (ru_allocation_index << 13) | \
           (ul_coding << 12) | (0 << 9) | (ul_num_ltf << 6) | (0 << 5) | \
           ((ul_nss + ul_stbc - 1) << 2) | ul_gi_ltf
print(f'0xc302249c=0x{reg_249c:08x}')

reg_24a0 = (pre_fec_padding_phy << 27) | (0 << 12) | int(n_sym)
print(f'0xc30224a0=0x{reg_24a0:08x}')

reg_24a4 = (pre_fec_padding_mac_ena << 21) | pre_fec_padding_mac
print(f'0xc30224a4=0x{reg_24a4:08x}')

reg_24a8 = (ul_stbc << 31) | (t_pe << 26) | (ul_bw << 24) | \
           (15 << 19) | (15 << 15) | (15 << 11) | (15 << 7) | \
           (bss_color << 1)
print(f'0xc30224a8=0x{reg_24a8:08x}')

reg_24ac = (a_factor << 23) | (l_ldpc_code << 21) | (pe_disambiguity << 20) | \
           (ul_mcs << 16) | (0 << 15) | (3 << 13) | (ul_dcm << 12) | int(l_len)
print(f'0xc30224ac=0x{reg_24ac:08x}')

print(f'0xc30224b0=0x{psdu_len:08x}')

reg_24b4 = (65535 << 16) | (ldpc_extra_sym << 14) | n_cw
print(f'0xc30224b4=0x{reg_24b4:08x}')

reg_24b8 = (n_short_mod_ncw << 14) | n_short_per_ncw
print(f'0xc30224b8=0x{reg_24b8:08x}')

reg_24bc = (ldpc_repeat_punc_ind << 28) | (n_repeat_punc_mod_cw << 14) | n_repeat_punc_per_cw
print(f'0xc30224bc=0x{reg_24bc:08x}')
