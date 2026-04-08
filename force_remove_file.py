import os
import sys
import win32file
import win32con

def force_remove_file(file_path):
    try:
        # 尝试正常删除文件
        os.remove(file_path)
        print(f"File successfully removed: {file_path}")
        return True
    except Exception as e:
        print(f"Failed to remove file normally: {e}")

    try:
        # 尝试强制删除文件
        handle = win32file.CreateFile(
            file_path,
            win32con.GENERIC_WRITE,
            0,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_ATTRIBUTE_NORMAL,
            None
        )
        win32file.SetFileInformationByHandle(
            handle,
            win32file.FileDispositionInfo,
            {"DeleteFile": 1}
        )
        handle.close()
        print(f"File successfully removed by handle: {file_path}")
        return True
    except Exception as e:
        print(f"Failed to remove file by handle: {e}")

    try:
        # 尝试使用命令行删除
        import subprocess
        subprocess.run(['cmd', '/c', 'del', '/f', '/q', file_path], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"File successfully removed by cmd: {file_path}")
        return True
    except Exception as e:
        print(f"Failed to remove file by cmd: {e}")

    return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python force_remove_file.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(0)

    if os.path.isdir(file_path):
        print("This is a directory, not a file")
        sys.exit(1)

    success = force_remove_file(file_path)
    sys.exit(0 if success else 1)
