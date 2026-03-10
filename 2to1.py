import os
import glob
import pandas as pd

def split_csv_by_odd_even_rows(target_path, recursive=False, encoding="utf-8-sig"):
    """
    搜索指定路径下的CSV文件，拆分为奇数行和偶数行两个文件
    :param target_path: 目标文件夹路径（如r"D:\test"）
    :param recursive: 是否递归搜索子文件夹（True=递归，False=仅当前文件夹）
    :param encoding: CSV文件编码（默认utf-8-sig，中文乱码可改为gbk/gb2312）
    """
    # 1. 校验目标路径是否存在
    if not os.path.exists(target_path):
        print(f"❌ 错误：目标路径 {target_path} 不存在！")
        return
    
    # 2. 匹配所有CSV文件（兼容大小写，如.CSV/.csv）
    file_pattern = "*.csv" if not recursive else os.path.join(target_path, "**", "*.csv")
    if not recursive:
        file_pattern = os.path.join(target_path, "*.csv")
    
    # 获取所有CSV文件路径（支持递归）
    csv_files = glob.glob(file_pattern, recursive=recursive)
    # 兼容大写后缀（如.CSV）
    csv_files += glob.glob(file_pattern.upper(), recursive=recursive)
    # 去重（避免重复处理）
    csv_files = list(set(csv_files))
    
    if not csv_files:
        print(f"⚠️ 路径 {target_path} 下未找到CSV文件！")
        return
    
    # 3. 遍历每个CSV文件进行拆分
    for file_path in csv_files:
        try:
            print(f"\n🔍 正在处理文件：{file_path}")
            
            # 读取CSV文件（处理编码、空值）
            df = pd.read_csv(
                file_path,
                encoding=encoding,
                na_filter=False  # 避免空值被识别为NaN
            )
            
            # 4. 拆分奇数行/偶数行（重置索引，避免行号断层）
            # 奇数行：CSV 1、3、5... → Pandas索引 0、2、4...
            df_odd = df.iloc[::2].reset_index(drop=True)
            # 偶数行：CSV 2、4、6... → Pandas索引 1、3、5...
            df_even = df.iloc[1::2].reset_index(drop=True)
            
            # 5. 构造新文件名（原目录+原文件名+后缀）
            file_dir = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            name_without_ext, ext = os.path.splitext(file_name)
            
            # 拆分后的文件路径
            odd_file_path = os.path.join(file_dir, f"{name_without_ext}_奇数行{ext}")
            even_file_path = os.path.join(file_dir, f"{name_without_ext}_偶数行{ext}")
            
            # 6. 保存拆分后的CSV文件（保留原编码）
            df_odd.to_csv(odd_file_path, index=False, encoding=encoding)
            df_even.to_csv(even_file_path, index=False, encoding=encoding)
            
            print(f"✅ 拆分完成：")
            print(f"   奇数行文件：{odd_file_path}（共{len(df_odd)}行）")
            print(f"   偶数行文件：{even_file_path}（共{len(df_even)}行）")
        
        except UnicodeDecodeError:
            # 编码错误时自动尝试GBK编码
            print(f"⚠️ {file_path} 用{encoding}编码读取失败，尝试GBK编码...")
            try:
                df = pd.read_csv(file_path, encoding="gbk", na_filter=False)
                df_odd = df.iloc[::2].reset_index(drop=True)
                df_even = df.iloc[1::2].reset_index(drop=True)
                odd_file_path = os.path.join(os.path.dirname(file_path), f"{os.path.splitext(os.path.basename(file_path))[0]}_奇数行.csv")
                even_file_path = os.path.join(os.path.dirname(file_path), f"{os.path.splitext(os.path.basename(file_path))[0]}_偶数行.csv")
                df_odd.to_csv(odd_file_path, index=False, encoding="gbk")
                df_even.to_csv(even_file_path, index=False, encoding="gbk")
                print(f"✅ 用GBK编码拆分完成！")
            except Exception as e:
                print(f"❌ 读取文件 {file_path} 失败：{str(e)}")
        except Exception as e:
            print(f"❌ 处理文件 {file_path} 出错：{str(e)}")
    
    print("\n🎉 所有CSV文件处理完成！")

# ========== 示例调用（直接修改以下参数即可） ==========
if __name__ == "__main__":
    # 配置参数
    TARGET_PATH = r"D:\users\gxu\spur_scan\260225\dump_data\test"  # 替换为你的目标路径
    RECURSIVE_SEARCH = False  # 是否递归搜索子文件夹（True/False）
    CSV_ENCODING = "utf-8-sig"  # CSV编码（中文乱码改"gbk"）
    
    # 执行拆分
    split_csv_by_odd_even_rows(
        target_path=TARGET_PATH,
        recursive=RECURSIVE_SEARCH,
        encoding=CSV_ENCODING
    )