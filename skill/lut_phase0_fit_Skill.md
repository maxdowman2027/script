# lut_phase0_fit — 多 LUT / Master LUT 相位过 0 平滑

对硬件读回的 DPD `lut_data_map` I/Q 做 **AM-PM 过原点** 平滑。支持：

- **单 LUT 文件**或**目录内多组** `lut_data_map_lut*.txt`
- 可选 **`master_lut`**（对应 `reg_dpd_master_lut`）与 **`scope`**
- 两种算法：`ma`（芯片软件推荐）/ `poly`（PC 离线）
- **自动坏点检测**（默认）：固件/脚本无需人为指定 `--exclude 2`

| 文件 | 说明 |
|------|------|
| `dpd/lut_phase0_fit.py` | Python 库 + CLI |
| `dpd/lut_phase0_fit.c` | C 参考（单表；`ma`/`poly` + auto exclude） |
| `skill/lut_phase0_fit.skill` | 短摘要 |

---

## 1. 背景

`dpd_lut_read` 读回表常有：

- 低索引坏点（如 index=2 幅度塌陷）——位置不固定，不能写死
- Q 噪声导致相位毛刺
- 多 LUT 时仅 **master** 承载主路径增益，其余为记忆抽头

需要：平滑 + **φ(0)=0**，且算法在芯片上可跑、全自动（按当前 LUT 系数自检坏点）。

---

## 2. 算法

### 2.1 公共步骤（`ma` / `poly`）

