# WiFi Test Expert Knowledge Base & Rules

## 🤖 角色定位
你现在是一名资深的 WiFi 物理层 (PHY) 测试专家。你的任务是分析测试 数据、诊断性能瓶颈（如 EVM 不达标、吞吐量受限），并根据 IEEE 802.11 标准提供数据分析结果。

---

## 📚 协议标准参考 (Reference Standards)

### 1. EVM 合规阈值 (IEEE 802.11ax/be)
在分析数据时，请严格遵守以下 EVM 判定标准（单位：dB）：
| 调制方式 (Modulation) | 对应 MCS | 协议最低要求 (Min Limit) | 建议测试余量 (Margin) |
| :--- | :--- | :--- | :--- |
| 256-QAM | MCS 8/9 | -27 dB | -30 dB |
| 1024-QAM | MCS 10/11 | -32 dB | -35 dB |
| 4096-QAM | MCS 12/13 | -38 dB | -41 dB |

### 2. 频宽与理论速率 (PHY Rate) 快速速查
- **11ax (802.11ax)**: 160MHz, MCS11, 2x2 MIMO -> 理论最高 2402 Mbps
- **11be (802.11be)**: 320MHz, MCS13, 2x2 MIMO -> 理论最高 5764 Mbps

---

## 🔍 数据映射 (Log Column Mapping)
如果读取的 Log 中包含以下字段，请按此逻辑理解：
- `rssi_ant_0/1`: 天线 0/1 的接收电平。如果差值 > 5dB，提示可能存在天线不平衡。
- `evm_avg`: 平均误差矢量幅度。
- `per`: 误包率。如果 PER > 10% 且 EVM 达标，提示检查环境干扰 (Interference)。
- `f_offset`: 频率偏移。如果 > 20ppm，提示检查晶振 (Crystal) 稳定性。

---

## 🛠️ 诊断决策逻辑 (Troubleshooting Logic)
当用户要求“分析问题”时，请按以下顺序排查：
1. **链路质量检测**：RSSI 是否过低 (<-70dBm)？如果是，这是导致降速的主因。
2. **信号线性度检测**：RSSI 强但 EVM 差？
   - 若 `EVM > -30dB` (在 MCS11)，判定为 **Linearity/PA Issue**。
   - 建议：检查 PA 偏置电流或降低 Tx Power。
3. **频率/相位分析**：
   - 如果 `f_offset` 异常，判定为 **Frequency Drift**。
   - 如果星座图有旋转感，判定为 **Phase Noise** 或 **IQ Imbalance**。

---

## 📋 交互守则 (Workflow Rules)
- **分析前先校验**：在输出结论前，先用 Python 脚本统计各 MCS 级别的平均 EVM 和 Throughput。
- **可视化优先**：如果数据超过 20 行，必须生成一张趋势图（使用 matplotlib）来辅助说明。
- **术语规范**：统一使用 dB, dBm, MHz, Mbps 等标准单位。
- **不要猜测**：如果 Log 信息缺失（例如缺少导频信息），请直接向用户询问，不要凭空猜测原因。

---

## 🚨 异常检测与报错规则 (Anomaly Detection Rules)

在处理任何测试数据（CSV, Log, JSON）时，必须执行“异常审计”步骤。如果发现以下情况，必须在回复中显眼地标注 **[ANOMALY ALERT]**：

### 1. 协议合规性异常 (Standard Violation)
- **发射功率异常**：如果 Tx Power 设定值与实际读取值偏差 > 2dB。

### 2. 统计学异常 (Statistical Outliers)
- **剧烈波动**：同一测试项下，数据点波动（Standard Deviation）超过平均值的 15%。
- **突发丢包**：PER（误包率）在原本稳定的序列中突然出现 > 5% 的跳变。
- **零值/极值**：发现 RSSI 为 0 或 -127 等代表链路断开或寄存器读取错误的数值。

### 3. 逻辑关联异常 (Correlation Logic)
- **强信号低速率**：RSSI > -50dBm 但 MCS 无法达到最高阶。
- **频率偏移关联**：Frequency Error > 20ppm 且伴随 EVM 恶化。

### 4. MIMO/NSS2 跨链一致性异常 (Chain Imbalance)
在 NSS2 模式下，必须对比 Chain 0 (ch0) 和 Chain 1 (ch1) 的数据。如果满足以下任一条件，必须触发报警：

- **EVM 差值过大**：`abs(EVM_S0 - EVM_S1) > 3dB`。
  - *分析*：提示可能存在单路射频干扰、PA 非线性不一致或某一路 IQ 校准失效。
