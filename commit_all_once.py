import git
import os

def main():
    repo_path = 'D:/users/gxu/scripts'
    commit_message = "提交所有剩余的脚本文件，完成任务"

    try:
        repo = git.Repo(repo_path)

        # 获取当前未追踪的文件
        untracked_files = repo.untracked_files

        if untracked_files:
            print("未追踪的文件：")
            for file in untracked_files:
                print(f"  {file}")

            # 提交所有未追踪的文件
            repo.git.add(untracked_files)
            commit = repo.index.commit(commit_message)
            print(f"\n提交成功！提交ID: {commit.hexsha}")
            print("所有未追踪文件已提交")

            # 检查是否还有未追踪的文件（应该没有了）
            final_untracked = repo.untracked_files
            if final_untracked:
                print("\n仍然有未追踪的文件：")
                for file in final_untracked:
                    print(f"  {file}")
            else:
                print("\n任务完成！所有文件已完全提交！")

        else:
            print("没有未追踪的文件")

        # 打印最终状态
        print("\n最终Git状态：")
        print(repo.git.status())

    except Exception as e:
        print(f"Git操作失败: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
