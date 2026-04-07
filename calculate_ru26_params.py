
import math

ru_allocation = 26
ul_mcs = 0
ul_nss = 1
ul_dcm = 0

ru_alloc_list = [26, 52, 106, 242, 484, 996, 1992]
ul_ru = ru_alloc_list.index(ru_allocation)

nsd_1lax = [
    [24, 48, 102, 234, 468, 980, 1960],
    [12, 24, 51, 117, 234, 490, 980]
]

n_bpscs = [1, 2, 2, 4, 4, 6, 6, 6, 8, 8, 10, 10]
r_x12 = [6, 6, 9, 6, 9, 8, 9, 10, 9, 10, 9, 10]

n_dbps = math.floor(nsd_1lax[ul_dcm][ul_ru] * r_x12[ul_mcs] * n_bpscs[ul_mcs] / 12 * ul_nss)

print(f"ru_allocation = {ru_allocation}, ul_ru = {ul_ru}")
print(f"nsd_1lax[ul_dcm][ul_ru] = {nsd_1lax[ul_dcm][ul_ru]}")
print(f"r_x12[ul_mcs] = {r_x12[ul_mcs]}")
print(f"n_bpscs[ul_mcs] = {n_bpscs[ul_mcs]}")
print(f"n_dbps = {n_dbps}")

# 计算理论上的apep_len与n_sym的关系
for n_sym in range(10, 350, 2):
    # 假设a_init=4，ul_coding=1，ul_stbc=0
    numerator = n_sym * n_dbps  # 大约的关系
    apep_len = math.floor((numerator - 16) / 8)
    print(f"n_sym = {n_sym}, 理论apep_len = {apep_len}")
