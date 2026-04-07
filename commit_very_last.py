import git
import os

def main():
    repo_path = 'D:/users/gxu/scripts'
    commit_message = "添加commit_last_file.py脚本"

    try:
        repo = git.Repo(repo_path)
        if os.path.exists(os.path.join(repo_path, 'commit_last_file.py')):
            repo.git.add('commit_last_file.py')
            commit = repo.index.commit(commit_message)
            print(f"提交成功！提交ID: {commit.hexsha}")
            print(repo.git.status())
        else:
            print("commit_last_file.py文件不存在")

    except Exception as e:
        print(f"Git操作失败: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
