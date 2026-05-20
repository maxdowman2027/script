# merge_csv_to_xlsx.py 脚本说明文档

## 脚本概述

`merge_csv_to_xlsx.py` 用于将目录下 `risc_wifitx_*.csv` 合并为单个 Excel：按文件名中的 **信道 channel**、**编码 BCC/LDPC**、**NSS1/NSS2/STBC** 划分 Sheet；可选导出 **CRC 失败**、**Flatness 失败**、**SpecMargin 失败** 到独立文件；并为明细表中的 `evm` / `evm_nss0` / `evm_nss1` 列着色以便查看。

合并完成后（默认）还会：**调用 `txAnalyse_wifi7.tx_plot_and_analyse`** 生成 WiFi7 TX 多页 PDF 与附带检查结果 txt；并对合并数据做 **EVM 异常扫描**，输出 txt 报告。

---

## 近期更新（WiFi7 绘图、EVM 异常扫描与绘图标题）

### WiFi7 TX 绘图（`txAnalyse_wifi7.py`）

1. **触发时机**  
   主 `.xlsx` 保存成功后，对 `input_dir` 下全部 **`risc_wifitx_*.csv`** 调用 **`tx_plot_and_analyse`**。

2. **输出位置**  
   默认目录：`{合并文件所在目录}/{合并文件名不含扩展名}_wifi7_tx_plot/`  
   文件前缀：`{合并文件名不含扩展名}_` + 时间戳 PDF（如 `*_tx_pdf_YYYY_MM_DD_HHMM.pdf`）及同前缀 txt。

3. **关闭方式**  
   命令行：`--no_wifi7_plots`；Python：`run_wifi7_plots=False`。  
   自定义目录：`--wifi7_plot_dir` / `wifi7_plot_dir=`。

4. **依赖数据格式**  
   与独立运行 `txAnalyse_wifi7.py` 相同：需 CSV 中含功率、EVM、IQ、谱模板等列；缺列时绘图可能在导入脚本中报错，合并脚本会捕获并打印失败原因。

5. **图标题（业务配置）**  
   **`txAnalyse_wifi7.py`** 中各子图标题由 **`_business_config_string`** 拼装：**带宽** 优先来自 **`cbw`**：值为 **0/1/2/3** 时分别显示 **20/40/80/160 MHz**（枚举）；其它取值或非枚举仍按数值或字符串格式化为 `…MHz`。也可读 `bandwidth` / `BW` 等列；缺失时从文件名中的 `risc_wifitx_20m_`、`_20m_` 等模式推断。**编码** **BCC/LDPC** 来自 **`fec_coding`**（列内多数表决），缺失时从文件名中的 `BCC`/`LDPC` 匹配。另含 **`wifi_format`**、**`rf_chan`**、**`Nsts`**、**GI** 等。  
   - **`suer_dcm`（或 `user_dcm`）**：若 CSV 含该列且能读到有效值，标题中追加 **`dcm=<值>`**（如 `dcm=0` / `dcm=1`），便于区分 HE SU DCM 开关配置；无该列则不显示。  
   - 仍无时退回为去掉 `risc_wifitx_` 后的文件名主干。  
   示例：`40MHz | hesu | ch36 | LDPC | dcm=1 | EVM`。同一段字符串用于 TXT 检查结果的分组标题。  
   `merge_csv_to_xlsx.run_wifi7_tx_plots` 直接调用上述逻辑，无需额外参数。

### EVM 异常扫描（`merge_csv_to_xlsx.py` 内）

1. **目的**  
   在相同 **`band` / coding（BCC·LDPC）/ `cbw` / NSS·STBC（来自 Sheet）/ `wifi_format`** 分组内：
   - 比较各 **rate** 在**全部 tx_pwr** 上的 **EVM 均值**：若某 rate 明显劣于组内中位数（默认高出 **2 dB**，即 EVM 数值更大），写入 **`[ANOMALY ALERT]`**。
   - 对每个 rate 的 **EVM–tx_pwr** 曲线，检测相邻功率点 **|ΔEVM|** 过大（默认 **3 dB**）。

2. **HT rate 口径**  
   与 EVM 透视统计一致：STBC / NSS2 下 **`_normalize_ht_rate_for_summary`** 归一后再分组。

3. **输出**  
   默认：`{basename}_evm_anomaly_report.txt`（与主合并文件同目录）。  
   控制台会重复打印含 **`[ANOMALY ALERT]`** 的行。

4. **关闭 / 调参**  
   - `--no_evm_anomaly` / `run_evm_anomaly_check=False`  
   - `--anomaly_report`、`--anomaly_rate_gap`（默认 2.0）、`--anomaly_curve_jump`（默认 3.0）

