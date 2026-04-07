import git
import os
import sys
import urllib.parse

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

            # 处理编码问题
            files_to_add = []
            for file in untracked_files:
                try:
                    # 尝试解码
                    decoded_file = file.encode('latin-1').decode('utf-8')
                    files_to_add.append(decoded_file)
                except:
                    files_to_add.append(file)

            # 添加所有未追踪的文件到暂存区
            print("\n正在添加未追踪的文件到暂存区...")
            for file in files_to_add:
                try:
                    repo.git.add(file)
                except Exception as e:
                    print(f"添加文件 '{file}' 失败: {e}")

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

    except Exception as e:
        print(f"Git操作失败: {type(e).__name__}: {e}")
        import traceback
        print("\n详细错误信息:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
