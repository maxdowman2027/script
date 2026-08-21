# lut_phase0_fit — LUT 相位强制过 0 点拟合优化

将硬件读回的 DPD LUT（`lut_data_map` 格式 I/Q）做 **AM-PM 过原点** 平滑，生成可回写的新系数表。

| 文件 | 说明 |
|------|------|
| `dpd/lut_phase0_fit.py` | Python 库 + CLI（推荐日常使用，含绘图） |
| `dpd/lut_phase0_fit.c` | C 参考实现（嵌入式 / 离线工具链对照） |
| `skill/lut_phase0_fit.skill` | 短技能摘要 |

---

## 1. 问题背景

`wifi_dpd_test_wifi7.dpd_lut_read` 读回的 `lut_data_map_lut*.txt` 中，常见：

- 低索引出现 **幅度塌陷 / 相位跳变**（例如 index=2）
- Q 分量噪声导致 AM-PM 曲线不光滑
- 希望 LUT 相位特性满足 **φ(0)=0**（过 0 点），便于与 PA AM-PM / 校准约定一致

MATLAB 侧同类思路见 `dpd/polyfit_for_lut.m` + `wlsEst.m`：对 I/Q 做加权多项式，且可通过 `orderVec` 跳过常数项使曲线过原点。本工具改为在 **幅度 / 相位极坐标** 上显式约束过 0。

---

## 2. 算法

输入：长度 \(N\) 的定点 I/Q（默认 \(N=33\)，index 0 为零垫）。

1. **极坐标**  
   \[
   a_k = |I_k + j Q_k|,\quad
   \varphi_k = \mathrm{unwrap}\angle(I_k + j Q_k)
   \]

2. **剔点**  
   默认排除 index `2`（读回常见坏点）；`a_k=0` 的点不参与拟合。

3. **过原点加权多项式**（无常数项）  
   \[
   a(x)\approx\sum_{p=1}^{d_a} c_p\, x^{p},\qquad
   \varphi(x)\approx\sum_{p=1}^{d_\varphi} b_p\, x^{p}
   \]
   其中 \(x\) 为 LUT **索引** \(0..N-1\)。  
   因此 \(a(0)=0\)、\(\varphi(0)=0\)。

4. **权重**（对齐 `polyfit_for_lut.m` 的 \(Q\) 对角线思想）  
   - 前 `early_bins=3` 个点：权重 `1`  
   - 其余点：权重 `200`  
   → 更信任中高幅度区形状。

5. **重建**  
   \[
   z_k = a(k)\,e^{j\varphi(k)}
   \]
   - index `0` → `(I,Q)=(0,0)`  
   - index `1` → **强制 Q=0**（首有效点相位 0°），\(I=\mathrm{round}|z_1|\)  
   - 其余点对 \(\Re z,\Im z\) 四舍五入为整数

6. **输出**  
   - `*_phase0fit.txt`：`lut_data_map_lutN = {...}`  
   - `*_phase0fit.csv`：`index,i,q`（给 C 工具 / 表格）  
   - `*_phase0fit.png`：原曲线 / 拟合 / 输出对比（仅 Python）

---

## 3. Python 用法

仓库根：`D:\users\gxu\scripts`。

```powershell
# 默认：deg_amp=4, deg_ph=4, exclude=2，输出写到输入同目录
python dpd/lut_phase0_fit.py `
  "D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\dpd_lut_fig_wifi7\20260821\1lut\dig_gain1_66\lut_data_map_lut0.txt"

# 指定输出目录与参数
python dpd/lut_phase0_fit.py INPUT.txt -o OUT_DIR --deg-amp 4 --deg-ph 4 --exclude 2
python dpd/lut_phase0_fit.py INPUT.txt --exclude 2,3 --no-plot
```

### 库 API

```python
from dpd.lut_phase0_fit import load_lut_data_map, map_to_arrays, fit_lut_phase0, write_lut_data_map