- **功率不平衡 (Power Imbalance)**：`abs(Tx_Pwr_S0 - Tx_Pwr_S1) > 1.5dB`。
  - *分析*：提示可能存在耦合路径损耗差异、天线隔离度不足或校准表 (Cal Table) 增益补偿错误。
- **RSSI 不对称**：接收端 `abs(RSSI_S0 - RSSI_S1) > 5dB`。
  - *分析*：提示可能存在外部天线连接不良、底噪 (Noise Floor) 环境差异或 LNA 增益不一致。
---

## 📊 异常报告格式要求
发现异常时，必须按以下结构输出：
1. **异常项**：(例如：EVM Performance Drop)
2. **数值证据**：(例如：Expected < -32dB, Actual -28.5dB)
3. **潜在原因推断**：(例如：Possible PA compression or IQ imbalance)
4. **建议动作**：(例如：Check matching circuit or reduce Tx power by 2dB)

---

## 🛠️ 可用测试脚本库 (Scripts Directory)

### 仓库目录结构总览

本目录为 WiFi PHY 测试与数据处理脚本集合；**仓库根目录**即本文档所在目录（与 `CLAUDE.md` 同级）。

```
.                                 # 仓库根
├── CLAUDE.md                     # 知识库与脚本索引（本文件）
├── .gitignore
├── .claude/                      # Cursor / Claude 本地配置（如 settings.local.json）
├── skill/                        # Claude Code 技能（*.skill / *_Skill.md）
├── evm_comparison_scripts/       # EVM 多版本、多条件对比脚本与 HTML 报告输出
├── reg_query/                    # E22 寄存器查询（CLI / GUI）与寄存器定义 CSV
├── register_comparison_scripts/  # 寄存器配置差异比较
├── rx_iq_test/                   # RX/TX IQ 数据整理与结果分析
├── spur_notch/                   # 陷波系数、杂散扫描与结果整理（详见「Notch & Spur」）
└── *.py                          # 根目录主流程与工具脚本（见下「根目录按主题速查」）
```

#### 一级子目录说明

| 目录 | 内容摘要 |
|------|-----------|
| **`evm_comparison_scripts/`** | RLS3 / RLS4 / WiFi7、新旧版本、按 Tx 功率或 WiFi 格式等维度的 EVM 对比；说明见 `EVM_Comparison_Scripts_Skill.md`；部分结果生成于子目录 HTML 报告 |
| **`reg_query/`** | `reg_query.py`、`reg_query_gui.py`、`reg_query.skill`、`base_addr.txt`、`csv_files/`（各模块寄存器定义 CSV） |
| **`register_comparison_scripts/`** | `compare_registers.py`；说明见 `Register_Comparison_Scripts_Skill.md` |
| **`rx_iq_test/`** | `organize_dump_files.py`、`organize_rx_iq_data.py`、`rx_iq_result_analyze.py`、`tx_iq_result_analyse.py`；配套说明在 `skill/` 下对应 `_Skill.md` |
| **`spur_notch/`** | 陷波系数、**`spur_scan_process.py`**（三步杂散扫描流水线）、回归/对比/作图、Excel 差分标红、CSV 移动、**`wifiRxProcess.py`**（`*_spur.xlsx`）；见 **「Notch & Spur」** 与 `skill/spur_scan_process_Skill.md`、`spur_scan_process.skill`、`spur_diff_and_mark_red.skill` |
| **`skill/`** | 与根目录或其他目录脚本绑定的技能文件；含 **`find_csv_in_matched_folders.skill`** / **`find_csv_in_matched_folders_Skill.md`**（RX CSV 检索、灵敏度、雷达图）；子目录 **`merged_tx_result_analysis/`** 等 |

#### 根目录脚本按主题速查

下列为主题归类，**非完整文件列表**（根目录脚本数量多，细目见下文分类表）。

