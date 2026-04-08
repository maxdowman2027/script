
import shutil
import os
import time

def force_remove_dir(dir_path):
    if not os.path.exists(dir_path):
        print(f"Directory does not exist: {dir_path}")
        return True

    try:
        # 尝试直接删除
        shutil.rmtree(dir_path)
        print(f"Directory successfully removed: {dir_path}")
        return True
    except Exception as e:
        print(f"Failed to remove directory: {e}")

        # 尝试逐个删除文件
        try:
            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                try:
                    if os.path.isfile(file_path):
                        os.chmod(file_path, 0o777)
                        os.remove(file_path)
                        print(f"Removed file: {file_path}")
                    elif os.path.isdir(file_path):
                        force_remove_dir(file_path)
                except Exception as e2:
                    print(f"Failed to remove {file_path}: {e2}")

            # 最后删除目录
            os.rmdir(dir_path)
            print(f"Directory successfully removed: {dir_path}")
            return True
        except Exception as e3:
            print(f"Failed to force remove directory: {e3}")
            return False

if __name__ == "__main__":
    dir_path = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx\20260407\vht_ht_2\evm_comparison_results"

    print("Attempting to remove directory:", dir_path)

    # 尝试多次删除，每次间隔1秒
    for i in range(3):
        if force_remove_dir(dir_path):
            break
        else:
            print(f"Attempt {i+1} failed, retrying in 1 second...")
            time.sleep(1)
    else:
        print("All attempts failed to remove directory")
