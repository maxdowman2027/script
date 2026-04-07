import git
import os

def main():
    repo_path = 'D:/users/gxu/scripts'
    commit_message = "添加多Sheet分析脚本和说明文档"

    try:
        # 打开Git仓库
        repo = git.Repo(repo_path)
        print(f"成功打开Git仓库: {repo_path}")

        # 检查当前状态
        print("\n--- 当前Git状态 ---")
        print(repo.git.status())

        # 要提交的文件列表
        files_to_add = [
            'analyze_multi_sheet.py',
            'skill/merged_tx_result_analysis/analyze_multi_sheet_skill.md'
        ]

        # 添加文件到暂存区
        print("\n--- 正在添加文件到暂存区 ---")
        for file in files_to_add:
            if os.path.exists(os.path.join(repo_path, file)):
                print(f"添加: {file}")
                repo.git.add(file)
            else:
                print(f"警告: 文件不存在: {file}")

        # 检查是否有变更需要提交
        print("\n--- 检查待提交的变更 ---")
        diff = repo.index.diff("HEAD")
        if not diff:
            print("没有需要提交的变更")
            return

        print(f"待提交的变更数量: {len(diff)}")
        for change in diff:
            print(f"  - {change.a_path}")

        # 执行提交
        print(f"\n--- 正在提交变更 ---")
        print(f"提交信息: '{commit_message}'")
        commit = repo.index.commit(commit_message)

        print("提交成功！")
        print(f"提交ID: {commit.hexsha}")
        print(f"提交作者: {commit.author}")
        print(f"提交日期: {commit.committed_datetime}")

    except Exception as e:
        print(f"\n--- Git操作失败 ---")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {e}")
        import traceback
        print("\n详细错误信息:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
