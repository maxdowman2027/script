# lut_phase0_fit — 多 LUT / Master LUT 相位过 0 平滑

对硬件读回的 DPD `lut_data_map` I/Q 做 **AM-PM 过原点** 平滑。支持：

- **单 LUT 文件**或**目录内多组** `lut_data_map_lut*.txt`
- 可选 **`master_lut`**（对应 `reg_dpd_master_lut`）与 **`scope`**
- 两种算法：`ma`（芯片软件推荐）/ `poly`（PC 离线）

| 文件 | 说明 |
|------|------|
| `dpd/lut_phase0_fit.py` | Python 库 + CLI |
| `dpd/lut_phase0_fit.c` | C 参考（单表；`ma`/`poly`） |
| `skill/lut_phase0_fit.skill` | 短摘要 |

---

## 1. 背景

`dpd_lut_read` 读回表常有：

- 低索引坏点（如 index=2 幅度塌陷）
- Q 噪声导致相位毛刺
- 多 LUT 时仅 **master** 承载主路径增益，其余为记忆抽头

需要：平滑 + **φ(0)=0**，且算法在芯片上可跑、不太费时。

---

## 2. 算法

### 2.1 公共步骤（`ma` / `poly`）

1. \(a_k=|I+jQ|\)，\(\varphi_k=\mathrm{unwrap}\angle(\cdot)\)
2. 剔除/插值 `exclude` 索引（默认 `2`）
3. 平滑得到 \(a'(k),\varphi'(k)\)
4. **过 0**：\(a'(0)=0\)，\(\varphi'\leftarrow\varphi'-\varphi'(0)\)
5. \(z=a'e^{j\varphi'}\)；近零幅度点置 `(0,0)`
6. **仅 master**（且 \(a'(1)\ge1\)）：index1 强制 Q=0
7. 四舍五入写回定点 I/Q

### 2.2 `ma` — 芯片推荐（默认）

对 \(a,\varphi\) 各做一次 **奇数窗居中滑动平均**（默认窗长 **5**）：

- 复杂度 **O(N·W)**，N=33、W=5 → 约几百次加减，无矩阵求逆
- 边沿用边界复制
- 适合 training 后 / application 前在固件里轻量修表

### 2.3 `poly` — PC 离线

无常数项加权多项式（对齐早期 `polyfit_for_lut` 思想）：

\[
a(x)=\sum_{p=1}^{d_a}c_p x^p,\quad
\varphi(x)=\sum_{p=1}^{d_\varphi}b_p x^p
\]

权重：前 3 点=1，其余=200。阶数默认 4。条件数更高，更适合离线。

### 2.4 多 LUT / master

| 参数 | 含义 |
|------|------|
| `--master-lut N` | 对应 `reg_dpd_master_lut`（如 0） |
| `--scope all` | 每组 LUT 都平滑（默认） |
| `--scope master_only` | **只平滑 master**；其它组原样写出（passthrough） |

Master 才强制 index1 实部；slave 常在低索引接近 0，不强行钉相位。

---

## 3. Python 用法

```powershell
cd D:\users\gxu\scripts

# 目录：3 组 LUT，芯片友好 MA，全部平滑，master=0
python dpd/lut_phase0_fit.py `
  "D:\test_data\AP\260821_dpd\3lut_test\dynamic_multi_frame_training" `
  -o "D:\users\gxu\scripts\dpd\output\260821\3lut_phase0_ma" `
  --method ma --ma-win 5 --master-lut 0 --scope all

# 只修 master
python dpd/lut_phase0_fit.py DIR -o OUT --method ma --master-lut 0 --scope master_only

# 离线 poly
python dpd/lut_phase0_fit.py DIR -o OUT --method poly --deg-amp 4 --deg-ph 4 --exclude 2

# 单文件
python dpd/lut_phase0_fit.py PATH\lut_data_map_lut0.txt -o OUT --method ma
```

产物（每组）：

- `lut_data_map_lutK_phase0_ma.txt` / `_poly.txt`
- 同名 `.csv`、`.png`
- `lut_data_map_all_phase0_<method>.txt`（合并）

### API

```python
from dpd.lut_phase0_fit import run_multi, fit_lut_phase0

run_multi(r"D:\path\to\maps", r"D:\out", method="ma", master_lut=0, scope="all")
```

---

## 4. C 用法（单表）

```text
lut_phase0_fit.exe in.csv out.csv
lut_phase0_fit.exe in.csv out.csv ma 5 2
lut_phase0_fit.exe in.csv out.csv poly 4 4 2
```

固件可只移植 `lut_phase0_fit_run()` 的 **MA 路径**（`moving_average` + unwrap + 过 0 + 重建）。多 LUT 时对每个 `lut_sel` 调一次；`is_master` 仅对 master 置 1。

样例 CSV：`dpd/testdata/lut_phase0_fit/sample_lut_raw.csv`

---

## 5. 与训练流程关系

```text
训练 / 读回 → lut_data_map_lut0..K.txt
       ↓
lut_phase0_fit (ma, scope=all|master_only)
       ↓
写回 dpd_mem_write / itera LUT
```

不替代 RLS/静态训练；只做 **表后处理**。

---

## 6. 参数速查

| 参数 | 默认 | 说明 |
|------|------|------|
| `--method` | `ma` | `ma` / `poly` |
| `--ma-win` | 5 | 奇数窗；越大越钝 |
| `--master-lut` | 无 | `reg_dpd_master_lut` |
| `--scope` | `all` | `all` / `master_only` |
| `--exclude` | `2` | 平滑前插值替换的坏点 |

---

## 7. 例：260821 3lut dynamic_multi_frame_training

目录含 `lut_data_map_lut0/1/2.txt`，CSV 中 `reg_dpd_master_lut=0`。

推荐：

```powershell
python dpd/lut_phase0_fit.py `
  "D:\test_data\AP\260821_dpd\3lut_test\dynamic_multi_frame_training" `
  -o "...\output\260821\3lut_phase0_ma" `
  --method ma --master-lut 0 --scope all
```

验收：`phase@0≈0°`；master 的 `phase@1≈0°`；index2 不再塌陷。