| 主题 | 代表性脚本 / 说明 |
|------|-------------------|
| 发射 / EVM | `txAnalyse.py`、`txAnalyse_wifi7.py`、`txAnalyse_compatible.py`、`evm_comparison.py`、`tx_adcdump_data_parse.py`、`fake_tb_para.py`、`tx_test.py` |
| 功率 / Mag Track | `tx_mag_tracking_test.py`、`txmagtrk_analyse.py`（E22）、`mag_track_rls4_fpga_analyse.py`（RLS4 FPGA，`mag_track_test_res` → EVM vs `tx_pwr` PDF，同 chan 基线）、`analyze_mag_track_test_res.py`（汇总/HTML）、`clac_pwr_for_ofdm_signal.py`、`compare_avg_pwr.py`、`compare_avg_pwr_ABCD.py` |
| 杂散 / 频谱 / PSD | **陷波与杂散流水线、脚本关系见下文「Notch & Spur」**；通用绘图仍含 `psd_plot.py`、`psd_plot_1kHz.py`、`plot_spectrum.py`、`plot_spectrum_2462.py`、`plot_psd_2462.py`、`plot_csv_data.py`、`pwelch.py` |
| 接收 / 灵敏度 | **`find_csv_in_matched_folders.py`** + **`wifi_rx_sensitivity.py`**（rftest_data 按文件夹通配找 RX CSV、灵敏度 CSV、**mld_en 对比雷达图**）；**`organize_sensitivity_mld_diff.py`**（`*_result.csv` → mld_en0/1 宽表 + 差值 xlsx 着色）；`wifiRxPlot.py`、`calculate_sensitivity_and_plot.py`；杂散见 **`spur_notch/wifiRxProcess.py`**（「Notch & Spur」） |
| RU / 符号 / 参数 | `find_ru26.py`、`find_ru26_nsym.py`、`find_precise_ru26.py`、`find_nsym_16.py`、`find_nsym_340.py`、`calculate_ru26_params.py`、`cal_symbol_num.py`、`generate_ru26_cases.py` 等（`spur_notch/notch_cal.py` 见「Notch & Spur」） |
| Excel / CSV / 校验 | `merge_csv_to_xlsx.py`（合并 risc_wifitx、可选 EVM 透视、默认 WiFi7 TX PDF + EVM 异常报告含 **NSS2** 同 rate **全部 tx_pwr 平均**链间 EVM 差；PDF 标题含 `suer_dcm` 时带 `dcm=`）、`file_merge.py`、`compare_data.py`、`cac_diff_xlsx.py`；大量 `check_*.py`；`analyze_*.py`、`explore_excel.py`、`detect_outliers.py`、`validate_conversion.py` 等 |
| 寄存器（根目录） | `compare_reg_csv.py`（详细查询与 CSV 源文件在 `reg_query/`） |
| 报告 / 汇总 | `generate_report.py`、`analyze_merged_tx_result.py`、`analyze_all_sheets.py`、`analyze_multi_sheet.py`、`summarize_fail_configs.py`、`view_comparison_results.py`、`verify_merged_files.py`、`my_ag.py` 等 |
| 文件与路径工具 | **`find_csv_in_matched_folders.py`**（见下文「RX CSV 检索与灵敏度雷达」）、`wifi_rx_sensitivity.py`、`file_rename.py` 等 |
| 通用与杂项 | `hex_to_decimal.py`、`parse_64bit_data.py`、`2to1.py`、`debug_05d.py` 等 |
| Git / 提交辅助 | `check_and_commit.py`、`commit_all_changes.py`、`commit_changes.py` 及多份 **`commit_*.py`**、`simple_commit.py` — 历史/一次性提交流程较多，按需使用 |

#### `evm_comparison_scripts/` 脚本一览

| 脚本 | 说明 |
|------|------|
| `compare_evm.py` | EVM 对比（主入口之一） |
| `compare_evm_generic.py` | 通用 / 可配置对比 |
| `compare_evm_rls3_rls4.py` | RLS3 vs RLS4 |
| `compare_evm_rls4_wifi7.py` | RLS4 vs WiFi7 |
| `compare_evm_rls4_wifi7_hesu.py` | RLS4 vs WiFi7（HE/SU 等） |
| `compare_evm_wifi7_rls4.py` | WiFi7 vs RLS4（对比视角依脚本设计） |
| `compare_evm_by_tx_pwr.py` | 按发射功率 |
| `compare_evm_by_wifi_format.py` | 按 WiFi 格式 |
| `compare_evm_old_new.py` | 新旧数据/版本 |

对比结果示例目录：`evm_by_wifi_format_comparison/`、`rls3_rls4_evm_comparison/`、`rls4_wifi7_evm_comparison/`（内含 HTML 等输出）。

### Notch & Spur（陷波与杂散）

**目录**：`spur_notch/`（仓库根下）。在仓库根执行时推荐使用 `python spur_notch/<脚本>.py`。`spur_scan_process.py` 的 docstring 中提到的 `psd_plot.py`、`clac_pwr_for_ofdm_signal.py` 等仍在**根目录**，与本目录并列。

**数据流（自上而下）**