m = load_lut_data_map(r"path\lut_data_map_lut0.txt")
ii, qq = map_to_arrays(m)
r = fit_lut_phase0(ii, qq, deg_amp=4, deg_ph=4, exclude=[2])
write_lut_data_map(r"out\lut_data_map_lut0_phase0fit.txt", r["i_out"], r["q_out"], lut_sel=0)
```

---

## 4. C 用法

### 编译

```powershell
gcc -O2 -o dpd/lut_phase0_fit.exe dpd/lut_phase0_fit.c -lm
# 或 cl /O2 dpd\lut_phase0_fit.c
```

### 运行

输入须为 CSV（可用 Python 先从 map 导出，或直接用 Python 生成的 `*_phase0fit.csv` 的**原始**旁路：Python `run_file` 会写出拟合后的 csv；若要对原始 I/Q 跑 C，先：

```powershell
python -c "from pathlib import Path; from dpd.lut_phase0_fit import load_lut_data_map, map_to_arrays, write_iq_csv; m=load_lut_data_map(r'IN.txt'); i,q=map_to_arrays(m); write_iq_csv(r'IN_raw.csv', i.astype(int), q.astype(int))"
```

更简单：Python 拟合时已写出结果 csv；要用 C **复现同一算法**，应对 **原始** I/Q CSV：

```powershell
# 由 map 导出原始 CSV（index,i,q）
python -c "from dpd.lut_phase0_fit import load_lut_data_map, map_to_arrays, write_iq_csv; import numpy as np; m=load_lut_data_map(r'D:\path\lut_data_map_lut0.txt'); i,q=map_to_arrays(m); write_iq_csv(r'D:\path\lut_raw.csv', np.rint(i).astype(int), np.rint(q).astype(int))"

.\dpd\lut_phase0_fit.exe D:\path\lut_raw.csv D:\path\lut_c_out.csv 4 4 2
```

参数：`deg_amp deg_ph exclude`（`exclude<0` 表示不删点）。  
成功时额外写同名 `.txt` 的 `lut_data_map`。

### C API（可嵌入）

```c
LutPhase0Fit fit;
memset(&fit, 0, sizeof(fit));
fit.n = 33;
fit.deg_amp = 4;
fit.deg_ph = 4;
fit.exclude = 2;
/* fill fit.i_in[] / fit.q_in[] */
int rc = lut_phase0_fit_run(&fit);
/* fit.i_out[] / fit.q_out[] */
```

---

## 5. 参数建议

| 参数 | 默认 | 说明 |
|------|------|------|
| `deg_amp` / `deg_ph` | 4 | 过高易在高端振荡；过低抹平真实 AM-PM |
| `exclude` | `2` | 按读回坏点调整；无坏点可 `--exclude` 空（Python 传无有效数字）或 C 用 `-1` |
| `force_index1_real` | 开 | 首有效点相位钉在 0° |

验收：输出 `phase@0`、`phase@1` 应为 **0°**；AM 曲线应单调光滑（相对原表去掉塌陷点）。

---

## 6. 与训练流水线关系

| 步骤 | 工具 |
|------|------|
| 训练估 LUT | `dpd/xian_static_dpd_main1.py`（含 iQxel PN） |
| 写板 / 读回 | `wifi_dpd_test_wifi7.py` `dpd_mem_write` / `dpd_lut_read` |
| **读回后修相** | **`lut_phase0_fit`（本工具）** |
| 再写板 | 将 `*_phase0fit.txt` 贴回 `lut_data_map_lut*` |

本工具 **不替代** 逆模型训练；只优化 **已有定点 LUT 表** 的相位过 0 与平滑。

---

## 7. 例：dig_gain1_66 / 1lut

输入：

`...\Log\dpd_lut_fig_wifi7\20260821\1lut\dig_gain1_66\lut_data_map_lut0.txt`

典型现象：index=2 幅度异常偏低、相位 ~46°。  
拟合后 index2 被平滑，相位从 0 连续爬升，可用于上板对比。

---

## 8. 限制

- 单组 LUT（一次处理一个 `lut_data_map_lutN`）；多 LUT 请分别跑。  
- C 版默认只支持 **一个** exclude 索引；多点剔除用 Python。  
- 横轴为 **LUT index**，不是物理幅度轴；若需按 `|z|` 拟合，需另扩展。  
- 加权 LS 在极端病态数据下可能失败（C 返回负码）；可降阶或改 exclude。
