# mag_track_rls4_fpga_analyse.py — RLS4.0 FPGA 磁跟踪回归 CSV 曲线分析

## 环境与脚本分工（必读）

| 场景 | 脚本 | 说明 |
|------|------|------|
| **RLS4.0 FPGA** | `mag_track_rls4_fpga_analyse.py` | 有 FPGA-on 的 mag 元组出页；同图叠 **`tx_mag_track_on=0`** 基线（**同 chan** 聚合全部 dly/mag）与 **FPGA-on** 严格曲线 |
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

### 4b. 同一张图：FPGA magtrack on 与 tx_mag_track_on=0 对比

- **出页条件**：仅在某个 **完整分面元组**（默认含 `chan,dly,start_point,...`）下存在 **`tx_mag_track_on=1`** 的数据时，生成一页 PDF（不再为「仅有 FPGA off 且同元组」单独出页）。
- **`tx_mag_track_on=1` 的 `(1,0)`、`(1,1)`**：使用 **当前分面 mag 元组**（与 `start_point`、`win_len` 等一致）在 **`tx_pwr`** 上的 EVM 曲线。
- **`tx_mag_track_on=0` 的 `(0,0)`、`(0,1)`**：**仅按 `chan`（及 `amplitude`）** 从全表聚合：在相同 **`tx_pwr`** 上对 **所有 `dly` 与 mag 参数** 的 EVM 取 **均值** 后画两条基线（避免 FPGA 分面里 `dly=52` 而 `tx_mag_track_on=0` 只在 `dly=0` 时无数据、图线消失）。图例带说明。
- 若某 `chan` 下缺少用于基线的 `tx_mag_track_on=0` 且对应 `amplitude` 的数据，会记入 **`*_rls4_magtrk_plot_warnings.txt`**（若有）。

### 5. 默认分面键（`GROUP_COLS`）
一页对应唯一元组：

`chan`, `dly`, `start_point`, `win_len`, `chn_len`, `chn_ofst`, `start_mode`

可在源码 `CONFIG["GROUP_COLS"]` 或命令行 **`--group-cols`**（逗号分隔、无空格或自行 strip）中调整，例如需要把 `rx_dc_en` 也拆开时加入列表。

---

## 聚合规则
对原始行先按  
`(分面列..., tx_pwr, tx_mag_track_on, amplitude)`  
分组，对 **`evm`** 取 **均值**（同一分面键、同一功率点、同一开关组合若多行则合并）。

**作图时**：`tx_mag_track_on=0` 的两条基线在 **`chan` + `tx_pwr` + `amplitude`** 上聚合（对 **全部 `dly` 与其它 mag 列** 取均值）；`tx_mag_track_on=1` 仍使用完整分面键。

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

输出：`<basename>_rls4_magtrk.pdf`、`<basename>_load_diag.txt`；若某 `chan` 缺少某种 `amplitude` 的 `tx_mag_track_on=0` 基线数据，另见 **`*_rls4_magtrk_plot_warnings.txt`**（与 PDF 同前缀）。

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
- `tx_mag_track_on=0` 基线改为 **仅同 `chan`** 聚合（含全部 `dly`/mag），保证每张 FPGA-on 图均有对比线；避免 `dly` 与 FPGA 分面不一致导致空曲线。