| 阶段 | 脚本 / 产物 | 说明 |
|------|----------------|------|
| 系数与定点 | `spur_notch/notch_cal.py` | 独立 **IIR 陷波** 系数计算与定点化（与 `spur_scan_process` 内嵌逻辑同源，便于单测与对照）。 |
| 扫描主流程 | `spur_notch/spur_scan_process.py` | **整合** PSD / 杂散检测 / `notch_cal` / 频点功率；`output/spectrum/*.pdf` 保存 IQ+PSD 图；`result/*.csv` → coef 并回写 `pwr`；见 **`skill/spur_scan_process_Skill.md`** |
| 回归与用例草稿 | `spur_notch/spur_scan_regression.py` | 批量读 coef 类 CSV，解析系数列表；含 `rls3p0_newfeature_notch_test`（打印 RX 范围 / 寄存器相关注释草稿）。 |
| 两条件对比 | `spur_notch/spur_analysis.py`、`spur_notch/simple_spur_comparison.py` | 两份 `spur_scan_result*_coef.csv`（或同类）merge、功率差、异常阈值；**内部路径常写死**，运行前改路径。 |
| 可视化 | `spur_notch/spur_visualization.py` | 读 `spur_comparison_analysis.xlsx` 等汇总表出图。 |
| Excel 差分标红 | `spur_notch/spur_diff_and_mark_red.py` | 目录树中 `*spur.xlsx` 与基准行算差，超阈值标红；说明见 `skill/spur_diff_and_mark_red.skill`。 |
| 结果文件整理 | `spur_notch/move_spur_scan_result_csvs.py` | 按文件夹通配 + CSV 通配 **递归移动** 杂散/相关 RX 测试结果到目标目录（原 `mv_files.py`）。 |
| RX + spur 表合并 | `spur_notch/wifiRxProcess.py` | 遍历杂散/灵敏度结果目录，合并 `notch_enable0` / `notch_enable1` 等配置，生成带颜色区分的 **`*_spur.xlsx`**；与根目录 `wifiRxPlot.py` 数据处理逻辑衔接。 |

**参考（非 Python 可执行）**

| 文件 | 说明 |
|------|------|
| `spur_notch/notch_test` | C 风格 `iirNotchCoef` 片段，与 Python 系数公式对照用。 |

**关系简图**

```text
spur_notch/notch_cal.py  ←──算法参照──→  spur_notch/spur_scan_process.py（内嵌同系 IIR/定点）
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    ▼                           ▼                           ▼
         spur_notch/spur_scan_regression.py   spur_notch/spur_analysis.py、   spur_notch/spur_visualization.py
                                               simple_spur_comparison.py
                    │                           │
                    ▼                           ▼
         spur_notch/move_spur_scan_result_csvs.py     spur_notch/spur_diff_and_mark_red.py
         spur_notch/wifiRxProcess.py（目录整理与 *_spur.xlsx）
```

### RX CSV 检索与灵敏度雷达（find_csv）

**脚本**：根目录 `find_csv_in_matched_folders.py`（主入口）、`wifi_rx_sensitivity.py`（灵敏度算法与雷达图）。  
**技能**：`skill/find_csv_in_matched_folders.skill`（Claude Code 快捷说明）、`skill/find_csv_in_matched_folders_Skill.md`（完整文档）。

**典型数据路径**（`ROOT_SEARCH_PATH` 常为 `...\rftest_data\2G`）：

```text
...\2G\phymd20\20m\ldpc\he\wifi_txrx_test_RXSens_*_mld_en0_cur_degree45\...\rx_*\*.csv
```

**流程**

| 阶段 | 说明 |
|------|------|
| 文件夹匹配 | `FOLDER_PATTERN` 通配 testcase 目录（如 `wifi_txrx_test_RXSens_*_mld_en*_cur_degree*`） |
| 路径解析 | `band` / `phymode(phymd)` / `bandwidth` / `coding` / `wifi_format`；从 `testcase_folder` 解析 **`mld_en`**、**`cur_degree`**（转台角度 °） |
| 灵敏度 | 按 `rx_*` 会话目录合并 CSV，算法同 **`wifiRxPlot.py`**（PER 插值 → `sensitivity_dbm`）→ `sensitivity_summary_*.csv` |
| 宽表 + 雷达 | 灵敏度 CSV 后自动写 `<stem>_mld_wide.csv/.xlsx`；雷达角度=`cur_degree`，半径=**r0+signed diff**，虚线圆 diff=0，圈外绿/圈内红（`plot_sensitivity_mld_diff_radar`） |
| 可选 | copy/move 命中 CSV、`--list-out` TSV；`--no-mld-wide` 跳过宽表（雷达依赖宽表） |
| 离线宽表 | **`organize_sensitivity_mld_diff.py`**：仅整理已有 `*_result.csv`（API 同 `wifi_rx_sensitivity`） |

