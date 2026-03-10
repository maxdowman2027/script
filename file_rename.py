import os
import sys

def rename_files(target_path, old_char, new_char, recursive=False):
    """
    替换指定路径下所有文件名称中的指定字符（适配所有文件类型）
    :param target_path: 目标文件夹路径（如r"D:\test"）
    :param old_char: 要替换的字符/字符串（如"old"）
    :param new_char: 替换后的字符/字符串（如"new"）
    :param recursive: 是否递归遍历子文件夹（True/False）
    """
    # 1. 校验目标路径是否存在
    if not os.path.exists(target_path):
        print(f"❌ 错误：目标路径 {target_path} 不存在！")
        return
    
    # 2. 初始化统计变量（适配所有文件类型）
    total_files = 0       # 遍历的文件总数（所有类型）
    renamed_files = 0     # 成功重命名的文件数
    skip_files = []       # 跳过的文件（无匹配字符/已存在新文件名/权限不足等）
    
    # 3. 遍历文件（递归/非递归）
    for root, dirs, files in os.walk(target_path):
        for file_name in files:
            total_files += 1  # 所有文件都计数，不再筛选CSV
            # 检查文件名是否包含要替换的字符
            if old_char not in file_name:
                skip_files.append(os.path.join(root, file_name))
                continue
            
            # 4. 生成新文件名（保留原后缀）
            new_file_name = file_name.replace(old_char, new_char)
            # 拼接原文件完整路径和新文件完整路径
            old_file_path = os.path.join(root, file_name)
            new_file_path = os.path.join(root, new_file_name)
            
            # 5. 安全校验：新文件名已存在则跳过（避免覆盖）
            if os.path.exists(new_file_path):
                print(f"⚠️ 跳过：新文件名 {new_file_name} 已存在，不覆盖 → {old_file_path}")
                skip_files.append(old_file_path)
                continue
            
            # 6. 执行重命名（捕获异常）
            try:
                os.rename(old_file_path, new_file_path)
                renamed_files += 1
                print(f"✅ 重命名成功：{old_file_path} → {new_file_path}")
            except PermissionError:
                print(f"❌ 权限不足：无法重命名 {old_file_path}（文件可能被占用/无修改权限）")
                skip_files.append(old_file_path)
            except Exception as e:
                print(f"❌ 重命名失败 {old_file_path}：{str(e)}")
                skip_files.append(old_file_path)
        
        # 非递归模式：只遍历当前目录，退出os.walk循环
        if not recursive:
            break
    
    # 7. 输出统计结果（适配所有文件类型）
    print("\n" + "-"*60)
    print(f"📊 执行结果统计（所有文件类型）：")
    print(f"   遍历文件总数：{total_files}")
    print(f"   成功重命名：{renamed_files} 个")
    print(f"   跳过/失败：{len(skip_files)} 个")
    if skip_files:
        # 只显示前5个跳过的文件，避免输出过长
        print(f"   跳过的文件示例：{skip_files[:5]} {'...' if len(skip_files)>5 else ''}")

if __name__ == "__main__":
    # ========== 用户配置区（仅需修改以下4行） ==========
    TARGET_PATH = r"D:\users\gxu\spur_scan\260206\scprit_test"  # 目标路径（加r避免转义）
    OLD_CHAR = "旧字符"                                        # 要替换的字符/字符串（如"temp"）
    NEW_CHAR = "mcs0_vht_ldpc_rfpwr-56.7"                      # 替换后的字符/字符串（如"final"）
    RECURSIVE = False                                          # 是否递归遍历子文件夹（True/False）
    # ========== 无需修改以下代码 ==========
    
    # 调用重命名函数
    rename_files(
        target_path=TARGET_PATH,
        old_char=OLD_CHAR,
        new_char=NEW_CHAR,
        recursive=RECURSIVE
    )