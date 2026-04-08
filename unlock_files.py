
import os
import win32api
import win32con
import win32file
import win32security

def unlock_file(file_path):
    """尝试解锁文件"""
    try:
        # 打开文件
        handle = win32file.CreateFile(
            file_path,
            win32con.GENERIC_WRITE,
            win32con.FILE_SHARE_DELETE | win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_ATTRIBUTE_NORMAL,
            None
        )

        # 尝试获取文件访问权限
        sd = win32security.GetFileSecurity(
            file_path,
            win32security.DACL_SECURITY_INFORMATION
        )
        dacl = sd.GetSecurityDescriptorDacl()

        # 向所有用户授予完全控制权限
        everyone_sid = win32security.CreateWellKnownSid(win32security.WinLocalSystemSid)
        ace = win32security.ACL()
        ace.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            win32con.GENERIC_ALL,
            everyone_sid
        )
        dacl.AddAce(ace)
        sd.SetSecurityDescriptorDacl(True, dacl, False)
        win32security.SetFileSecurity(
            file_path,
            win32security.DACL_SECURITY_INFORMATION,
            sd
        )

        handle.close()
        print(f"Successfully unlocked file: {file_path}")
        return True

    except Exception as e:
        print(f"Failed to unlock file {file_path}: {e}")
        return False

def main():
    directory = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx\20260407\vht_ht_2\evm_comparison_results"
    print(f"Unlocking files in directory: {directory}")

    if not os.path.exists(directory):
        print("Directory does not exist")
        return

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            print(f"\nUnlocking: {filename}")
            unlock_file(file_path)

    print("\nUnlocking complete")

if __name__ == "__main__":
    main()
