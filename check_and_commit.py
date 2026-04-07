import git
import os

def main():
    repo_path = 'D:/users/gxu/scripts'
    commit_message = "添加merged_tx_result分析脚本和可视化脚本，包括说明文档"

    try:
        # 打开Git仓库
        repo = git.Repo(repo_path)
        print(f"成功打开Git仓库: {repo_path}")

        # 获取待提交的变更
        index = repo.index
        print("正在检查暂存区状态...")

        # 列出暂存区中的变更
        staged_files = []
        for item in index.diff("HEAD"):
            staged_files.append(item.a_path)

        if staged_files:
            print("暂存区中的文件:")
            for file in staged_files:
                print(f"  - {file}")

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
            print("暂存区是空的，没有变更需要提交")

    except Exception as e:
        print(f"Git操作失败: {type(e).__name__}: {e}")
        import traceback
        print("\n详细错误信息:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
