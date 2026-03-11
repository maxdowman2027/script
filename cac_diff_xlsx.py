import pandas as pd

def calc_diff_from_spec_col_xlsx(file_path, base_row_idx=0, start_col_idx=0, output_path=None):
    """
    计算XLSX表格所有行与指定行的差值（仅从指定列数开始计算）
    :param file_path: XLSX文件路径（绝对/相对路径，如"D:/test.xlsx"）
    :param base_row_idx: 基准行行号（int，从0开始计数，0=第一行）
    :param start_col_idx: 起始列数（int，从0开始计数，2=第三列开始）
    :param output_path: 结果保存路径（None则不保存，需以.xlsx结尾）
    :return: 包含原列+差值列的DataFrame
    """
    # 步骤1：校验文件格式（仅处理XLSX/XLS）
    if not file_path.endswith((".xlsx", ".xls")):
        raise ValueError("仅支持Excel文件（.xlsx/.xls），请确认文件格式！")
    
    # 步骤2：读取XLSX文件（需提前安装openpyxl：pip install openpyxl）
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
    except ModuleNotFoundError:
        print("❌ 缺少读取XLSX的依赖库，请先执行：pip install openpyxl")
        return None
    except Exception as e:
        print(f"❌ 读取XLSX文件失败：{e}")
        return None
    
    # 步骤3：校验基准行数和起始列数（避免超出范围）
    # 校验基准行
    if base_row_idx < 0 or base_row_idx >= len(df):
        print(f"⚠️ 基准行号{base_row_idx}无效（表格共{len(df)}行），自动使用第一行（行号0）")
        base_row_idx = 0
    base_row = df.iloc[base_row_idx]
    
    # 校验起始列
    total_cols = len(df.columns)
    if start_col_idx < 0 or start_col_idx >= total_cols:
        print(f"⚠️ 起始列号{start_col_idx}无效（表格共{total_cols}列），自动使用第一列（列号0）")
        start_col_idx = 0
    
    # 步骤4：筛选起始列及之后的所有列
    target_cols_all = df.columns[start_col_idx:]  # 从指定列开始的所有列
    df_target_cols = df[target_cols_all]          # 截取指定列范围的子表格
    
    # 步骤5：筛选子表格中的数值列（仅计算int/float列）
    numeric_cols = df_target_cols.select_dtypes(include=['int64', 'float64']).columns
    if len(numeric_cols) == 0:
        print("⚠️ 指定列范围內无数值列，无需计算差值")
        return df
    
    # 步骤6：核心：计算所有行与基准行的差值
    diff_df = df_target_cols[numeric_cols].sub(base_row[numeric_cols], axis=1)
    diff_df.columns = [f"{col}_diff" for col in numeric_cols]  # 重命名差值列
    
    # 步骤7：合并原表格与差值列，填充空值
    result_df = pd.concat([df, diff_df], axis=1).fillna(0)
    
    # 步骤8：保存XLSX结果（可选）
    if output_path:
        if not output_path.endswith(".xlsx"):
            output_path = output_path + ".xlsx"  # 自动补全.xlsx后缀
        try:
            result_df.to_excel(output_path, index=False, engine="openpyxl")
            print(f"✅ 结果已保存至：{output_path}")
        except Exception as e:
            print(f"❌ 保存XLSX文件失败：{e}")
    
    return result_df

# ========== 示例调用（适配XLSX格式） ==========
if __name__ == "__main__":
    # 1. 定义XLSX文件参数
    xlsx_path = r"D:\users\gxu\spur_scan\2G_high_mcs\40m\vht\2G_40m_vht_spur.xlsx"
    base_row_idx = 0   # 指定第3行（行号从0开始）为基准行
    start_col_idx = 1   # 从第4列（列号从0开始）开始计算差值
    output_path = r"D:\users\gxu\spur_scan\2G_high_mcs\40m\vht\2G_40m_vht_spur_diff.xlsx"
    
    # 2. 执行计算
    result_df = calc_diff_from_spec_col_xlsx(
        file_path=xlsx_path,
        base_row_idx=base_row_idx,
        start_col_idx=start_col_idx,
        output_path=output_path
    )
    
    # 3. 打印结果预览
    if result_df is not None:
        print("=== 差值列预览（XLSX格式） ===")
        diff_cols = [col for col in result_df.columns if "_diff" in col]
        print(result_df[diff_cols].head())