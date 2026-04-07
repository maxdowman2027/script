import git
import os

def main():
    repo_path = 'D:/users/gxu/scripts'
    commit_message = "添加commit_final_file.py脚本"

    try:
        repo = git.Repo(repo_path)
        ultimate_file = 'commit_final_file.py'

        if os.path.exists(os.path.join(repo_path, ultimate_file)):
            repo.git.add(ultimate_file)
            commit = repo.index.commit(commit_message)
            print(f"提交成功！提交ID: {commit.hexsha}")
            print("所有文件已完全提交！")
            print("最终Git状态：")
            print(repo.git.status())
        else:
            print(f"{ultimate_file}文件不存在")

    except Exception as e:
        print(f"Git操作失败: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
