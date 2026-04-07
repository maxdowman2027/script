# Claude Code 技能库安装与使用指南

## 概述

本文档介绍了在 `D:\users\gxu\scripts` 项目中安装和配置的 Claude Code 常用技能库，以及它们的使用方法。

## 1. 技能库安装情况

### 1.1 依赖库安装
项目已安装以下常用依赖库：

```
pandas>=1.3.0          # 数据分析库
matplotlib>=3.5.0      # 图表绘制库
numpy>=1.21.0          # 数值计算库
openpyxl>=3.1.0        # Excel文件处理库
scipy>=1.7.0           # 科学计算库
seaborn>=0.12.0        # 数据可视化库
plotly>=5.13.0         # 交互式图表库
requests>=2.28.0       # HTTP请求库
pyvisa>=1.10.0         # 仪器控制库
pywifi>=1.1.0          # WiFi控制库
```

### 1.2 官方插件市场
已配置并启用官方插件市场（claude-plugins-official），包含以下主要插件：

#### 代码分析与处理
- `code-review`：代码审查工具
- `code-simplifier`：代码简化工具
- `commit-commands`：提交命令
- `feature-dev`：功能开发工具

#### 语言支持
- `pyright-lsp`：Python LSP 支持
- `gopls-lsp`：Go 语言 LSP 支持
- `jdtls-lsp`：Java 语言 LSP 支持
- `kotlin-lsp`：Kotlin 语言 LSP 支持
- `ruby-lsp`：Ruby 语言 LSP 支持
- `rust-analyzer-lsp`：Rust 语言 LSP 支持
- `typescript-lsp`：TypeScript 语言 LSP 支持

#### 项目管理
- `claude-md-management`：CLAUDE.md 文件管理
- `pr-review-toolkit`：PR 审查工具包
- `hookify`：钩子管理工具

#### 安全与学习
- `security-guidance`：安全指导工具
- `learning-output-style`：学习输出风格
- `explanatory-output-style`：解释性输出风格

## 2. 项目特定技能

项目中的 `skill/` 文件夹包含以下技能文件：

### 2.1 `evm_comparison.skill` - EVM 比较分析

**功能**：对比两个 WiFi TX 测试文件中 EVM（误差向量幅度）随发射功率变化的关系

**使用方法**：
```bash
python evm_comparison.py
```

**配置修改**：
```python
# 在 evm_comparison.py 的 main 函数中修改以下变量
separate = False  # False表示所有MCS在一个图上，True表示每个MCS一个图
```

**输出文件**：
- 所有 MCS 合并图：`evm_comparison_per_mcs_combined.png`
- 每个 MCS 单独图：`evm_comparison_per_mcs_separate.pdf`

### 2.2 `calculate_sensitivity_and_plot_Skill.md` - 灵敏度计算与对比

**功能**：计算 WiFi 接收灵敏度，对比 notch_en=0 和 notch_en=1 两种配置下的灵敏度

**使用方法**：
```bash
python calculate_sensitivity_and_plot.py
```

**配置修改**：
```python
# 在 calculate_sensitivity_and_plot.py 的 __main__ 函数中修改路径
csv_file_path = "your_csv_file_path.csv"
output_pdf_path = "your_output.pdf"
```

**输出文件**：`sensitivity_comparison.pdf`

### 2.3 `txAnalyse.skill` - TX 信号分析

**功能**：分析 WiFi TX（发射）信号测试数据，生成图表和报告

**使用方法**：
```bash
python txAnalyse.py
```

**主要功能**：
- 信号幅度和相位分析
- 功率计算
- 调制质量评估

### 2.4 `txmagtrk_analyse.skill` - 磁跟踪测试数据分析

**功能**：分析 WiFi TX（发射）磁跟踪（Magnetic Tracking）测试数据

**使用方法**：
```bash
python txmagtrk_analyse.py
```

**主要功能**：
- 磁跟踪对比分析（trk_en=0 与 trk_en=1）
- 多参数分组分析
- 图表生成与保存

**配置修改**：
```python
# 在 txmagtrk_analyse.py 的 __main__ 函数中修改
CSV_DIR = r"your_data_directory"
SAVE_ROOT_DIR = r"your_save_directory"
RECURSIVE_SEARCH = False
```

