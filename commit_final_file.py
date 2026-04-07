import git
import os

def main():
    repo_path = 'D:/users/gxu/scripts'
    commit_message = "添加commit_commit_summary.py脚本"

    try:
        repo = git.Repo(repo_path)
        final_file = 'commit_commit_summary.py'

        if os.path.exists(os.path.join(repo_path, final_file)):
            repo.git.add(final_file)
            commit = repo.index.commit(commit_message)
            print(f"提交成功！提交ID: {commit.hexsha}")
            print("最后一个文件已提交")
            print(repo.git.status())
        else:
            print(f"{final_file}文件不存在")

    except Exception as e:
        print(f"Git操作失败: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
