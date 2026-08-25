# lut_phase0_fit — 多 LUT / Master LUT 相位过 0 拟合

对硬件读回的 DPD `lut_data_map` I/Q 做坏点剔除与平滑，生成可回写系数。

| 文件 | 说明 |
|------|------|
| `dpd/lut_phase0_fit.py` | Python 库 + CLI |
| `dpd/fit_lut_custom_phase0.py` | 260825 3lut 一键入口（poly master + slave passthrough） |
| `dpd/lut_phase0_fit.c` | C 参考（与 Py 对齐演进中） |
| `skill/lut_phase0_fit.skill` | 短摘要 |

---

## 1. 背景

### 1lut（260821）

拟合后 AM 更光滑、板上 **EVM 更好**；maxerr 可能变大 — **勿用 maxerr 评判**。

### 3lut（260825 教训）

1. 对 lut1/lut2 **全表 poly** 会发明低端非零点 → 记忆支路损坏。  
2. 对 **相位** 做过原点 poly 会把中段 φ（~3–8°）整体压低 → LUT0 相位趋势错误。  

**正确做法**：master **amp poly + 相位保趋势**；slave **passthrough**；锁定 `|z[1]|`。

---

## 2. 算法

### 2.1 `poly`（默认，推荐 3lut）

1. `exclude=auto` 坏点 → amp/phase 邻点插值  
2. **幅度**：无常数项加权多项式（`--deg-amp`，默认 4）  
3. **相位**：**保留插值后的原趋势**（不做过原点 phase poly）  
4. master：锁定 `|z[1]|`，强制 Q[1]=0  
5. 有 `--master-lut` 时，slave 默认 **passthrough**（可用 `--slave-method` 覆盖）

### 2.2 `poly_ph`（旧版 / 1lut）

amp + phase 均无常数项 poly。仅当训练相位中段已接近 0 时适用。

### 2.3 备选

| method | 说明 |
|--------|------|
| `repair` | 只修坏点 + master 相位对齐（改写最少） |
| `smooth` | 混合 MA + amp 钳位 |
| `iqpoly` | I/Q 过原点多项式（MATLAB `polyfit_for_lut`） |
| `ma` | 全表 amp/phase 滑动平均 |

---

## 3. 用法

```powershell
cd D:\users\gxu\scripts

# 推荐 3lut（默认 poly = amp poly + phase preserve；slave passthrough）
python dpd/lut_phase0_fit.py `
  "D:\test_data\AP\260825_dpd\3lut_multi_frame_training\original_coefficients" `
  -o "D:\test_data\AP\260825_dpd\3lut_multi_frame_training\fit_coefficients" `
  --master-lut 0 --scope all

# 或一键脚本
python dpd/fit_lut_custom_phase0.py

# 旧版 amp+phase 双 poly（midφ≈0 的 1lut）
python dpd/lut_phase0_fit.py DIR -o OUT --method poly_ph --master-lut 0

# 更保真：只修 master 坏点
python dpd/lut_phase0_fit.py DIR -o OUT --method repair --master-lut 0 --slave-method passthrough
```

产物：`lut_data_map_lutN.txt`（HW 写回名）、`*_phase0_poly.txt/.csv/.png`、`lut_data_map_all_phase0_poly.txt`。

---

## 4. 参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `--method` | `poly` | `poly` / `poly_ph` / `iqpoly` / `smooth` / `repair` / `ma` |
| `--master-lut` | — | `reg_dpd_master_lut` |
| `--slave-method` | auto | auto：对 `poly`/`poly_ph`/`iqpoly`/`ma` → `passthrough` |
| `--deg-amp` / `--deg-ph` | 4 / 4 | amp 阶数；`deg-ph` 仅 `poly_ph`/`iqpoly` |
| `--exclude` | `auto` | 自动坏点 |
| `--scope` | `all` | `all` / `master_only` |

---

## 5. 260825 推荐产物

`D:\test_data\AP\260825_dpd\3lut_multi_frame_training\fit_coefficients\`

| LUT | 处理 |
|-----|------|
| lut0 | amp poly；phase 保趋势；exclude `[2]`；`|z1|=4096` |
| lut1/2 | **原样**（passthrough） |

上板对比 **EVM / spectrum**，勿盯 maxerr。