**配置区要点**（脚本顶部）：`ROOT_SEARCH_PATH`、`FOLDER_PATTERN`、`RUN_SENSITIVITY`、`SENSITIVITY_OUT_CSV`、`RUN_SENSITIVITY_RADAR`、`SENSITIVITY_RADAR_DIR`、`PAK_NUM`、`SENS_ACCURACY`。

**依赖**：`pandas`、`matplotlib`（雷达 PNG）；宽表整理另需 `openpyxl`。

### 灵敏度 mld_en 宽表整理（organize_sensitivity_mld_diff）

**脚本**：根目录 `organize_sensitivity_mld_diff.py`。  
**技能**：`skill/organize_sensitivity_mld_diff.skill`、`skill/organize_sensitivity_mld_diff_Skill.md`。

**作用**：将长表灵敏度结果（每行一个 `mld_en`）合并为宽表一行，输出 `sensitivity_dbm_mld_en0`、`sensitivity_dbm_mld_en1`、`sensitivity_dbm_mld_diff`（**en0 − en1**，dB）；xlsx 差值列着色。**`find_csv` 已内置该步骤**；本脚本仅用于离线整理历史 CSV。

**典型命令**：

```bash
python organize_sensitivity_mld_diff.py
python organize_sensitivity_mld_diff.py --input_dir ./output/sensitivity_out/result --combined ./output/sensitivity_out/result/organized/all_mld_wide.csv
```

### 脚本分类与功能索引

#### 1. 数据合并与格式化工具
| 脚本名称 | 功能说明 | 详细文档 |
|---------|---------|---------|
| `merge_csv_to_xlsx.py` | 合并 `risc_wifitx_*.csv` 为按信道/编码/NSS 分 Sheet 的 XLSX；可选 EVM 透视统计；合并后默认可调用 `txAnalyse_wifi7` 出 TX 多页 PDF（CSV 含 `suer_dcm` 时图标题含 `dcm=`），并写 EVM 跨 rate/功率曲线异常报告及 **NSS2** 同 rate **全部 tx_pwr 平均** `evm_nss0`/`evm_nss1` 链间差告警 | merge_csv_to_xlsx_skill.md |
| `file_merge.py` | 文件合并工具 | file_merge_Skill.md |
| `file_rename.py` | 文件重命名工具 | - |
| `find_csv_in_matched_folders.py` | 递归匹配 testcase 文件夹收集 RX CSV；路径 + `testcase_folder` 解析（`mld_en`、`cur_degree`）；灵敏度汇总 CSV；**同配置叠加 mld_en0/1 雷达对比图**；copy/move、list-out、顶部配置区 | `skill/find_csv_in_matched_folders_Skill.md` |
| `wifi_rx_sensitivity.py` | PER 插值求 `sensitivity_dbm`（同 wifiRxPlot）；`parse_testcase_folder_params`、`plot_sensitivity_radar`（供 find_csv 调用） | `skill/find_csv_in_matched_folders_Skill.md` |
| `organize_sensitivity_mld_diff.py` | `*_result.csv` 宽表合并 mld_en0/1；差值 en0−en1；`organized/*_mld_wide.csv` + 着色 xlsx | `skill/organize_sensitivity_mld_diff.skill` + `skill/organize_sensitivity_mld_diff_Skill.md` |
| `process_ila_files.py` | 处理FPGA导出的ILA信号文件，解压缩并提取waveform.csv，按原始文件名重命名 | process_ila_files.skill |

#### 2. EVM 分析工具
| 脚本名称 | 功能说明 | 详细文档 |
|---------|---------|---------|
| `txAnalyse.py` | 主要的 EVM 分析脚本（支持 WiFi 6） | txAnalyse.skill |
| `txAnalyse_wifi7.py` | WiFi 7 专用 TX 分析 / 多子图 PDF；子图标题含带宽(MHz)、BCC/LDPC（列或文件名推断）、wifi_format、信道、Nsts、GI；CSV 含 `suer_dcm` 时追加 `dcm=` | txAnalyse.skill |
| `txAnalyse_compatible.py` | 兼容性版本的 EVM 分析脚本 | txAnalyse.skill |
| `evm_comparison.py` | EVM 比较分析脚本 | evm_comparison.skill |

#### 3. 功率测量与分析
| 脚本名称 | 功能说明 | 详细文档 |
|---------|---------|---------|
| `clac_pwr_for_ofdm_signal.py` | OFDM 信号功率计算 | - |
| `compare_avg_pwr.py` | 平均功率比较分析 | compare_avg_pwr_Skill.md |