5. **数据采集**  
   只要开启 EVM 统计 **或** 异常扫描，脚本会从各 Sheet 合并数据中附带 **`_source_sheet`**；若仅关闭 EVM 透视但仍开启异常扫描，会按需二次读取 CSV 构建分析表。

---

## 近期更新（EVM 统计与独立输出）

1. **独立统计文件**  
   在指定发射功率点（默认 **15 dBm**，容差 ±0.51 dB）下，生成透视表：行为  
   `band`、`coding_LDPC_BCC`、`bw_cbw`、`rate`、`NSS_STBC`，列为各 **`wifi_format`** 的平均 EVM（dB）。  
   结果写入 **单独的 `.xlsx` 文件**（不嵌入主合并文件）。

2. **按 band / coding / NSS_STBC 分 Sheet**  
   同一文件内按 **`band`（2G/5G）**、**`coding_LDPC_BCC`（BCC/LDPC）**、**`NSS_STBC`（NSS1/NSS2/STBC）** 的组合拆成多个工作表；Sheet 名形如 `2G_BCC_NSS1`、`5G_LDPC_NSS2`（非法字符已替换，超长截断至 31 字符；重名时自动加 `_2`、`_3` 后缀）。  
   **每个 Sheet 内只保留列：`bw_cbw`、`rate`、以及各 `wifi_format` 的 EVM**，便于同一射频大类下浏览。

3. **默认输出路径**  
   与主合并结果同目录：  
   `{合并文件名去掉扩展名}_evm_{功率}dBm_stat.xlsx`  
   例如：`merged_tx_result.xlsx` → `merged_tx_result_evm_15dBm_stat.xlsx`。

4. **最优 / 最差 EVM 着色（Sheet 内、按 bw 分组跨 rate）**  
   在每个 Sheet 中，先按 **`bw_cbw` 分组**，在同一带宽内对不同 **rate** 行比较每个 **`wifi_format` 列**：
   - **浅绿色**（`#C6EFCE`）：该 **bw_cbw** 组内该列 **最优 EVM**（数值 **最小**，即最负）。
   - **浅红色**（`#FFC7CE`）：该 **bw_cbw** 组内该列 **最差 EVM**（数值 **最大**）。
   - 若该 **bw_cbw** 组仅一行或数值全相同，则只标 **绿色**。

5. **命令行（合并 / EVM 统计）**  
   - `--summary_tx_pwr`：统计用功率点（dBm），默认 `15`。  
   - `--evm_summary_out`：指定统计表输出路径（可选）。  
   - `--no_evm_summary`：不生成统计文件。  
   - `--no_wifi7_plots`：不调用 `txAnalyse_wifi7` 绘图。  
   - `--wifi7_plot_dir`：指定 WiFi7 PDF/txt 输出目录。  
   - `--no_evm_anomaly`：不写 EVM 异常报告。  
   - `--anomaly_report`：异常报告 txt 路径。  
   - `--anomaly_rate_gap`、`--anomaly_curve_jump`：异常阈值（dB）。

6. **依赖与数据列**  
   统计依赖 CSV 中常见字段：`tx_power_set(dBm)`、`wifi_format`、`rate`、`fec_coding`（或从 CSV 分组 Sheet 名推断 BCC/LDPC）、`rf_chan`、`cbw`，以及 EVM 列（`evm` / `evm_aver(dB)` / `aver_evmAll` / `evm_nss0` 等）。  
   WiFi7 PDF 标题若需区分 DCM，CSV 中应保留 **`suer_dcm`** 列。

7. **HT（wifi_format 为 ht）rate 口径归一**（透视前生效，仅用于统计聚合）  
   - **STBC**：`mcs{n}_stbc` 记为 `mcs{n}`（与单流 MCS 档位对齐）。  
   - **NSS2**：`mcs8`、`mcs9`… 分别记为 `mcs0`、`mcs1`…（即 MCS 编号 **≥8 时减 8**，与双流相对 MCS 对齐）。

---

## 主要功能

### 1. CSV 合并与 Sheet 划分

- 匹配 `risc_wifitx_*.csv`。  
- Sheet 名：`channel{信道}_{BCC|LDPC}[_{NSS1|NSS2|STBC}]`。  
- 合并同组多个 CSV，可选调整 `evm_nss0`/`evm_nss1` 列位置；按 `wifi_format` 对行填充区分格式。

### 2. 失败记录拆分（可选）

- **CRC**：`psdu_crc == Fail` → 指定 CRC 失败 xlsx。  
- **Flatness**：`spectralFlatness_margin` 解析出负值 → `{basename}_flatness_fail.xlsx`。  
- **SpecMargin**：`spectrumMarginDb` / `spectrumMarginDb_nss1` 解析出负值 → `{basename}_specmargin_fail.xlsx`。

### 3. EVM 统计独立报表（可选）

