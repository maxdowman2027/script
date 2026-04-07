import git
import os

def main():
    repo_path = 'D:/users/gxu/scripts'
    commit_message = "更新.gitignore文件，添加对分析结果目录的忽略"

    try:
        repo = git.Repo(repo_path)
        print("Git仓库状态:")
        print(repo.git.status())

        repo.git.add('.gitignore')
        commit = repo.index.commit(commit_message)
        print(f"提交成功！提交ID: {commit.hexsha}")

        print("\n提交后状态:")
        print(repo.git.status())

    except Exception as e:
        print(f"Git操作失败: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
