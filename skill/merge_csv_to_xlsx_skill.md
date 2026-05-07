# merge_csv_to_xlsx.py 脚本说明文档

## 脚本概述

`merge_csv_to_xlsx.py` 用于将目录下 `risc_wifitx_*.csv` 合并为单个 Excel：按文件名中的 **信道 channel**、**编码 BCC/LDPC**、**NSS1/NSS2/STBC** 划分 Sheet；可选导出 **CRC 失败**、**Flatness 失败**、**SpecMargin 失败** 到独立文件；并为明细表中的 `evm` / `evm_nss0` / `evm_nss1` 列着色以便查看。

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

5. **命令行**  
   - `--summary_tx_pwr`：统计用功率点（dBm），默认 `15`。  
   - `--evm_summary_out`：指定统计表输出路径（可选）。  
   - `--no_evm_summary`：不生成统计文件。

6. **依赖与数据列**  
   统计依赖 CSV 中常见字段：`tx_power_set(dBm)`、`wifi_format`、`rate`、`fec_coding`（或从 CSV 分组 Sheet 名推断 BCC/LDPC）、`rf_chan`、`cbw`，以及 EVM 列（`evm` / `evm_aver(dB)` / `aver_evmAll` / `evm_nss0` 等）。

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

---

## 依赖

- `pandas`
- `openpyxl`

---

## 兼容说明（Claude Code Skill JSON）

以下为旧版 `.skill` 文件的等价元数据摘要，供自动化工具索引：

- **名称**: merge_csv_to_xlsx  
- **描述**: 合并 `risc_wifitx` CSV 到 XLSX；CRC/Flatness/SpecMargin 失败拆分；EVM 统计单独多 Sheet 输出（band/coding/NSS×STBC），Sheet 内按 bw 分组跨 rate 标注最优/最差 EVM。  
- **标签**: CSV合并, XLSX, WiFi测试, EVM, CRC, Flatness, SpecMargin  
- **需求**: pandas, openpyxl  
