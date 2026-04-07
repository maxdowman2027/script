import git
import os

def main():
    repo_path = 'D:/users/gxu/scripts'
    commit_message = "添加所有剩余的分析脚本和文件"

    try:
        # 打开Git仓库
        repo = git.Repo(repo_path)
        print(f"成功打开Git仓库: {repo_path}")

        # 检查是否还有未追踪的文件
        untracked_files = repo.untracked_files
        if untracked_files:
            print("未追踪的文件:")
            for file in untracked_files:
                print(f"  - {file}")

            # 添加所有未追踪的文件到暂存区
            print("\n正在添加未追踪的文件到暂存区...")
            repo.git.add(*untracked_files)
            print("所有未追踪的文件已添加到暂存区")

            # 检查是否还有未暂存的修改
            unstaged_changes = repo.git.diff('HEAD', '--name-only')
            if unstaged_changes:
                print("\n未暂存的修改:")
                for file in unstaged_changes.splitlines():
                    print(f"  - {file}")
                repo.git.add(unstaged_changes.splitlines())
                print("所有未暂存的修改已添加到暂存区")

            # 执行提交
            print(f"\n正在提交变更，提交信息: '{commit_message}'")
            repo.index.commit(commit_message)
            print("提交成功！")

            # 显示最新提交
            latest_commit = repo.head.commit
            print(f"\n最新提交:")
            print(f"  ID: {latest_commit.hexsha}")
            print(f"  作者: {latest_commit.author}")
            print(f"  日期: {latest_commit.committed_datetime}")
            print(f"  信息: {latest_commit.message}")
        else:
            print("没有未追踪的文件需要提交")

            # 检查是否还有未暂存的修改
            unstaged_changes = repo.git.diff('HEAD', '--name-only')
            if unstaged_changes:
                print("\n未暂存的修改:")
                for file in unstaged_changes.splitlines():
                    print(f"  - {file}")
                repo.git.add(unstaged_changes.splitlines())
                print("所有未暂存的修改已添加到暂存区")

                # 执行提交
                print(f"\n正在提交变更，提交信息: '{commit_message}'")
                repo.index.commit(commit_message)
                print("提交成功！")

                # 显示最新提交
                latest_commit = repo.head.commit
                print(f"\n最新提交:")
                print(f"  ID: {latest_commit.hexsha}")
                print(f"  作者: {latest_commit.author}")
                print(f"  日期: {latest_commit.committed_datetime}")
                print(f"  信息: {latest_commit.message}")
            else:
                print("没有任何变更需要提交")

    except Exception as e:
        print(f"Git操作失败: {type(e).__name__}: {e}")
        import traceback
        print("\n详细错误信息:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
