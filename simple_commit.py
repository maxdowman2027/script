import subprocess
import os

def main():
    repo_path = 'D:/users/gxu/scripts'
    os.chdir(repo_path)

    commit_message = "添加所有剩余的分析脚本和文件"

    try:
        print(f"正在提交变更，提交信息: '{commit_message}'")

        # 使用 subprocess 直接运行 git commit 命令
        # 注意：在 Windows 上，我们需要使用 shell=True
        result = subprocess.run(
            ['git', 'commit', '-m', commit_message],
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("提交成功！")
            print(f"标准输出:\n{result.stdout}")
        else:
            print(f"提交失败，返回码: {result.returncode}")
            print(f"标准输出:\n{result.stdout}")
            print(f"标准错误:\n{result.stderr}")

    except Exception as e:
        print(f"Git操作失败: {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()
