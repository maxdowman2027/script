
import math
import random
import os
from find_nsym_16 import calculate_nsym

# 目标 ru_allocation 值
target_ru = 26

# 查找 n_sym = 16 的情况
print(f"正在查找 ru_allocation = {target_ru}, n_sym = 16 的配置...")
found_16 = False
for apep_len in range(4, 10000, 4):
    n_sym = calculate_nsym(target_ru, apep_len)
    if n_sym == 16:
        last_mpdu_len = apep_len - 4  # 固定比apep_len小4
        print(f"  找到配置:")
        print(f"    ru_allocation = {target_ru}")
        print(f"    apep_len = {apep_len}")
        print(f"    last_mpdu_len = {last_mpdu_len}")
        print(f"    n_sym = {n_sym}")
        found_16 = True
        break

    if n_sym > 16:
        break

# 查找 n_sym = 340 的情况
print(f"\n正在查找 ru_allocation = {target_ru}, n_sym = 340 的配置...")
found_340 = False
for apep_len in range(1000, 100000, 4):
    n_sym = calculate_nsym(target_ru, apep_len)
    if n_sym == 340:
        last_mpdu_len = apep_len - 4  # 固定比apep_len小4
        print(f"  找到配置:")
        print(f"    ru_allocation = {target_ru}")
        print(f"    apep_len = {apep_len}")
        print(f"    last_mpdu_len = {last_mpdu_len}")
        print(f"    n_sym = {n_sym}")
        found_340 = True
        break

    if n_sym > 340:
        break

if not found_16:
    print(f"\n未找到 ru_allocation = {target_ru}, n_sym = 16 的配置")

if not found_340:
    print(f"\n未找到 ru_allocation = {target_ru}, n_sym = 340 的配置")
