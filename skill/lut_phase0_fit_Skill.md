# lut_phase0_fit — 多 LUT / Master LUT 相位过 0 修表

对硬件读回的 DPD `lut_data_map` I/Q 做 **坏点修复 + 相位过原点**，尽量**保留训练 AM/PM**，避免全表平滑把 DPD 性能抹掉。

| 文件 | 说明 |
|------|------|
| `dpd/lut_phase0_fit.py` | Python 库 + CLI |
| `dpd/lut_phase0_fit.c` | C 参考（`repair`/`ma`/`poly` + auto exclude） |
| `skill/lut_phase0_fit.skill` | 短摘要 |
| `dpd/testdata/lut_phase0_fit/` | C 用样例 CSV（含 index=2 塌陷） |

---

## 1. 背景与教训

读回表常有低索引坏点（如 index=2 幅度塌陷）。早期默认 **`ma` 全表滑动平均** 会大幅改写整表 I/Q（实测 mean|Δz| 可到数千），板上 **maxerr 明显变差**（例：21→60）。

因此默认改为 **`repair`（DPD-safe）**：只修坏点 + master 全局相位对齐；**不要**默认跑全表 MA/poly。芯片侧应全自动（`exclude=auto`），无需人工指定坏点索引。

---

## 2. 算法

### 2.1 `repair`（默认，推荐上板）

1. \(a_k=|I+jQ|\)，\(\varphi_k=\mathrm{unwrap}\angle(\cdot)\)
2. **`exclude=auto`** 检出坏点 → 仅对这些 bin 做 amp/phase 邻点插值；**好点原样保留**
3. \(z_0\leftarrow 0\)
4. **仅 master**（`force_index1_real`）：整表乘 \(e^{-j\arg(z_1)}\)，再钉 `Q[1]=0`（全局旋转，保相对 AM/PM）
5. **slave 不做独立相位旋转**（否则破坏多 LUT 记忆支路相位一致性）
6. 四舍五入写回定点 I/Q

复杂度 O(N)，适合芯片固件。

### 2.2 自动坏点检测（O(N)）

两侧邻居幅度均 ≥200 才检测（避免 slave 低索引真实 0 误报）；相对邻域均值塌陷/尖峰（+可选相位跳变）则标记。一次标出后统一插值。

| 常量（Py / C 对齐） | 典型值 | 含义 |
|---------------------|--------|------|
| `AUTO_AMP_NEIGH_MIN` | 200 | 两侧邻居最小幅度才检测 |
| `AUTO_AMP_REL_THR` | 0.40 | 相对邻域均值残差门限 |
| `AUTO_AMP_DIP_FACTOR` | 0.60 | 塌陷：低于 `min(邻居)×因子` |
| `AUTO_AMP_SPIKE_FACTOR` | 1.80 | 尖峰：高于 `max(邻居)×因子` |
| `AUTO_PHASE_THR_RAD` | 40° | 相位跳变辅助门限 |

| `--exclude` | 含义 |
|-------------|------|
| `auto`（默认） | 自动检测 |
| `none` | 不剔除 |
| `2` / `2,5` | 人工指定（调试） |

### 2.3 `ma` / `poly`（可选，易伤 EVM）

- `ma`：全表 amp/phase 滑动平均后再重建（调试毛刺用，**默认勿用**）
- `poly`：无常数项加权多项式（PC 离线）

二者同样：**仅 master** 做相位对齐；slave 保持绝对相位。

### 2.4 多 LUT / master

| 参数 | 含义 |
|------|------|
| `--master-lut N` | `reg_dpd_master_lut` |
| `--scope all` | 每组都处理（默认）；slave=只修坏点 |
| `--scope master_only` | 只处理 master；其它 passthrough |

默认额外写出 **`lut_data_map_lutN.txt`**（与读回同名，便于写回硬件）。`--no-hw-names` 可关。

---

## 3. Python 用法

```powershell
cd D:\users\gxu\scripts

# 推荐：DPD 保真 repair（默认 method）
python dpd/lut_phase0_fit.py `
  "D:\test_data\AP\260825_dpd\3lut_multi_frame_training\original_coefficients" `
  -o "D:\test_data\AP\260825_dpd\3lut_multi_frame_training\fit_coefficients" `
  --master-lut 0 --scope all

