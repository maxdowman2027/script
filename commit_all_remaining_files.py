import git
import os

def main():
    repo_path = 'D:/users/gxu/scripts'
    commit_message = "提交所有剩余的脚本文件"

    try:
        repo = git.Repo(repo_path)
        untracked = repo.untracked_files

        if untracked:
            print("未追踪的文件:")
            for file in untracked:
                print(f"  {file}")

            repo.git.add(untracked)
            commit = repo.index.commit(commit_message)
            print(f"提交成功！提交ID: {commit.hexsha}")
            print("所有未追踪文件已提交")
            print(repo.git.status())
        else:
            print("没有未追踪的文件")

    except Exception as e:
        print(f"Git操作失败: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
