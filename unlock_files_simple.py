
import os
import sys
import win32file
import win32con

def unlock_file(file_path):
    try:
        # 尝试以只读模式打开文件
        handle = win32file.CreateFile(
            file_path,
            win32con.GENERIC_READ,
            win32con.FILE_SHARE_DELETE | win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_ATTRIBUTE_NORMAL,
            None
        )
        handle.close()
        print(f"File unlocked: {file_path}")
        return True
    except Exception as e:
        print(f"Failed to unlock file: {file_path}")
        print(f"Error: {e}")
        return False

def main():
    directory = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx\20260407\vht_ht_2\evm_comparison_results"

    if not os.path.exists(directory):
        print("Directory does not exist")
        return

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            print(f"\nProcessing file: {filename}")

            if unlock_file(file_path):
                try:
                    # 尝试删除文件
                    os.remove(file_path)
                    print(f"File deleted: {file_path}")
                except Exception as e:
                    print(f"Failed to delete file: {file_path}")
                    print(f"Error: {e}")

    # 尝试删除目录
    try:
        os.rmdir(directory)
        print(f"Directory deleted: {directory}")
    except Exception as e:
        print(f"Failed to delete directory: {directory}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
