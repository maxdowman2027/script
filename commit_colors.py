import subprocess
import os

def run_git_command():
    # 设置工作目录
    os.chdir("D:/users/gxu/scripts")

    try:
        # 添加修改的文件
        print("添加修改的文件...")
        subprocess.run(["git", "add", "merge_csv_to_xlsx.py"], check=True)
        subprocess.run(["git", "add", "check_fill_colors.py"], check=True)

        # 提交修改
        print("提交修改...")
        subprocess.run(["git", "commit", "-m", "为不同wifi_format的行添加填充色"], check=True)

        print("提交成功！")
    except subprocess.CalledProcessError as e:
        print(f"git命令执行失败: {e}")
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    run_git_command()