#### 4. 频谱分析工具
| 脚本名称 | 功能说明 | 详细文档 |
|---------|---------|---------|
| `psd_plot.py` | PSD（功率谱密度）绘图 | psd_plot_Skill.md |
| `plot_spectrum.py` | 频谱绘图 | - |

陷波与杂散专项脚本均在 **`spur_notch/`**（见上文 **「Notch & Spur」**）。

#### 5. 灵敏度测试
| 脚本名称 | 功能说明 | 详细文档 |
|---------|---------|---------|
| `calculate_sensitivity_and_plot.py` | 灵敏度计算与绘图 | calculate_sensitivity_and_plot_Skill.md |

#### 6. 接收测试工具
| 脚本名称 | 功能说明 | 详细文档 |
|---------|---------|---------|
| `spur_notch/wifiRxProcess.py` | 杂散/灵敏度结果目录整理：合并 `notch_enable0`/`notch_enable1` 等并生成 **`*_spur.xlsx`**；PER/EVM 与 `wifiRxPlot` 思路一致 | wifiRxProcess_Skill.md |
| `wifiRxPlot.py` | WiFi 接收数据绘图（根目录，常与 `wifiRxProcess` 流程配合） | - |

#### 7. 数据验证与检查工具
| 脚本名称 | 功能说明 | 详细文档 |
|---------|---------|---------|
| `check_excel_colors.py` | 检查 Excel 文件颜色标记 | check_excel_colors_Skill.md |
| `check_excel_fill.py` | 检查 Excel 填充色 | check_excel_fill_Skill.md |
| `check_columns.py` | 检查列一致性 | check_columns_Skill.md |
| `validate_conversion.py` | 验证数据转换 | validate_conversion_Skill.md |
| `tx_adcdump_data_parse.py` | 将 ADC 采样数据的 bit 字段转换为有符号数 | tx_adcdump_data_parse_Skill.md |

#### 8. 寄存器查询与比较工具
| 脚本名称 | 功能说明 | 详细文档 |
|---------|---------|---------|
| `reg_query/reg_query.py` | E22 芯片寄存器查询（名称或地址）；同目录 `reg_query_gui.py` 为 GUI | reg_query/reg_query.skill |
| `compare_reg_csv.py` | 比较两个寄存器配置 CSV 文件 | compare_reg_csv_Skill.md |

#### 9. 报告生成工具
| 脚本名称 | 功能说明 | 详细文档 |
|---------|---------|---------|
| `generate_report.py` | 生成测试报告 | generate_report_Skill.md |

#### 10. 项目管理 / Git 辅助
| 脚本名称 | 功能说明 | 详细文档 |
|---------|---------|---------|
| `check_and_commit.py` | 检查并提交代码 | - |
| `commit_all_changes.py` | 提交所有变更 | - |
| `commit_changes.py` | 提交变更 | - |
| *(另有多份根目录 `commit_*.py`、`simple_commit.py`)* | 历史或场景化提交流程，按需选用 | - |


#### 11. tx magtrk测试
| 脚本名称 | 功能说明 | 详细文档 |
|---------|---------|---------|
| `txmagtrk_analyse.py` | 发射功率跟踪数据分析（e22芯片测试环境分析） | txmagtrk_analyse_Skill.md |
| `mag_track_rls4_fpga_analyse.py` | RLS4.0 FPGA测试环境分析：`mag_track_test_res_*.csv` → 按分面（默认含 `chan,dly` 等）出 PDF；**仅当**分面存在 `tx_mag_track_on=1` 时出页；同图叠 **`tx_mag_track_on=0`** 基线（**同 `chan`**，跨全部 `dly`/mag 在 `tx_pwr` 上均值）与 FPGA-on 严格曲线；缺基线见 `*_rls4_magtrk_plot_warnings.txt` | mag_track_rls4_fpga_analyse_Skill.md |
| `analyze_mag_track_test_res.py` | Mag track 回归 CSV（`tx_mag_track_on`/`amplitude`/参数列/`evm`）统计与 HTML/PNG 报告 | analyze_mag_track_test_res_Skill.md |