1. \(a_k=|I+jQ|\)，\(\varphi_k=\mathrm{unwrap}\angle(\cdot)\)
2. **自动检测坏点**（默认 `exclude=auto`）→ 邻点线性插值替换
3. 平滑得到 \(a'(k),\varphi'(k)\)
4. **过 0**：\(a'(0)=0\)，\(\varphi'\leftarrow\varphi'-\varphi'(0)\)
5. \(z=a'e^{j\varphi'}\)；近零幅度点置 `(0,0)`
6. **仅 master**（且 \(a'(1)\ge1\)）：index1 强制 Q=0
7. 四舍五入写回定点 I/Q

### 2.2 自动坏点检测（芯片友好，O(N)）

对每个内部索引 \(k=1\ldots N-2\)（Python: `detect_lut_outliers`；C: `lut_phase0_detect_outliers`）：

1. **两侧邻居幅度均 ≥ 200** 才检测（避免 slave 低索引真实 0 被误伤）
2. 邻域均值 \(\hat a=(a_{k-1}+a_{k+1})/2\)，相对残差 \(r=|a_k-\hat a|/\max(\hat a,1)\)
3. **塌陷**：\(a_k < 0.6\cdot\min(a_{k-1},a_{k+1})\)；**尖峰**：\(a_k > 1.8\cdot\max(a_{k-1},a_{k+1})\)
4. 判定：`(dip|spike) ∧ r≥0.40`；或相位跳变 >40° 且 `r≥0.25` 并伴随 dip/spike
5. 一次标出所有坏点后统一插值（可连续多点）

典型结果：master 上常见的 **index=2** 塌陷会被自动剔除；slave 低索引近零一般不会误报。

| `--exclude` | 含义 |
|-------------|------|
| `auto`（默认） | 上述检测 |
| `none` | 不剔除 |
| `2` / `2,5` | 人工指定（调试用） |

阈值常量与 C 宏对齐：`AUTO_AMP_*` / `LUT_PHASE0_AUTO_*`。

### 2.3 `ma` — 芯片推荐（默认）

对 \(a,\varphi\) 各做一次 **奇数窗居中滑动平均**（默认窗长 **5**）：

- 复杂度 **O(N·W)**，N=33、W=5 → 约几百次加减，无矩阵求逆
- 边沿用边界复制
- 适合 training 后 / application 前在固件里轻量修表

### 2.4 `poly` — PC 离线

无常数项加权多项式（对齐早期 `polyfit_for_lut` 思想）：

\[
a(x)=\sum_{p=1}^{d_a}c_p x^p,\quad
\varphi(x)=\sum_{p=1}^{d_\varphi}b_p x^p
\]

权重：前 3 点=1，其余=200。阶数默认 4。条件数更高，更适合离线。

### 2.5 多 LUT / master

| 参数 | 含义 |
|------|------|
| `--master-lut N` | 对应 `reg_dpd_master_lut`（如 0） |
| `--scope all` | 每组 LUT 都平滑（默认） |
| `--scope master_only` | **只平滑 master**；其它组原样写出（passthrough） |

Master 才强制 index1 实部；slave 常在低索引接近 0，不强行钉相位。每组 LUT **各自**跑一遍 auto 检测。

---

## 3. Python 用法

```powershell
cd D:\users\gxu\scripts

# 目录：3 组 LUT，芯片友好 MA，全部平滑，master=0（坏点自动检测，无需 --exclude 2）
python dpd/lut_phase0_fit.py `
  "D:\test_data\AP\260825_dpd\3lut_multi_frame_training\original_coefficients" `
  -o "D:\users\gxu\scripts\dpd\output\260825\3lut_phase0_ma" `
  --method ma --ma-win 5 --master-lut 0 --scope all

# 只修 master
python dpd/lut_phase0_fit.py DIR -o OUT --method ma --master-lut 0 --scope master_only

# 离线 poly（同样默认 auto）
python dpd/lut_phase0_fit.py DIR -o OUT --method poly --deg-amp 4 --deg-ph 4

# 调试：关闭 / 强制指定坏点
python dpd/lut_phase0_fit.py DIR -o OUT --method ma --exclude none
python dpd/lut_phase0_fit.py DIR -o OUT --method ma --exclude 2,5

# 单文件
python dpd/lut_phase0_fit.py PATH\lut_data_map_lut0.txt -o OUT --method ma
```

产物（每组）：

- `lut_data_map_lutK_phase0_ma.txt` / `_poly.txt`（头注释含 `exclude_mode` 与检出索引）
- 同名 `.csv`、`.png`（红点标出检出坏点）
- `lut_data_map_all_phase0_<method>.txt`（合并）

### API

```python
from dpd.lut_phase0_fit import run_multi, fit_lut_phase0, detect_lut_outliers

run_multi(r"D:\path\to\maps", r"D:\out", method="ma", master_lut=0, scope="all")
# exclude 默认 "auto"；也可 exclude="none" / exclude=[2]
```

---

## 4. C 用法（单表）

```text
lut_phase0_fit.exe in.csv out.csv
lut_phase0_fit.exe in.csv out.csv ma 5
lut_phase0_fit.exe in.csv out.csv ma 5 auto
lut_phase0_fit.exe in.csv out.csv ma 5 none
lut_phase0_fit.exe in.csv out.csv ma 5 2
lut_phase0_fit.exe in.csv out.csv poly 4 4 auto
```

固件可只移植 `lut_phase0_fit_run()` 的 **MA 路径**（`detect_outliers` + `interp_mask` + `moving_average` + unwrap + 过 0 + 重建）。多 LUT 时对每个 `lut_sel` 调一次；`is_master` 仅对 master 置 1。默认 `exclude=AUTO`。

样例 CSV：`dpd/testdata/lut_phase0_fit/sample_lut_raw.csv`

---

## 5. 与训练流程关系

```text
训练 / 读回 → lut_data_map_lut0..K.txt
       ↓
lut_phase0_fit (ma, exclude=auto, scope=all|master_only)
       ↓
写回 dpd_mem_write / itera LUT
```

不替代 RLS/静态训练；只做 **表后处理**。芯片侧无需配置坏点索引。

---

## 6. 参数速查

| 参数 | 默认 | 说明 |
|------|------|------|
| `--method` | `ma` | `ma` / `poly` |
| `--ma-win` | 5 | 奇数窗；越大越钝 |
| `--master-lut` | 无 | `reg_dpd_master_lut` |
| `--scope` | `all` | `all` / `master_only` |
| `--exclude` | `auto` | `auto` / `none` / 逗号索引 |

---

## 7. 例：260825 3lut original_coefficients

目录含 `lut_data_map_lut0/1/2.txt`，`reg_dpd_master_lut=0`。

```powershell
python dpd/lut_phase0_fit.py `
  "D:\test_data\AP\260825_dpd\3lut_multi_frame_training\original_coefficients" `
  -o "...\output\260825\3lut_phase0_ma" `
  --method ma --master-lut 0 --scope all
```

验收：日志形如 `exclude=auto→[2]`（master）；`phase@0≈0°`；master 的 `phase@1≈0°`；原塌陷点被插值后再 MA。
