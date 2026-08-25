# lut_phase0_fit — 多 LUT / Master LUT 相位过 0 修表

对硬件读回的 DPD `lut_data_map` I/Q 做 **坏点修复 + 平滑 + 相位过原点**。目标：曲线更光滑，同时限制对训练 AM/PM 的改写，争取相对原表提升 DPD。

| 文件 | 说明 |
|------|------|
| `dpd/lut_phase0_fit.py` | Python 库 + CLI |
| `dpd/lut_phase0_fit.c` | C 参考（与 Py 对齐演进中） |
| `skill/lut_phase0_fit.skill` | 短摘要 |
| `dpd/testdata/lut_phase0_fit/` | 样例 CSV（含 index=2 塌陷） |

---

## 1. 背景与教训

| 路径 | 现象 |
|------|------|
| 全表 `ma`/`poly` | 曲线很光滑，但 mean\|Δz\| 大，板上 maxerr 恶化（例 21→60） |
| 仅 `repair` | 保真好，但曲线仍毛刺多，相对原表几乎不提升 |
| **`smooth`（默认）** | 坏点修复 + **混合 MA**（相位多、幅度少）+ **amp 偏差钳位** |

芯片侧：`exclude=auto`，无需人工指定坏点索引。

---

## 2. 算法

### 2.1 `smooth`（默认，推荐上板）

1. 自动坏点 → amp/phase 邻点插值得 \(a_w,\varphi_w\)
2. 对 \(a_w,\varphi_w\) 做 MA（默认窗 5）得 \(a_s,\varphi_s\)
3. 混合：\(a=(1-m_a)a_w+m_a a_s\)，\(\varphi=(1-m_\varphi)\varphi_w+m_\varphi\varphi_s\)
   - master 默认 \(m_a=0.50,\ m_\varphi=0.80\)
   - slave 默认 \(m_a=0.35,\ m_\varphi=0.65\)（更保守，保记忆支路）
4. **amp 钳位**：相对 \(a_w\) 的相对偏差不超过 `--max-amp-dev`（默认 0.10）
5. **仅 master** 全局相位对齐到 index1 实部；并**保留 master index1 幅度**（HW 增益锚点，不被 MA 拉偏）；slave 不旋相位
6. 定点写回；并写出 HW 同名 `lut_data_map_lutN.txt`

### 2.2 `repair`

只修坏点 + master 相位对齐；好点原样。光滑度不足时用 `smooth`。

### 2.3 `ma` / `poly` / `iqpoly`

- `ma`：全表 amp/phase MA（易伤 EVM）
- `poly`：amp/phase 无常数项加权多项式
- `iqpoly`：I/Q 过原点多项式（对齐 MATLAB `polyfit_for_lut`；适合 master 离线）

### 2.4 自动坏点（O(N)）

两侧邻居幅度 ≥200 才检测；塌陷/尖峰（+可选相位跳变）。阈值：`AUTO_AMP_*`。

---

## 3. Python 用法

```powershell
cd D:\users\gxu\scripts

# 推荐：默认 smooth
python dpd/lut_phase0_fit.py `
  "D:\test_data\AP\260825_dpd\3lut_multi_frame_training\original_coefficients" `
  -o "D:\test_data\AP\260825_dpd\3lut_multi_frame_training\fit_coefficients" `
  --master-lut 0 --scope all

# 更光滑（略增改写）
python dpd/lut_phase0_fit.py DIR -o OUT --method smooth --mix-amp 0.6 --mix-ph 0.9 --max-amp-dev 0.12

# 更保真
python dpd/lut_phase0_fit.py DIR -o OUT --method smooth --mix-amp 0.35 --mix-ph 0.7 --max-amp-dev 0.08
python dpd/lut_phase0_fit.py DIR -o OUT --method repair --master-lut 0
```

产物：`lut_data_map_lutN.txt`（HW）、`*_phase0_smooth.txt/.csv/.png`、`lut_data_map_all_phase0_smooth.txt`

---

## 4. 参数速查

| 参数 | 默认 | 说明 |
|------|------|------|
| `--method` | `smooth` | `smooth`/`repair`/`ma`/`poly`/`iqpoly` |
| `--ma-win` | 5 | MA 窗（`smooth`/`ma`） |
| `--mix-amp` | master 0.50 / slave 0.35 | amp 向 MA 混合比 |
| `--mix-ph` | master 0.80 / slave 0.65 | phase 向 MA 混合比 |
| `--max-amp-dev` | 0.10 | amp 相对 repaired 最大偏差 |
| `--exclude` | `auto` | 自动坏点 |
| `--master-lut` / `--scope` | — / `all` | 多 LUT |

---

## 5. 例：260825 3lut（smooth）

相对原表（约）：

| LUT | amp 二阶粗糙度 | phase 二阶粗糙度 | amp 相关 |
|-----|----------------|------------------|----------|
| lut0 | 3083→~1230 | 22°→~0.5° | ~0.9997 |
| lut1/2 | 下降 | 相位毛刺明显下降 | >0.99 |

写回 `fit_coefficients\lut_data_map_lut*.txt` 后上板对比 EVM/maxerr。

---

## 6. 变更说明（摘要）

1. `exclude=auto` — 取消硬编码 `--exclude 2`
2. `repair` — 全表 MA 伤性能后的保真路径（光滑不足）
3. **`smooth` 默认** — 坏点 + 混合 MA（相位>幅度）+ amp 钳位 + master 保 index1 幅度；slave 更保守、不旋相位
4. 备选 `iqpoly` — MATLAB `polyfit_for_lut` 风格 I/Q 过原点多项式（离线）