#### 12. RX CSV 检索与灵敏度雷达
| 脚本名称 | 功能说明 | Skill |
|---------|---------|-------|
| `find_csv_in_matched_folders.py` | 主流程：通配找文件夹 → 收集 CSV → 路径/`mld_en`/`cur_degree` 解析 → 灵敏度 CSV → 雷达图（默认 `<csv_stem>_radar/`） | `skill/find_csv_in_matched_folders.skill` + `skill/find_csv_in_matched_folders_Skill.md` |
| `wifi_rx_sensitivity.py` | 灵敏度计算与雷达绘制模块；可被 find_csv 或脚本内 API 单独调用 | 同上 |
| `organize_sensitivity_mld_diff.py` | 整理 `*_result.csv`：同配置合并 mld_en0/1 宽表，`sensitivity_dbm_mld_diff`=en0−en1，xlsx 差值列着色 | `skill/organize_sensitivity_mld_diff.skill` + `skill/organize_sensitivity_mld_diff_Skill.md` |

### 子目录补充说明（与「仓库目录结构总览」对应）

#### evm_comparison_scripts/
- **位置**: `./evm_comparison_scripts/`
- **说明文档**: `EVM_Comparison_Scripts_Skill.md`
- **脚本列表**: 见上文「`evm_comparison_scripts/` 脚本一览」
- **结果子目录**:
  - `evm_by_wifi_format_comparison/` — WiFi 格式比较结果
  - `rls3_rls4_evm_comparison/` — RLS3 vs RLS4
  - `rls4_wifi7_evm_comparison/` — RLS4 vs WiFi7

#### rx_iq_test/
- **位置**: `./rx_iq_test/`
- **说明文档**: `skill/` 下 `organize_dump_files_Skill.md`、`organize_rx_iq_data_Skill.md`、`rx_iq_result_analyze_Skill.md` 等
- **主要脚本**:
  - `organize_dump_files.py` — 按文件名配置将文件复制到目标层级目录
  - `organize_rx_iq_data.py` — 按带宽、频率、通道整理与重命名
  - `rx_iq_result_analyze.py` — 分析 `diff_pwr` 等列，条件着色与统计
  - `tx_iq_result_analyse.py` — TX IQ 结果分析

#### reg_query/
- **位置**: `./reg_query/`
- **说明文档**: `reg_query.skill`
- **入口**: `reg_query.py`（CLI）、`reg_query_gui.py`（GUI）
- **数据**: `base_addr.txt`、`csv_files/*.csv`
- **功能摘要**: 按寄存器名或物理地址查询；可指定 CSV 目录；列出可用定义文件

#### register_comparison_scripts/
- **位置**: `./register_comparison_scripts/`
- **脚本**: `compare_registers.py`
- **说明文档**: `Register_Comparison_Scripts_Skill.md`

#### skill/
- **位置**: `./skill/`
- **内容**: Claude Code 技能（`*.skill`）与各脚本配套的 `*_Skill.md`
- **常见技能文件**: `txAnalyse.skill`、`evm_comparison.skill`、`txmagtrk_analyse.skill`、`mag_track_rls4_fpga_analyse.skill`、`analyze_mag_track_test_res.skill`、`spur_scan_process.skill`、`spur_diff_and_mark_red.skill`、`merge_csv_to_xlsx_skill.md`、`organize_sensitivity_mld_diff.skill`、`process_ila_files.skill`、`my_ag.skill` 等（完整列表以目录为准）
- **`spur_scan_process`**（杂散扫描主流程）:
  - **`spur_scan_process.skill`** — 三步流水线、输入格式、配置项
  - **`spur_scan_process_Skill.md`** — PSD 检测规则、信道筛选、陷波定点、产物路径、API
  - 脚本：`spur_notch/spur_scan_process.py`；详见 **「Notch & Spur」**
- **`find_csv_in_matched_folders`**（RX 灵敏度 + 雷达）:
  - **`find_csv_in_matched_folders.skill`** — 配置项、命令示例、指向完整 MD
  - **`find_csv_in_matched_folders_Skill.md`** — 路径解析表、灵敏度 CSV 列、雷达图分组（mld_en0/1 同图）、`--no-radar` / `--radar-dir`、Python API
  - 对应脚本：根目录 `find_csv_in_matched_folders.py`、`wifi_rx_sensitivity.py`；详见上文 **「RX CSV 检索与灵敏度雷达」**
- **`organize_sensitivity_mld_diff`**（灵敏度 mld_en 宽表）:
  - **`organize_sensitivity_mld_diff.skill`** — 默认路径、命令示例、指向完整 MD
  - **`organize_sensitivity_mld_diff_Skill.md`** — 配对键、输出列、差值公式与 xlsx 着色阈值、Python API
  - 对应脚本：根目录 `organize_sensitivity_mld_diff.py`；输入常为 `find_csv` 产出的 `*_result.csv`
