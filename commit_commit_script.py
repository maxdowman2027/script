import git
import os

def main():
    repo_path = 'D:/users/gxu/scripts'
    commit_message = "添加commit_new_scripts.py脚本"

    try:
        repo = git.Repo(repo_path)
        print(f"成功打开Git仓库: {repo_path}")

        if os.path.exists(os.path.join(repo_path, 'commit_new_scripts.py')):
            repo.git.add('commit_new_scripts.py')
            commit = repo.index.commit(commit_message)
            print(f"提交成功！提交ID: {commit.hexsha}")
            print(repo.git.status())
        else:
            print("commit_new_scripts.py文件不存在")

    except Exception as e:
        print(f"Git操作失败: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
