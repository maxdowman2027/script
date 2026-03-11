import os
import shutil
import fnmatch
import re

def move_csv_from_matched_folders_recursively(
    root_search_path,  # 要递归搜索文件夹的根路径
    folder_pattern,    # 文件夹命名匹配规则（通配符/正则）
    csv_pattern,       # CSV文件命名匹配规则（通配符/正则）
    target_move_path,  # 移动到的目标路径
    use_regex_folder=False,  # 文件夹是否用正则匹配
    use_regex_csv=False,     # CSV文件是否用正则匹配
    overwrite=False          # 是否覆盖重名文件（False=自动加后缀）
):
    """
    1. 递归搜索指定根路径下符合命名格式的文件夹
    2. 在这些符合条件的文件夹内（包括其子文件夹）递归查找符合格式的CSV文件
    3. 将所有匹配的CSV文件移动到指定目标路径
    """
    # 验证搜索根路径是否存在
    if not os.path.exists(root_search_path):
        print(f"错误：搜索根路径 '{root_search_path}' 不存在！")
        return

    # 自动创建目标路径（如果不存在）
    os.makedirs(target_move_path, exist_ok=True)
    print(f"目标路径已确认/创建：{target_move_path}")

    # 统计变量
    total_matched_folders = 0  # 符合条件的文件夹数
    total_scanned_subfolders = 0  # 内层递归扫描的子文件夹数
    total_matched_csv = 0      # 符合条件的CSV文件数
    total_moved = 0           # 成功移动的CSV数
    total_skipped = 0          # 跳过/移动失败的CSV数

    # 第一步：外层递归 - 查找所有符合命名格式的文件夹
    for dir_path, _, _ in os.walk(root_search_path):
        # 获取当前文件夹的名称（仅最后一级）
        current_folder_name = os.path.basename(dir_path)

        # 匹配文件夹命名规则
        is_folder_match = False
        if use_regex_folder:
            is_folder_match = re.match(folder_pattern, current_folder_name) is not None
        else:
            is_folder_match = fnmatch.fnmatch(current_folder_name, folder_pattern)

        if not is_folder_match:
            continue  # 跳过不符合条件的文件夹

        total_matched_folders += 1
        print(f"\n========== 找到符合条件的文件夹：{dir_path} ==========")

        # 第二步：内层递归 - 在该文件夹内（包括所有子文件夹）查找CSV文件
        for sub_dir_path, _, file_names in os.walk(dir_path):
            total_scanned_subfolders += 1
            # 仅在非空文件夹时打印（避免冗余输出）
            if file_names:
                print(f"  扫描子文件夹：{sub_dir_path}")

            # 筛选符合条件的CSV文件
            for file_name in file_names:
                # 过滤非CSV文件（大小写不敏感）
                if not file_name.lower().endswith(".csv"):
                    continue

                # 匹配CSV文件命名规则
                is_csv_match = False
                if use_regex_csv:
                    is_csv_match = re.match(csv_pattern, file_name) is not None
                else:
                    is_csv_match = fnmatch.fnmatch(file_name, csv_pattern)

                if not is_csv_match:
                    continue

                # 找到符合条件的CSV文件
                total_matched_csv += 1
                source_csv = os.path.join(sub_dir_path, file_name)
                print(f"    ✅ 找到目标CSV：{source_csv}")

                # 处理重名文件（避免覆盖）
                target_csv = os.path.join(target_move_path, file_name)
                if os.path.exists(target_csv) and not overwrite:
                    file_base, file_ext = os.path.splitext(file_name)
                    suffix = 1
                    while True:
                        new_file_name = f"{file_base}_{suffix}{file_ext}"
                        target_csv = os.path.join(target_move_path, new_file_name)
                        if not os.path.exists(target_csv):
                            print(f"      ⚠️  重名自动重命名：{new_file_name}")
                            break
                        suffix += 1

                # 移动CSV文件
                try:
                    shutil.move(source_csv, target_csv)
                    total_moved += 1
                    print(f"      ✔️  移动成功：{target_csv}")
                except PermissionError:
                    print(f"      ❌  权限错误：无法读取/写入 {source_csv}")
                    total_skipped += 1
                except FileNotFoundError:
                    print(f"      ❌  文件不存在：{source_csv}（可能已被删除）")
                    total_skipped += 1
                except Exception as e:
                    print(f"      ❌  移动失败：{source_csv} → {str(e)}")
                    total_skipped += 1

    # 输出最终统计结果
    print(f"\n=================== 移动完成 ===================")
    print(f"📁 递归搜索根路径：{root_search_path}")
    print(f"📂 找到符合条件的文件夹：{total_matched_folders} 个")
    print(f"🔍 内层扫描子文件夹总数：{total_scanned_subfolders} 个")
    print(f"📄 找到符合条件的CSV文件：{total_matched_csv} 个")
    print(f"✅ 成功移动到目标路径：{total_moved} 个")
    print(f"❌ 跳过/移动失败：{total_skipped} 个")
    print(f"🎯 目标路径：{target_move_path}")

# ===================== 配置区（请根据你的需求修改）=====================
if __name__ == "__main__":
    # 1. 要递归搜索的根路径（替换为你的实际路径）
    ROOT_SEARCH_PATH = r"D:\chip_test\dev\chip_rx\eagletest\rftest_data\2G\phymd40\40m\ldpc\vht"  # Windows示例
    # ROOT_SEARCH_PATH = "/home/yourname/source_root"  # Linux/Mac示例

    # 2. 文件夹命名匹配规则（示例：匹配以"report_"开头的文件夹）
    FOLDER_PATTERN = "*_notch_enable0"  # 通配符示例
    # FOLDER_PATTERN = r"^data_\d{4}$"  # 正则示例（如data_2024、data_2025）

    # 3. CSV文件命名匹配规则（示例：匹配以"sales_"开头的CSV）
    CSV_PATTERN = "Rx_mcs*_20260311_*.csv"  # 通配符示例
    # CSV_PATTERN = r"^order_\d{8}\.csv$"  # 正则示例（如order_20260209.csv）

    # 4. 移动到的目标路径（替换为你的实际路径）
    TARGET_MOVE_PATH = r"D:\users\gxu\spur_scan\260311\add_pwr_diff_3\2G\40m\vht\notch_enable0\vht\ldpc"  # Windows示例
    # TARGET_MOVE_PATH = "/home/yourname/moved_target"  # Linux/Mac示例

    # 5. 是否使用正则匹配（文件夹/CSV）
    USE_REGEX_FOLDER = False
    USE_REGEX_CSV = False

    # 6. 是否覆盖目标路径下的重名文件（False=自动加后缀，True=覆盖）
    OVERWRITE = False

    # 执行核心函数
    move_csv_from_matched_folders_recursively(
        root_search_path=ROOT_SEARCH_PATH,
        folder_pattern=FOLDER_PATTERN,
        csv_pattern=CSV_PATTERN,
        target_move_path=TARGET_MOVE_PATH,
        use_regex_folder=USE_REGEX_FOLDER,
        use_regex_csv=USE_REGEX_CSV,
        overwrite=OVERWRITE
    )