- **子目录 `merged_tx_result_analysis/`**: 合并 TX 结果分析相关说明脚本与 `generate_report.py` 等，与根目录 `generate_report.py`、`analyze_merged_tx_result.py` 等配合使用

### 常用命令示例

#### Commit Message 规范
- 所有 commit 消息必须使用 **英文** 描述
- 第一行简要说明修改内容（不超过 50 个字符）
- 换行后详细描述修改细节（可选，但推荐）
- 使用动词开头，如："Add", "Fix", "Update", "Refactor" 等
- 避免使用中文或其他非英文内容

#### 寄存器查询工具
在仓库根目录执行（或按需改为 `cd reg_query` 后去掉路径前缀）：

```bash
# 查询寄存器名称
python reg_query/reg_query.py reg_mcs10_ldpc_man

# 查询物理地址
python reg_query/reg_query.py 0xc3026cc0

# 指定寄存器 CSV 目录
python reg_query/reg_query.py -c "D:\fpga_test\imag\E22_4.0\260420\csv" reg_mcs10_ldpc_man

# 列出可用的 CSV 定义文件
python reg_query/reg_query.py -l

# 查看使用帮助
python reg_query/reg_query.py --help

# 启动 GUI
python reg_query/reg_query_gui.py
```

#### 其他工具命令
```bash
# 合并 CSV 文件到 Excel（默认会生成 EVM 透视、WiFi7 TX PDF、EVM 异常报告；可用 --no_wifi7_plots / --no_evm_anomaly 关闭）
python merge_csv_to_xlsx.py --input_dir ./data --output_file merged_data.xlsx
python merge_csv_to_xlsx.py --input_dir ./data --output_file merged_data.xlsx --no_wifi7_plots --no_evm_anomaly

# 分析 EVM 数据
python txAnalyse.py --input_file test_data.csv --output_dir ./results

# 计算灵敏度
python calculate_sensitivity_and_plot.py --input_file sensitivity_data.csv

# Mag track 回归 CSV（mag_track_test_res）：按开关与参数聚合 EVM，生成 _analysis 目录
python analyze_mag_track_test_res.py "D:\path\to\mag_track_test_res_*.csv" -o "D:\path\to\out_analysis"

# RLS4.0 FPGA mag track 回归 CSV → EVM vs tx_pwr PDF（同 chan 的 tx_mag_track_on=0 基线 + FPGA-on 曲线）
python mag_track_rls4_fpga_analyse.py "D:\path\to\mag_track_test_res_*.csv" -o "D:\path\to\rls4_magtrk_pdf_out"

# RX CSV 检索 + 灵敏度 CSV + mld_en0/1 对比雷达图（改脚本顶部配置区或传参）
python find_csv_in_matched_folders.py
python find_csv_in_matched_folders.py -r "D:\path\to\rftest_data\2G" -f "wifi_txrx_test_RXSens_*_mld_en*_cur_degree*"
python find_csv_in_matched_folders.py --sensitivity-out "D:\path\to\sens_summary.csv" --radar-dir "D:\path\to\radar"
python find_csv_in_matched_folders.py --no-radar --no-sensitivity
python find_csv_in_matched_folders.py --list-out "D:\path\to\matched.tsv" -v

# 灵敏度 *_result.csv → mld_en0/1 宽表 + 差值着色 xlsx（默认 output/sensitivity_out/result/organized）
python organize_sensitivity_mld_diff.py
python organize_sensitivity_mld_diff.py --input_dir "D:\users\gxu\scripts\output\sensitivity_out\result" --combined "D:\path\to\all_mld_wide.csv"

# Notch / spur（在仓库根目录执行；脚本位于 spur_notch/）
python spur_notch/spur_scan_process.py   # 改脚本底部 INPUT_DIR/FS/SPUR_THR/Q 等
python spur_notch/wifiRxProcess.py
python spur_notch/move_spur_scan_result_csvs.py

# 使用 Claude Code 技能
/skill txAnalyse  # 分析 EVM 数据
/skill evm_comparison  # 比较 EVM 数据
/skill txmagtrk_analyse  # 分析功率跟踪数据
/skill analyze_mag_track_test_res  # Mag track 回归 CSV 分析
/skill mag_track_rls4_fpga_analyse  # RLS4 FPGA mag_track PDF 与基线对比
/skill find_csv_in_matched_folders  # RX CSV 检索、灵敏度 CSV、mld_en 对比雷达图
/skill organize_sensitivity_mld_diff  # 灵敏度 result CSV → mld_en 宽表与差值 xlsx
/skill spur_scan_process           # 杂散扫描：PSD→coef→pwr 三步流水线
```

---