- 见上文「近期更新」：独立文件、**多 Sheet**（按 band / coding / NSS_STBC）、Sheet 内按 **bw_cbw** 分组跨 **rate** 最优/最差着色。

---

## 配置与调用

### 直接运行（默认路径见脚本内 `argparse`）

```bash
python merge_csv_to_xlsx.py
```

### 常用参数

```bash
python merge_csv_to_xlsx.py ^
  --input_dir "D:\path\to\csv_dir" ^
  --output_file "D:\path\to\merged_tx_result.xlsx" ^
  --crc_fail_file "D:\path\to\tx_crc_fail_result.xlsx" ^
  --summary_tx_pwr 15 ^
  --evm_summary_out "D:\path\to\custom_evm_stat.xlsx"
```

### WiFi7 绘图与 EVM 异常（可选开关示例）

```bash
python merge_csv_to_xlsx.py ^
  --input_dir "D:\path\to\csv_dir" ^
  --output_file "D:\path\to\merged_tx_result.xlsx" ^
  --wifi7_plot_dir "D:\path\to\wifi7_plots_out" ^
  --anomaly_report "D:\path\to\my_anomaly_report.txt" ^
  --anomaly_rate_gap 2.0 ^
  --anomaly_curve_jump 3.0

# 仅合并 + EVM 统计，跳过 WiFi7 PDF 与异常扫描
python merge_csv_to_xlsx.py --input_dir .\data --output_file .\merged.xlsx --no_wifi7_plots --no_evm_anomaly
```

### 从 Python 调用

```python
from merge_csv_to_xlsx import merge_csv_to_xlsx

merge_csv_to_xlsx(
    input_dir=r"D:\data\csv",
    output_file=r"D:\data\merged_tx_result.xlsx",
    crc_fail_file=r"D:\data\crc_fail.xlsx",
    summary_tx_pwr_dbm=15.0,
    add_evm_summary=True,
    evm_summary_output_file=None,  # None 则自动生成同目录 _evm_15dBm_stat.xlsx
    run_wifi7_plots=True,
    wifi7_plot_dir=None,
    run_evm_anomaly_check=True,
    anomaly_report_file=None,
    anomaly_rate_mean_gap_db=2.0,
    anomaly_curve_jump_db=3.0,
)
```

---

## 参数说明（merge_csv_to_xlsx）

| 参数 | 说明 |
|------|------|
| `input_dir` | 含 `risc_wifitx_*.csv` 的目录 |
| `output_file` | 主合并输出 `.xlsx` |
| `crc_fail_file` | CRC 失败输出；可为 `None` 关闭 |
| `summary_tx_pwr_dbm` | 统计表筛选功率（默认 15） |
| `add_evm_summary` | 是否生成 EVM 统计独立文件 |
| `evm_summary_output_file` | 统计文件路径；`None` 则自动命名 |
| `run_wifi7_plots` | 是否在合并完成后调用 `txAnalyse_wifi7.tx_plot_and_analyse` |
| `wifi7_plot_dir` | WiFi7 PDF/txt 输出目录；`None` 则为 `{basename}_wifi7_tx_plot` |
| `run_evm_anomaly_check` | 是否生成 `{basename}_evm_anomaly_report.txt` |
| `anomaly_report_file` | 异常报告路径；`None` 则默认与合并文件同目录 |
| `anomaly_rate_mean_gap_db` | 同配置下 rate 均值劣于组内中位数的阈值（dB） |
| `anomaly_curve_jump_db` | 同一 rate 相邻功率点 \|ΔEVM\| 阈值（dB） |

---

## 依赖

- `pandas`
- `openpyxl`
- `numpy`（EVM 异常扫描）
- **WiFi7 绘图**：`matplotlib`（由 `txAnalyse_wifi7` 导入）；该路径还需完整 TX CSV 列集

---

## 兼容说明（Claude Code Skill JSON）

以下为旧版 `.skill` 文件的等价元数据摘要，供自动化工具索引：

- **名称**: merge_csv_to_xlsx  
- **描述**: 合并 `risc_wifitx` CSV 到 XLSX；CRC/Flatness/SpecMargin 失败拆分；EVM 统计单独多 Sheet 输出（band/coding/NSS×STBC），Sheet 内按 bw 分组跨 rate 标注最优/最差 EVM；合并后可选调用 `txAnalyse_wifi7` 生成 TX 多页 PDF（图标题由 CSV 业务列拼装，含 `suer_dcm` 时追加 `dcm=`）并输出 EVM 跨 rate / 功率曲线异常 txt。  
- **标签**: CSV合并, XLSX, WiFi测试, EVM, CRC, Flatness, SpecMargin, WiFi7, matplotlib  
- **需求**: pandas, openpyxl, numpy；WiFi7 绘图另需 matplotlib 及 TX CSV 完整列  