### 2.5 `wifiRxProcess_Skill.md` - WiFi 接收过程处理

**功能**：处理 WiFi 接收测试数据，执行 wifiRxPlot 和 file_merge 功能

**使用方法**：
```bash
python wifiRxProcess.py
```

**主要功能**：
- 读取并合并测试数据
- 计算灵敏度指标
- 生成可视化图表
- 合并 Excel 文件

### 2.6 `spur_diff_and_mark_red.skill` - 杂散分析与标记

**功能**：分析杂散信号，标记超出阈值的数值为红色

**使用方法**：
```bash
python spur_diff_and_mark_red.py
```

**主要功能**：
- 杂散信号计算
- 数据对比分析
- Excel 文件标记

## 3. 配置文件

### 3.1 `.claude/settings.local.json`

**权限配置**：
```json
{
  "permissions": {
    "allow": [
      "Bash(python:*)",
      "Bash(rm:*)",
      "Bash(git:*)",
      "Bash(cmd.exe:*)",
      "Bash(cmd:*)",
      "Bash(powershell:*)",
      "Bash(chmod +x:*)",
      "Bash(lsof:*)",
      "Bash(matlab:*)",
      "Bash(tasklist:*)",
      "Bash(mode.com:*)",
      "Bash(netstat:*)",
      "Bash(wmic process:*)",
      "Bash(pip install:*)",
      "Bash(claude:*)"
    ]
  },
  "plugins": {
    "enabled": true,
    "marketplaces": {
      "claude-plugins-official": {
        "enabled": true
      }
    }
  }
}
```

**技能搜索路径**：
```json
"skills": {
  "autoLoad": true,
  "searchPaths": [
    "D:\\users\\gxu\\scripts\\skill"
  ]
}
```

## 4. 使用说明

### 4.1 执行 Python 脚本

**直接运行**：
```bash
python script_name.py
```

**使用 Claud Code**：
```bash
claude "执行 script_name.py 并分析结果"
```

### 4.2 使用官方插件

**查看已安装插件**：
```bash
claude plugin list
```

**启用/禁用插件**：
```bash
claude plugin enable plugin_name
claude plugin disable plugin_name
```

**安装新插件**：
```bash
claude plugin install plugin_name
```

### 4.3 自动技能匹配

Claude Code 会自动识别项目中的 `.skill` 文件，并在你提出相关任务时自动匹配并建议相应的技能。

## 5. 常见问题

### 5.1 依赖库版本不匹配

**问题**：执行脚本时提示模块未找到或版本不兼容

**解决方法**：
```bash
# 检查依赖库版本
pip list

# 更新所有依赖库
pip install -r requirements.txt --upgrade

# 更新单个库
pip install library_name --upgrade
```

### 5.2 路径问题

**问题**：脚本无法找到文件或路径不存在

**解决方法**：
- 确保脚本中的路径与实际文件路径一致
- 检查路径中的斜杠方向（Windows 系统使用反斜杠，Linux/Mac 使用正斜杠）
- 使用绝对路径而非相对路径

### 5.3 权限问题

**问题**：无法执行脚本或写入文件

**解决方法**：
- 检查文件和文件夹的权限设置
- 以管理员身份运行终端或脚本
- 在 `.claude/settings.local.json` 中添加相应的权限

## 6. 技能扩展

### 6.1 创建新技能

**使用官方插件**：
```bash
claude plugin install skill-creator
```

**创建流程**：
1. 使用 `skill-creator` 插件初始化技能文件
2. 编写技能说明文档
3. 实现相关功能代码
4. 测试并优化技能

### 6.2 导入外部技能

**方法**：
1. 下载技能文件到 `skill/` 文件夹
2. 更新 `.claude/settings.local.json` 中的搜索路径
3. 重启 Claude Code 以加载新技能

## 7. 技术支持

如果在使用过程中遇到问题，可以：

1. 检查官方文档和插件说明
2. 使用 Claude Code 的 `help` 功能
3. 在项目的 `修改总结.md` 文件中查找更新信息
4. 联系开发团队获取支持

---

本指南会定期更新，以反映技能库的最新变化。如有任何建议或改进意见，请随时联系开发团队。