# 显式
python dpd/lut_phase0_fit.py DIR -o OUT --method repair --master-lut 0 --scope all

# 仅当确认需要更强平滑时
python dpd/lut_phase0_fit.py DIR -o OUT --method ma --ma-win 5 --master-lut 0
```

产物：

- `lut_data_map_lutN.txt`（HW 写回）
- `lut_data_map_lutN_phase0_repair.txt` / `.csv` / `.png`
- `lut_data_map_all_phase0_repair.txt`

### API

```python
from dpd.lut_phase0_fit import run_multi, fit_lut_phase0, detect_lut_outliers

run_multi(r"D:\path\to\maps", r"D:\out", method="repair", master_lut=0, scope="all")
```

---

## 4. C 用法（单表）

```text
lut_phase0_fit.exe in.csv out.csv
lut_phase0_fit.exe in.csv out.csv repair
lut_phase0_fit.exe in.csv out.csv repair auto
lut_phase0_fit.exe in.csv out.csv ma 5 auto
```

固件移植 `lut_phase0_fit_run()` 的 **repair** 路径；多 LUT 时 master 置 `is_master=1`，slave 置 0。

---

## 5. 流程

```text
训练 / 读回 → original_coefficients/lut_data_map_lut*.txt
       ↓
lut_phase0_fit --method repair --master-lut N --scope all
       ↓
fit_coefficients/lut_data_map_lut*.txt → dpd_mem_write
```

不替代 RLS/静态训练；只做表后处理。

---

## 6. 参数速查

| 参数 | 默认 | 说明 |
|------|------|------|
| `--method` | `repair` | `repair` / `ma` / `poly` |
| `--ma-win` | 5 | 仅 `ma` |
| `--master-lut` | 无 | master 索引 |
| `--scope` | `all` | `all` / `master_only` |
| `--exclude` | `auto` | 自动坏点 |
| `--no-hw-names` | off | 不写同名 HW 文件 |

---

## 7. 例：260825 3lut

`original_coefficients` → `fit_coefficients`：

- lut0：`auto→[2]`，修塌陷 + master 相位对齐（若 index1 已为实部则旋转角≈0）
- lut1/2：无坏点则 **I/Q 不变**（保记忆相位）

验收：相对原表畸变应远小于 `ma`；板上 EVM/maxerr 应接近原训练表，且 index2 不再塌陷。

---

## 8. 变更说明（Changelog）

### 8.1 自动坏点（替代硬编码 `--exclude 2`）

**动机**：坏点位置不固定；芯片软件必须按当前 LUT 自检，不能依赖人工配置。

**改动**：

- 新增 `detect_lut_outliers` / C `lut_phase0_detect_outliers`（邻域均值塌陷/尖峰，O(N)）
- CLI/API 默认 `--exclude auto`；仍支持 `none` 与逗号索引调试
- 日志/头注释输出 `exclude_mode` 与实际检出索引（如 `auto→[2]`）

### 8.2 默认方法改为 `repair`（DPD 保真）

**动机**：默认 `ma` 全表平滑重写训练 AM/PM，板上 maxerr 恶化（例 21→60）；mean|Δz| 可达数千。

**改动**：

| 项 | 旧行为 | 新行为 |
|----|--------|--------|
| 默认 `--method` | `ma` | **`repair`** |
| 好点 I/Q | 被 MA/poly 改写 | **原样保留** |
| 坏点 | 插值后仍进全表 MA | 仅插值替换 |
| master 相位 | MA 后再减 `φ(0)` / 钉 Q1 | 全局乘 \(e^{-j\arg(z_1)}\)，钉 Q1 |
| slave 相位 | 各自对齐（破坏记忆相干） | **不旋转**，只修坏点 |
| 输出 | 仅 `*_phase0_ma.txt` | 额外 **`lut_data_map_lutN.txt`**（HW 同名） |

**保留**：`--method ma|poly` 供离线/调试；文档明确易伤 EVM。

### 8.3 相关提交

- `ea86095` — Auto-detect LUT bad bins（`exclude=auto`）
- `a3a7d21` — Default to DPD-safe `repair`（非全表 MA）
- 本文档 + `CLAUDE.md` 索引 — 汇总用法与设计约束
