# mag_track_rls4_fpga_analyse.py — RLS4.0 FPGA 磁跟踪回归 CSV 曲线分析

## 环境与脚本分工（必读）

| 场景 | 脚本 | 说明 |
|------|------|------|
| **RLS4.0 FPGA** | `mag_track_rls4_fpga_analyse.py` | `mag_track_test_res_*.csv`；横轴 **`tx_pwr`**；**`chan` / `dly`** 分面；含 FPGA-on 时强制先画 **magtrack off** 与 **magtrack on (Instruments)** 再画 FPGA-on |
| **E22 芯片** | `txmagtrk_analyse.py` | 见 `skill/txmagtrk_analyse_Skill.md`；`test_power`、`trk_en` 等 |

若需 **汇总表 / HTML / 柱状图**，用 `analyze_mag_track_test_res.py`。

---

## 作图逻辑（按需求固定）

### 1. 横坐标
- **默认且推荐**：**`tx_pwr`**（发射功率设定，dBm），作为 X 轴扫描量。  
- 可用 `--x-column COL` 覆盖（一般不需要）。

### 2. `dly` 作为 mag 参数、同图比较范围
- **`dly` 相同** 的数据画在 **同一张图** 里（与同一 `chan`、同一组其它 mag 参数一起，见下）。  
- 即：`dly` 在 **分面键（panel keys）** 中：换 `dly` → 新一页 PDF。

### 3. `chan` 分开比较
- **`chan` 不同** → **不同 PDF 页**（不同分面，不与其它信道混在同图）。

### 4. 四种开关组合与图例含义

| `tx_mag_track_on` | `amplitude` | 含义（图例） |
|-------------------|---------------|--------------|
| 0 | 0 | **magtrack off**（FPGA off，仪表幅度 off） |
| 0 | 1 | **magtrack on (Instruments)**（FPGA off，`amplitude=1`） |
| 1 | 0 | FPGA magtrack on，仪表幅度 off |
| 1 | 1 | FPGA magtrack on + 仪表幅度 on |

### 4b. 含 FPGA magtrack on 的图：强制对比基线

当该分面内存在 **`tx_mag_track_on=1`** 的数据时（图中会出现 FPGA magtrack on 曲线）：

1. **先绘制**两条对比基线：**magtrack off** `(0,0)`、**magtrack on (Instruments)** `(0,1)`。  
2. **再绘制** FPGA magtrack on：`(1,0)`、`(1,1)`。  
   基线略加粗、`zorder` 较低；FPGA-on 曲线在上层。

若当前 **mag 元组分面** 下缺少 `(0,0)` 或 `(0,1)` 点，脚本会用 **同一 `chan`、同一 `dly`** 下、其它 mag 元组在相同 **`tx_pwr`** 上的 **EVM 均值** 生成 **fallback 参考线**（图例后缀 `[ref: mean over mag params, same chan & dly]`）。启用 fallback 时写入 **`*_rls4_magtrk_plot_warnings.txt`**（截断记录）。

**仅含 FPGA off**（无任何 `tx_mag_track_on=1`）的分面：按数据中实际存在的组合绘制，不套用上述 fallback。

若某组合在当前分面（且无可用 fallback）下仍无数据，则该条曲线跳过。

### 5. 默认分面键（`GROUP_COLS`）
一页对应唯一元组：

`chan`, `dly`, `start_point`, `win_len`, `chn_len`, `chn_ofst`, `start_mode`

可在源码 `CONFIG["GROUP_COLS"]` 或命令行 **`--group-cols`**（逗号分隔、无空格或自行 strip）中调整，例如需要把 `rx_dc_en` 也拆开时加入列表。

---

## 聚合规则
对原始行先按  
`(分面列..., tx_pwr, tx_mag_track_on, amplitude)`  
分组，对 **`evm`** 取 **均值**（同一分面、同一功率点、同一开关组合若多行则合并）。

---

## 命令行

```bash
python mag_track_rls4_fpga_analyse.py [INPUT] -o OUT_DIR [选项]
```

| 参数 | 说明 |
|------|------|
| `INPUT` | 单 CSV 或目录 |
| `-o`, `--out-dir` | 输出目录 |
| `--encoding` | 传给 `load_mag_track_csv` |
| `--x-column` | 横轴列，默认 **`tx_pwr`** |
| `--group-cols` | 分面列，逗号分隔；默认 `chan,dly,start_point,win_len,chn_len,chn_ofst,start_mode` |
| `--no-evm-infer` | 禁止 EVM 列启发式推断 |
| `-r`, `--recursive` | 目录输入时递归子目录 |

输出：`<basename>_rls4_magtrk.pdf`、`<basename>_load_diag.txt`；若发生参考线 fallback，另见 `<basename>_rls4_magtrk_plot_warnings.txt`。

---

## 数据与读入
- 行尾多余 `,` 由 `analyze_mag_track_test_res` 预处理，避免列错位。  
- **`pwr`** 为功率读数，勿与 **`evm`** 混淆；EVM 推断逻辑已排除 `pwr` 等列。

---

## 依赖
`pandas`, `numpy`, `matplotlib`，以及同目录 `analyze_mag_track_test_res.py`。

---

## 与 txmagtrk_analyse.py 的对应（更新）

| txmagtrk（E22） | 本脚本（RLS4 FPGA） |
|-----------------|---------------------|
| `test_power` | **`tx_pwr`**（横轴） |
| `trk_en` + `amplitude` 四象限曲线 | **`tx_mag_track_on` + `amplitude`** 四象限曲线 |
| 五参数分面 | **`chan` + `dly` + start_point/win_len/chn_len/chn_ofst/start_mode** 分面 |

---

## 版本说明
- 含 FPGA magtrack on 的分面：强制先画 **magtrack off** 与 **magtrack on (Instruments)**，再画 FPGA-on；缺数据时支持 **chan+dly** 聚合 fallback 与 `*_plot_warnings.txt`。
