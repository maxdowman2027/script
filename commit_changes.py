import git
import os

def main():
    repo_path = 'D:/users/gxu/scripts'  # 使用正确的Windows路径格式
    commit_message = "添加merged_tx_result分析脚本和可视化脚本，包括说明文档"

    try:
        # 打开Git仓库
        repo = git.Repo(repo_path)

        # 检查当前状态
        print("当前Git状态：")
        print(repo.git.status())
        print("\n---\n")

        # 检查未追踪的文件
        untracked_files = repo.untracked_files
        if untracked_files:
            print("未追踪的文件：")
            for f in untracked_files:
                print(f"  - {f}")
            print("\n---\n")

        # 获取待提交的文件列表
        index = repo.index
        diff = index.diff(None)
        if not diff:
            print("没有需要提交的变更")
            return

        print("待提交的变更：")
        for change in diff:
            print(f"  - {change.a_path}")
        print("\n---\n")

        # 执行提交
        print(f"正在提交变更，提交信息：\"{commit_message}\"")
        repo.index.commit(commit_message)
        print("提交成功！")

        # 显示最新提交信息
        print("\n---\n")
        print("最新提交信息：")
        print(repo.head.commit)
        print(repo.head.commit.message)

    except Exception as e:
        print(f"Git操作失败：{e}")
        import traceback
        print("\n详细错误信息：")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
