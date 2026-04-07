import git
import os

def main():
    repo_path = 'D:/users/gxu/scripts'

    try:
        repo = git.Repo(repo_path)
        print("Git仓库状态:")
        print(repo.git.status())

        # 检查是否还有未提交的文件
        untracked_files = repo.untracked_files
        if untracked_files:
            print("\n未追踪的文件:")
            for file in untracked_files:
                print(f"  {file}")

            # 提交剩余文件
            repo.git.add(untracked_files)
            commit = repo.index.commit("添加剩余的脚本文件")
            print(f"\n提交成功！提交ID: {commit.hexsha}")

            # 再次检查状态
            print("\n提交后状态:")
            print(repo.git.status())
        else:
            print("\n没有未追踪的文件")

    except Exception as e:
        print(f"Git操作失败: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
